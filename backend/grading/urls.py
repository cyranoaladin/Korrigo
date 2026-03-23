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
    ExamLLMSummaryView,
    CopyLLMSummaryView,
    AdminForceUnlockView,
    CopyReopenView,
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
from grading.views_my_students import MyStudentsListView, StudentBilanView
from grading.views_questionnaire import QuestionnaireResponseView, QuestionnaireBilanView

urlpatterns = [
    # Drafts
    path('copies/<uuid:copy_id>/draft/', DraftReturnView.as_view(), name='copy-draft'),

    # Annotations
    path('copies/<uuid:copy_id>/annotations/', AnnotationListCreateView.as_view(), name='annotation-list-create'),
    path('annotations/<uuid:pk>/', AnnotationDetailView.as_view(), name='annotation-detail'),

    # Workflow Copy
    path('copies/<uuid:id>/ready/', CopyReadyView.as_view(), name='copy-ready'),
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

    # LLM Summary Generation
    path('exams/<uuid:exam_id>/generate-summaries/', ExamLLMSummaryView.as_view(), name='exam-llm-summaries'),
    path('copies/<uuid:copy_id>/generate-summary/', CopyLLMSummaryView.as_view(), name='copy-llm-summary'),

    # Banque d'annotations — Suggestions contextuelles
    path('exams/<uuid:exam_id>/suggestions/', ContextualSuggestionsView.as_view(), name='contextual-suggestions'),
    path('exams/<uuid:exam_id>/annotation-templates/', AnnotationTemplateListView.as_view(), name='annotation-template-list'),

    # Annotations personnelles du correcteur
    path('my-annotations/', UserAnnotationListCreateView.as_view(), name='user-annotation-list-create'),
    path('my-annotations/auto-save/', AutoSaveAnnotationView.as_view(), name='user-annotation-auto-save'),
    path('my-annotations/<uuid:pk>/', UserAnnotationDetailView.as_view(), name='user-annotation-detail'),
    path('my-annotations/<uuid:pk>/use/', UserAnnotationUseView.as_view(), name='user-annotation-use'),

    # Admin Force Unlock
    path('copies/<uuid:copy_id>/force-unlock/', AdminForceUnlockView.as_view(), name='copy-force-unlock'),

    # Reopen (GRADED → READY)
    path('copies/<uuid:copy_id>/reopen/', CopyReopenView.as_view(), name='copy-reopen'),

    # Mes Élèves (correcteur)
    path('my-students/', MyStudentsListView.as_view(), name='my-students-list'),
    path('students/<int:student_id>/bilan/', StudentBilanView.as_view(), name='student-bilan'),
    path('questionnaire/', QuestionnaireResponseView.as_view(), name='questionnaire-response'),
    path('questionnaire/bilan/', QuestionnaireBilanView.as_view(), name='questionnaire-bilan'),
]
