from django.urls import path
from .views import (
    ExamUploadView, BookletListView, ExamListView,
    ExamDetailView, CopyListView, MergeBookletsView, ExportAllView, CSVExportView,
    CopyIdentificationView, UnidentifiedCopiesView, StudentCopiesView,
    CopyImportView, ExamSourceUploadView, BookletSplitView, BookletDetailView,
    BookletHeaderView, ExamDispatchView, IndividualPDFUploadView, PronoteExportView,
    CopyValidationView, BulkCopyValidationView,
    BulkSubjectVariantView, AutoDetectSubjectVariantView,
    ExamStudentListView,
    GlobalStatsView,
    ExamTypeListView, ExamTypeDetailView,
    JuryReportListView, JuryReportDetailView,
)
from .views_stats import StatsReportView
from .views_documents import (
    DocumentSetUploadView,
    DocumentSetListView,
    DocumentSetActivateView,
    DocumentSetRetryExtractionView,
)

urlpatterns = [
    # Exam Types and Jury Reports (Moved UP to avoid shadowing)
    path('types/', ExamTypeListView.as_view(), name='examtype-list'),
    path('types/<uuid:id>/', ExamTypeDetailView.as_view(), name='examtype-detail'),
    path('reports/', JuryReportListView.as_view(), name='juryreport-list'),
    path('reports/<uuid:id>/', JuryReportDetailView.as_view(), name='juryreport-detail'),

    # Mission 14: Upload & List
    path('upload/', ExamUploadView.as_view(), name='exam-upload'),
    path('', ExamListView.as_view(), name='exam-list'),
    path('global-stats/', GlobalStatsView.as_view(), name='exam-global-stats'),
    path('<uuid:id>/', ExamDetailView.as_view(), name='exam-detail'),
    path('<uuid:pk>/upload/', ExamSourceUploadView.as_view(), name='exam-source-upload'),
    
    # New Import Routes
    path('<uuid:exam_id>/copies/import/', CopyImportView.as_view(), name='copy-import'),
    path('<uuid:exam_id>/upload-individual-pdfs/', IndividualPDFUploadView.as_view(), name='individual-pdf-upload'),

    # Mission 16: Booklet Management
    path('<uuid:exam_id>/booklets/', BookletListView.as_view(), name='booklet-list'),
    path('booklets/<uuid:id>/header/', BookletHeaderView.as_view(), name='booklet-header'),
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
    path('<uuid:id>/export-pronote/', PronoteExportView.as_view(), name='export-pronote'),
    
    # Copy Validation (STAGING → READY)
    path('copies/<uuid:id>/validate/', CopyValidationView.as_view(), name='copy-validate'),
    path('<uuid:exam_id>/validate-all/', BulkCopyValidationView.as_view(), name='bulk-copy-validate'),
    
    # Subject Variant (bulk assign A/B)
    path('<uuid:exam_id>/bulk-subject-variant/', BulkSubjectVariantView.as_view(), name='bulk-subject-variant'),
    path('<uuid:exam_id>/auto-detect-subject/', AutoDetectSubjectVariantView.as_view(), name='auto-detect-subject'),
    
    # Dispatch
    path('<uuid:exam_id>/dispatch/', ExamDispatchView.as_view(), name='exam-dispatch'),
    
    # Student List (admin view)
    path('<uuid:exam_id>/student-list/', ExamStudentListView.as_view(), name='exam-student-list'),
    
    # Student Portal
    path('student/copies/', StudentCopiesView.as_view(), name='student-copies'),

    # Jury Report (dynamic stats)
    path('stats-report/', StatsReportView.as_view(), name='stats-report'),

    # Document Management (sujet, corrigé, barème)
    path('<uuid:exam_id>/document-sets/', DocumentSetUploadView.as_view(), name='document-set-upload'),
    path('<uuid:exam_id>/document-sets/list/', DocumentSetListView.as_view(), name='document-set-list'),
    path('<uuid:exam_id>/document-sets/<uuid:set_id>/activate/', DocumentSetActivateView.as_view(), name='document-set-activate'),
    path('<uuid:exam_id>/document-sets/<uuid:set_id>/retry-extraction/', DocumentSetRetryExtractionView.as_view(), name='document-set-retry'),
]

# Analytics endpoints (temporarily disabled - UploadMetrics model not yet implemented)
# from exams.views_analytics import UploadAnalyticsView, StorageAnalyticsView

# urlpatterns += [
#     path('analytics/uploads/', UploadAnalyticsView.as_view(), name='upload-analytics'),
#     path('analytics/storage/', StorageAnalyticsView.as_view(), name='storage-analytics'),
# ]
