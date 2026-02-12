from django.urls import path
from .views import StudentListView, StudentLoginView, StudentLogoutView, StudentMeView, StudentImportView, StudentChangePasswordView
# Import directly from exams views if possible, or use a wrapper. 
# To avoid circular imports if exams imports students models, act carefully.
# exams.views imports students.models inside a method to avoid circularity.
# We can import exams.views here safely usually.
from exams.views import StudentCopiesView

urlpatterns = [
    path('', StudentListView.as_view(), name='student-list'),
    path('login/', StudentLoginView.as_view(), name='student-login'),
    path('logout/', StudentLogoutView.as_view(), name='student-logout'),
    path('me/', StudentMeView.as_view(), name='student-me'),
    path('copies/', StudentCopiesView.as_view(), name='student-copies'),
    path('import/', StudentImportView.as_view(), name='student-import'),
    path('change-password/', StudentChangePasswordView.as_view(), name='student-change-password'),
]
