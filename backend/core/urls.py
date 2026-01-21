from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/exams/', include('exams.urls')),
    path('api/copies/', include('exams.urls_copies')), # Mission 17
    path('api/students/', include('students.urls')), # Mission 18
    path('api/login/', views.LoginView.as_view(), name='login'),
    path('api/logout/', views.LogoutView.as_view(), name='logout'),
    path('api/me/', views.UserDetailView.as_view(), name='user_detail'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

