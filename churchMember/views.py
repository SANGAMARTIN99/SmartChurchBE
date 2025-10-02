from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
import os

# Create your views here.

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_media(request):
    """
    Accepts multipart/form-data with 'file' and optional 'folder' (e.g., 'devotionals').
    Saves the file under MEDIA_ROOT/<folder>/ and returns a public URL.
    """
    file_obj = request.FILES.get('file')
    folder = request.data.get('folder', 'uploads')
    if not file_obj:
        return Response({'detail': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

    safe_folder = ''.join(c for c in folder if c.isalnum() or c in ('-', '_', '/')).strip('/')
    rel_path = os.path.join(safe_folder, file_obj.name)

    # Ensure directory exists
    full_dir = os.path.join(settings.MEDIA_ROOT, safe_folder)
    os.makedirs(full_dir, exist_ok=True)

    # Save file
    path = default_storage.save(rel_path, ContentFile(file_obj.read()))
    url = request.build_absolute_uri(os.path.join(settings.MEDIA_URL, path).replace('\\', '/'))
    return Response({'url': url}, status=status.HTTP_201_CREATED)

# Create your views here.
