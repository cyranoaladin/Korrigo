"""
Tests for async task status endpoints
P0-OP-03: Async task monitoring tests
"""
from unittest.mock import patch, Mock
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from celery.result import AsyncResult

User = get_user_model()


class TaskStatusViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role=User.Role.TEACHER
        )
        self.client.force_authenticate(user=self.user)

    @patch('grading.views_async.AsyncResult')
    def test_task_status_pending(self, mock_async_result):
        """GET task status returns PENDING state"""
        mock_result = Mock()
        mock_result.state = 'PENDING'
        mock_result.info = None
        mock_async_result.return_value = mock_result
        
        response = self.client.get('/api/grading/tasks/fake-task-id/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'PENDING')

    @patch('grading.views_async.AsyncResult')
    def test_task_status_success(self, mock_async_result):
        """GET task status returns SUCCESS with result"""
        mock_result = Mock()
        mock_result.state = 'SUCCESS'
        mock_result.info = {'copy_id': '123', 'status': 'success'}
        mock_async_result.return_value = mock_result
        
        response = self.client.get('/api/grading/tasks/fake-task-id/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'SUCCESS')
        self.assertEqual(response.data['result']['copy_id'], '123')

    @patch('grading.views_async.AsyncResult')
    def test_task_status_failure(self, mock_async_result):
        """GET task status returns FAILURE with error"""
        mock_result = Mock()
        mock_result.state = 'FAILURE'
        mock_result.info = Exception("Task failed")
        mock_async_result.return_value = mock_result
        
        response = self.client.get('/api/grading/tasks/fake-task-id/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'FAILURE')
        self.assertIn('error', response.data)

    @patch('grading.views_async.AsyncResult')
    def test_task_cancel(self, mock_async_result):
        """POST cancel revokes pending task"""
        mock_result = Mock()
        mock_result.state = 'PENDING'
        mock_async_result.return_value = mock_result
        
        response = self.client.post('/api/grading/tasks/fake-task-id/cancel/')
        
        self.assertEqual(response.status_code, 200)
        mock_result.revoke.assert_called_once()

    @patch('grading.views_async.AsyncResult')
    def test_task_cancel_completed_task_fails(self, mock_async_result):
        """Cannot cancel completed task"""
        mock_result = Mock()
        mock_result.state = 'SUCCESS'
        mock_async_result.return_value = mock_result
        
        response = self.client.post('/api/grading/tasks/fake-task-id/cancel/')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('already completed', response.data['error'].lower())

    def test_task_status_requires_authentication(self):
        """Task status endpoints require authentication"""
        self.client.logout()
        
        response = self.client.get('/api/grading/tasks/fake-task-id/')
        
        self.assertEqual(response.status_code, 401)

    @patch('grading.views_async.AsyncResult')
    def test_admin_sees_full_traceback(self, mock_async_result):
        """Admin users see full error traceback"""
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='adminpass123'
        )
        self.client.force_authenticate(user=admin)
        
        mock_result = Mock()
        mock_result.state = 'FAILURE'
        mock_result.info = Exception("Detailed error")
        mock_result.traceback = "Full traceback here..."
        mock_async_result.return_value = mock_result
        
        response = self.client.get('/api/grading/tasks/fake-task-id/')
        
        self.assertEqual(response.status_code, 200)
        # Admin should see traceback or detailed error info
        self.assertIn('error', response.data)
