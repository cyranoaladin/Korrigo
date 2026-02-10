from django.urls import path
from .views import (
    ExamUploadView, BookletListView, ExamListView,
    ExamDetailView, CopyListView, MergeBookletsView, ExportAllView, CSVExportView,
    CopyIdentificationView, UnidentifiedCopiesView, StudentCopiesView,
    CopyImportView, ExamSourceUploadView, BookletSplitView, BookletDetailView,
    ExamDispatchView, IndividualPDFUploadView
)

urlpatterns = [
    # Mission 14: Upload & List
    path('upload/', ExamUploadView.as_view(), name='exam-upload'),
    path('', ExamListView.as_view(), name='exam-list'),
    path('<uuid:id>/', ExamDetailView.as_view(), name='exam-detail'),
    path('<uuid:pk>/upload/', ExamSourceUploadView.as_view(), name='exam-source-upload'),
    
    # New Import Routes
    path('<uuid:exam_id>/copies/import/', CopyImportView.as_view(), name='copy-import'),
    path('<uuid:exam_id>/upload-individual-pdfs/', IndividualPDFUploadView.as_view(), name='individual-pdf-upload'),

    # Mission 16: Booklet Management
    path('<uuid:exam_id>/booklets/', BookletListView.as_view(), name='booklet-list'),
    # path('booklets/<uuid:id>/header/', BookletHeaderView.as_view(), name='booklet-header'), # Not implemented
    path('booklets/<uuid:id>/split/', BookletSplitView.as_view(), name='booklet-split'),
    path('booklets/<uuid:id>/', BookletDetailView.as_view(), name='booklet-detail'),
    
    # Mission 21: New Copy & Identification Endpoints
    path('<uuid:exam_id>/unidentified-copies/', UnidentifiedCopiesView.as_view(), name='unidentified-copies'),
    path('copies/<uuid:id>/identify/', CopyIdentificationView.as_view(), name='copy-identify'), # Using UUID
    
    # Correction Admin
    path('<uuid:exam_id>/copies/', CopyListView.as_view(), name='copy-list'),
    path('<uuid:exam_id>/merge-booklets/', MergeBookletsView.as_view(), name='merge-booklets'),
    
    # Export
    path('<uuid:id>/export-pdf/', ExportAllView.as_view(), name='export-all-pdf'),
    path('<uuid:id>/export-csv/', CSVExportView.as_view(), name='export-csv'),
    
    # Dispatch
    path('<uuid:exam_id>/dispatch/', ExamDispatchView.as_view(), name='exam-dispatch'),
    
    # Student Portal
    path('student/copies/', StudentCopiesView.as_view(), name='student-copies'),
]
