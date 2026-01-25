from django.urls import path
from . import views

urlpatterns = [
    path('desk/', views.IdentificationDeskView.as_view(), name='identification-desk'),
    path('identify/<uuid:copy_id>/', views.ManualIdentifyView.as_view(), name='manual-identify'),
    path('ocr-identify/<uuid:copy_id>/', views.OCRIdentifyView.as_view(), name='ocr-identify'),
    path('perform-ocr/<uuid:copy_id>/', views.OCRPerformView.as_view(), name='ocr-perform'),
]