"""
URL patterns for DNB Bilan API
"""

from django.urls import path
from . import views

app_name = 'bilan'

urlpatterns = [
    path('', views.list_bilans, name='list_bilans'),
    path('generate/', views.generate_bilan, name='generate_bilan'),
    path('stats/', views.bilan_stats, name='bilan_stats'),
    path('<uuid:pk>/', views.bilan_detail, name='bilan_detail'),
    path('<uuid:pk>/pdf/', views.download_bilan_pdf, name='download_bilan_pdf'),
]
