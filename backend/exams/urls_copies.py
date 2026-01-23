from django.urls import path
from .views import CopyIdentificationView, CorrectorCopiesView, CorrectorCopyDetailView

urlpatterns = [
    path('', CorrectorCopiesView.as_view(), name='corrector-copy-list'),
    path('<uuid:id>/', CorrectorCopyDetailView.as_view(), name='corrector-copy-detail'),
    path('<uuid:id>/identify/', CopyIdentificationView.as_view(), name='copy-identify'),
]
