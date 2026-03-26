from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from celery.result import AsyncResult

# 1. Added ResearchSession model to save history
from .models import ResearchSession , ChatMessage, Document
from .serializers import DocumentUploadSerializer
from .tasks import process_document_task
from ai_engine.graph import app as ai_graph

class UploadDocumentView(APIView):
    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        
        if serializer.is_valid():
            file = serializer.validated_data['file']
            query = serializer.validated_data['query']
            
            # --- NEW: Multi-PDF Session Logic ---
            # Check if the frontend sent an existing session_id
            session_id = request.data.get('session_id')
            
            if session_id:
                try:
                    # If session_id exists, we get that session to append files to it
                    session = ResearchSession.objects.get(id=session_id)
                except (ResearchSession.DoesNotExist, ValueError):
                    # Fallback if the ID is invalid
                    session = ResearchSession.objects.create(title=file.name)
            else:
                # No session_id provided, this is the first file of a new chat
                session = ResearchSession.objects.create(title=file.name)
            
            # Save file temporarily for Celery to pick up
            file_name = default_storage.save(f"temp/{file.name}", file)
            file_path = default_storage.path(file_name)
            
            # --- Pass session.id to the background task ---
            # The task will save the parsed text into the Document table linked to this session
            task = process_document_task.delay(file_path, query, session.id)
            
            return Response(
                {
                    "task_id": task.id, 
                    "session_id": session.id,
                    "message": f"Successfully added {file.name} to research session."
                }, 
                status=status.HTTP_202_ACCEPTED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TaskStatusView(APIView):
    def get(self, request, task_id):
        result = AsyncResult(task_id)
        output = None
        
        if result.ready():
            # If successful, result.result is the 'brief' string
            # If it failed, we convert the Error object to a string
            output = result.result if result.successful() else str(result.result)

        return Response({
            "status": result.status,
            "result": output
        })

# --- NEW: Endpoint to fill your Sidebar History ---
class HistoryView(APIView):
    def get(self, request):
        # Fetch all previous research sessions from Supabase
        sessions = ResearchSession.objects.all().order_by('-created_at')
        data = [
            {
                "id": s.id, 
                "title": s.title, 
                "created_at": s.created_at.strftime("%Y-%m-%d %H:%M")
            } for s in sessions
        ]
        return Response(data)
    
class ChatView(APIView):
    def post(self, request):
        session_id = request.data.get('session_id')
        query = request.data.get('query')

        # Safety Check: Ensure session exists
        session = get_object_or_404(ResearchSession, id=session_id)
        
        # 1. Fetch ALL documents linked to this research session
        all_docs = session.documents.all()
        
        if not all_docs.exists():
            return Response({
                "answer": "I don't see any documents in this session. Please upload some PDFs first!"
            })
        
        # 2. Map and Label the context
        # We wrap each document in headers so the LLM can distinguish between files
        context_blocks = []
        for doc in all_docs:
            block = f"--- SOURCE FILE: {doc.file_name} ---\n{doc.content}"
            context_blocks.append(block)
        
        full_context = "\n\n".join(context_blocks)

        # 3. Save the User's Message to history
        ChatMessage.objects.create(
            session=session, 
            sender="user", 
            text=query
        )

        # 4. Construct the prompt and Invoke the AI Graph
        # We explicitly tell the AI to use the provided filenames in its reasoning
        inputs = {
            "query": f"Using the provided documents, answer this: {query}. If the answer spans multiple files, please compare them and cite the filenames.",
            "context": [full_context]
        }
        
        try:
            result = ai_graph.invoke(inputs)
            # Pull the technical brief/answer from the graph result
            answer = result.get("brief", "I'm sorry, I couldn't process the documents correctly.")
        except Exception as e:
            answer = f"Error communicating with AI Engine: {str(e)}"

        # 5. Save the AI's Response to history
        ChatMessage.objects.create(
            session=session, 
            sender="ai", 
            text=answer
        )

        # 6. Return response to React
        return Response({"answer": answer})

class HistoryDetailView(APIView):
    # Rename Session
    def patch(self, request, session_id):
        session = ResearchSession.objects.get(id=session_id)
        session.title = request.data.get('title', session.title)
        session.save()
        return Response({"status": "updated"})

    # Delete Session
    def delete(self, request, session_id):
        ResearchSession.objects.get(id=session_id).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class SessionDetailView(APIView):
    """Retrieves all messages for a specific session (Sidebar Click)."""
    def get(self, request, session_id):
        session = ResearchSession.objects.get(id=session_id)
        messages = session.messages.all().order_by('timestamp')
        return Response({
            "title": session.title,
            "messages": [{"role": m.sender, "text": m.text} for m in messages]
        })