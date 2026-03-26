from rest_framework import serializers
import os

class DocumentUploadSerializer(serializers.Serializer):
    # Only allow files up to 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024 
    ALLOWED_EXTENSIONS = ['.pdf']

    file = serializers.FileField()
    query = serializers.CharField(required=False, default="Summarize this document.")

    def validate_file(self, value):
        # 1. Check File Extension
        ext = os.path.splitext(value.name)[1].lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            raise serializers.ValidationError("Only PDF files are allowed.")

        # 2. Check File Size
        if value.size > self.MAX_FILE_SIZE:
            raise serializers.ValidationError("File size must be under 10MB.")

        return value