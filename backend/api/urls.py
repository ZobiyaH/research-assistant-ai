from django.urls import path
from .views import UploadDocumentView, TaskStatusView, HistoryView,ChatView,SessionDetailView,HistoryDetailView

urlpatterns = [
    # This matches: http://localhost:8000/api/upload/
    path('upload/', UploadDocumentView.as_view(), name='upload'),
    
    # This matches: http://localhost:8000/api/status/<task_id>/
    path('status/<str:task_id>/', TaskStatusView.as_view(), name='task_status'),
    path('history/', HistoryView.as_view(), name='history'),
    path('chat/', ChatView.as_view(), name='chat'),
    path('session/<uuid:session_id>/', SessionDetailView.as_view(), name='session_detail'),
    path('history/<uuid:session_id>/', HistoryDetailView.as_view(), name='history_detail'),
]