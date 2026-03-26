import os
from celery import shared_task
from django.core.files.storage import default_storage
from .models import ResearchSession, ChatMessage, Document
from ai_engine.graph import app as ai_graph
from llama_cloud_services import LlamaParse

def parse_pdf_to_markdown(file_path):
    # Standard LlamaParse configuration
    parser = LlamaParse(result_type="markdown")
    extra_info = parser.load_data(file_path)
    return extra_info[0].text

@shared_task
def process_document_task(file_path, query, session_id):
    try:
        # 1. Parse PDF using LlamaParse
        markdown_text = parse_pdf_to_markdown(file_path)
        file_name = os.path.basename(file_path)
        
        # 2. Retrieve the active session
        session = ResearchSession.objects.get(id=session_id)
        
        # 3. Save to Document table 
        # This is critical for the "Multi-Doc" mapping feature
        Document.objects.create(
            session=session,
            file_name=file_name,
            content=markdown_text
        )
        
        # 4. Prepare inputs for the Gemini-powered Graph
        # We no longer need to truncate heavily because of Gemini's 1M window
        inputs = {
            "query": query, 
            "context": [markdown_text] 
        }
        
        # 5. Invoke the Graph (Now using Gemini 1.5 Flash)
        result = ai_graph.invoke(inputs)
        answer = result.get("brief", "Analysis complete.")

        # 6. Save the AI's response as the first message in the chat
        ChatMessage.objects.create(
            session=session, 
            sender="ai", 
            text=answer
        )
        
        # 7. Cleanup the temporary uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)
            
        return f"Successfully processed {file_name}"

    except Exception as e:
        print(f"CRITICAL TASK ERROR: {str(e)}")
        return f"Error: {str(e)}"