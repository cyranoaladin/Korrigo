from django.urls import path
from . import views

urlpatterns = [
    path('desk/', views.IdentificationDeskView.as_view(), name='identification-desk'),
    path('identify/<uuid:copy_id>/', views.ManualIdentifyView.as_view(), name='manual-identify'),
    path('ocr-identify/<uuid:copy_id>/', views.OCRIdentifyView.as_view(), name='ocr-identify'),
    path('perform-ocr/<uuid:copy_id>/', views.OCRPerformView.as_view(), name='ocr-perform'),

    # PRD-19: Multi-layer OCR endpoints
    path('copies/<uuid:copy_id>/ocr-candidates/', views.get_ocr_candidates, name='ocr-candidates'),
    path('copies/<uuid:copy_id>/select-candidate/', views.select_ocr_candidate, name='select-ocr-candidate'),
]