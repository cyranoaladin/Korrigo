"""
URL configuration pour l'app grading.
"""
from django.urls import path
from grading.views import (
    AnnotationListCreateView,
    AnnotationDetailView,
    CopyFinalizeView,
    CopyReadyView,
    CopyFinalPdfView,
    CopyAuditView,
    QuestionRemarkListCreateView,
    QuestionRemarkDetailView,
    CopyGlobalAppreciationView,
    CopyScoresView,
    CorrectorStatsView,
    ExamReleaseResultsView,
    ExamUnreleaseResultsView,
)
from grading.views_lock import (
    LockAcquireView,
    LockHeartbeatView,
    LockReleaseView,
    LockStatusView
)
from grading.views_draft import DraftReturnView
from grading.views_async import task_status, cancel_task
from grading.views_annotation_bank import (
    ContextualSuggestionsView,
    UserAnnotationListCreateView,
    UserAnnotationDetailView,
    UserAnnotationUseView,
    AutoSaveAnnotationView,
    AnnotationTemplateListView,
)

urlpatterns = [
    # Drafts
    path('copies/<uuid:copy_id>/draft/', DraftReturnView.as_view(), name='copy-draft'),

    # Annotations
    path('copies/<uuid:copy_id>/annotations/', AnnotationListCreateView.as_view(), name='annotation-list-create'),
    path('annotations/<uuid:pk>/', AnnotationDetailView.as_view(), name='annotation-detail'),

    # Workflow Copy
    path('copies/<uuid:id>/ready/', CopyReadyView.as_view(), name='copy-ready'),
    path('copies/<uuid:copy_id>/lock/', LockAcquireView.as_view(), name='lock-acquire'), # POST
    path('copies/<uuid:copy_id>/lock/status/', LockStatusView.as_view(), name='lock-status'), # GET
    path('copies/<uuid:copy_id>/lock/heartbeat/', LockHeartbeatView.as_view(), name='lock-heartbeat'), # POST
    path('copies/<uuid:copy_id>/lock/release/', LockReleaseView.as_view(), name='lock-release'), # DELETE
    path('copies/<uuid:id>/finalize/', CopyFinalizeView.as_view(), name='copy-finalize'),
    path('copies/<uuid:id>/final-pdf/', CopyFinalPdfView.as_view(), name='copy-final-pdf'),
    
    # Async Task Status (P0-OP-03)
    path('tasks/<str:task_id>/', task_status, name='task-status'),
    path('tasks/<str:task_id>/cancel/', cancel_task, name='task-cancel'),
    
    # Audit
    path('copies/<uuid:id>/audit/', CopyAuditView.as_view(), name='copy-audit'),
    
    # Question Remarks
    path('copies/<uuid:copy_id>/remarks/', QuestionRemarkListCreateView.as_view(), name='question-remark-list-create'),
    path('remarks/<uuid:pk>/', QuestionRemarkDetailView.as_view(), name='question-remark-detail'),
    
    # Global Appreciation
    path('copies/<uuid:copy_id>/global-appreciation/', CopyGlobalAppreciationView.as_view(), name='copy-global-appreciation'),

    # Per-question Scores
    path('copies/<uuid:copy_id>/scores/', CopyScoresView.as_view(), name='copy-scores'),

    # Corrector Stats
    path('exams/<uuid:exam_id>/stats/', CorrectorStatsView.as_view(), name='corrector-stats'),

    # Release/Unrelease Results
    path('exams/<uuid:exam_id>/release-results/', ExamReleaseResultsView.as_view(), name='exam-release-results'),
    path('exams/<uuid:exam_id>/unrelease-results/', ExamUnreleaseResultsView.as_view(), name='exam-unrelease-results'),

    # Banque d'annotations — Suggestions contextuelles
    path('exams/<uuid:exam_id>/suggestions/', ContextualSuggestionsView.as_view(), name='contextual-suggestions'),
    path('exams/<uuid:exam_id>/annotation-templates/', AnnotationTemplateListView.as_view(), name='annotation-template-list'),

    # Annotations personnelles du correcteur
    path('my-annotations/', UserAnnotationListCreateView.as_view(), name='user-annotation-list-create'),
    path('my-annotations/auto-save/', AutoSaveAnnotationView.as_view(), name='user-annotation-auto-save'),
    path('my-annotations/<uuid:pk>/', UserAnnotationDetailView.as_view(), name='user-annotation-detail'),
    path('my-annotations/<uuid:pk>/use/', UserAnnotationUseView.as_view(), name='user-annotation-use'),
]
