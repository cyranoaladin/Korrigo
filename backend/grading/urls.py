"""
URL configuration pour l'app grading.
"""
from django.urls import path
from grading.views import (
    AnnotationListCreateView,
    AnnotationDetailView,
    CopyLockView,
    CopyUnlockView,
    CopyFinalizeView
)

urlpatterns = [
    # Annotations
    path('copies/<uuid:copy_id>/annotations/', AnnotationListCreateView.as_view(), name='annotation-list-create'),
    path('annotations/<uuid:pk>/', AnnotationDetailView.as_view(), name='annotation-detail'),

    # Workflow Copy
    path('copies/<uuid:id>/lock/', CopyLockView.as_view(), name='copy-lock'),
    path('copies/<uuid:id>/unlock/', CopyUnlockView.as_view(), name='copy-unlock'),
    path('copies/<uuid:id>/finalize/', CopyFinalizeView.as_view(), name='copy-finalize'),
]
