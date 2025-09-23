from django.urls import path
from . import views

urlpatterns = [
    path('upload-image/', views.upload_image, name='upload_image'),
]