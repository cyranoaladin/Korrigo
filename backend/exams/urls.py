from django.urls import path
from .views import (
    ExamUploadView, BookletListView, MergeBookletsView, ExamDetailView,
    ExportAllView, CSVExportView, UnidentifiedCopiesView, BookletHeaderView,
    ExamListView, CopyListView
)

urlpatterns = [
    path('', ExamListView.as_view(), name='exam-list'),
    path('upload/', ExamUploadView.as_view(), name='exam-upload'),
    path('<uuid:id>/', ExamDetailView.as_view(), name='exam-detail'),
    path('<uuid:exam_id>/booklets/', BookletListView.as_view(), name='booklet-list'),
    path('<uuid:exam_id>/copies/', CopyListView.as_view(), name='copy-list'),
    path('<uuid:id>/export_all/', ExportAllView.as_view(), name='exam-export-all'),
    path('<uuid:id>/csv/', CSVExportView.as_view(), name='exam-csv'),
    path('booklets/<uuid:id>/header/', BookletHeaderView.as_view(), name='booklet-header'),
    path('<uuid:exam_id>/merge/', MergeBookletsView.as_view(), name='merge-booklets'),
    path('<uuid:id>/unidentified_copies/', UnidentifiedCopiesView.as_view(), name='unidentified-copies'),  # Mission 18
]
