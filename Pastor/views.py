from django.core.files.storage import FileSystemStorage
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_image(request):
    if request.user.role != 'PASTOR':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    file = request.FILES.get('image')
    if not file:
        return JsonResponse({'error': 'No file provided'}, status=400)
    fs = FileSystemStorage()
    filename = fs.save(file.name, file)
    url = fs.url(filename)
    return JsonResponse({'image_url': url})