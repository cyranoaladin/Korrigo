from django.urls import path
from .views import CopyIdentificationView

urlpatterns = [
    path('<uuid:id>/identify/', CopyIdentificationView.as_view(), name='copy-identify'),
]
