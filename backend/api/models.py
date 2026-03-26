from django.db import models
import uuid

class ResearchSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

class Document(models.Model):
    session = models.ForeignKey(ResearchSession, on_delete=models.CASCADE, related_name='documents')
    file_name = models.CharField(max_length=255)
    content = models.TextField() # The Markdown from LlamaParse

class ChatMessage(models.Model):
    session = models.ForeignKey(ResearchSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=20) # 'user' or 'ai'
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)