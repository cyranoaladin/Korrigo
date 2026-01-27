from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/exams/', include('exams.urls')),
    path('api/copies/', include('exams.urls_copies')), # Mission 17
    path('api/students/', include('students.urls')), # Mission 18
    path('api/identification/', include('identification.urls')), # ÉTAPE 1-2: OCR & Identification
    path('api/grading/', include('grading.urls')),  # Étape 3: Annotations & Grading (Prefix explicit)
    path('api/login/', views.LoginView.as_view(), name='login'),
    path('api/logout/', views.LogoutView.as_view(), name='logout'),
    path('api/me/', views.UserDetailView.as_view(), name='user_detail'),
    path('api/settings/', views.GlobalSettingsView.as_view(), name='settings'),
    path('api/change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    path('api/users/', views.UserListView.as_view(), name='user_list'),
    path('api/users/<int:pk>/', views.UserManageView.as_view(), name='user_manage'),
]

# API Documentation (DRF Spectacular)
urlpatterns += [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Health check endpoints (always available)
from core.views_health import health_check, liveness_check, readiness_check
urlpatterns += [
    path('api/health/', health_check, name='health_check'),
    path('api/health/live/', liveness_check, name='liveness'),
    path('api/health/ready/', readiness_check, name='readiness'),
]

# Metrics endpoint (admin only - P0-OP-08)
from core.views_metrics import MetricsView
urlpatterns += [
    path('api/metrics/', MetricsView.as_view(), name='metrics'),
]

# Dev/E2E endpoints (only if E2E_SEED_TOKEN is set)
if hasattr(settings, 'E2E_SEED_TOKEN') and settings.E2E_SEED_TOKEN:
    from core.views_dev import seed_e2e_endpoint
    urlpatterns += [
        path('api/dev/seed/', seed_e2e_endpoint, name='seed_e2e'),
    ]

# Patch B: Static media only in DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

