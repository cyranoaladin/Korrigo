"""
Tests pour l'audit trail (AuditLog)
Conformité: Phase 1 - Corrections Critiques Sécurité
"""
import pytest
from django.contrib.auth.models import User
from django.test import RequestFactory
from core.models import AuditLog
from core.utils.audit import (
    log_audit,
    log_authentication_attempt,
    log_data_access,
    log_workflow_action,
    get_client_ip,
)


@pytest.mark.django_db
class TestAuditLog:
    """Tests du modèle AuditLog"""

    def test_create_audit_log(self):
        """Test création d'un log d'audit"""
        user = User.objects.create_user(username='testuser', password='testpass')
        
        log = AuditLog.objects.create(
            user=user,
            action='test.action',
            resource_type='Test',
            resource_id='123',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0',
            metadata={'key': 'value'}
        )
        
        assert log.id is not None
        assert log.user == user
        assert log.action == 'test.action'
        assert log.metadata == {'key': 'value'}

    def test_audit_log_ordering(self):
        """Test que les logs sont ordonnés par timestamp décroissant"""
        user = User.objects.create_user(username='testuser', password='testpass')
        
        log1 = AuditLog.objects.create(
            user=user,
            action='action1',
            resource_type='Test',
            resource_id='1',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0'
        )
        
        log2 = AuditLog.objects.create(
            user=user,
            action='action2',
            resource_type='Test',
            resource_id='2',
            ip_address='192.168.1.1',
            user_agent='Mozilla/5.0'
        )
        
        logs = AuditLog.objects.all()
        assert logs[0] == log2  # Plus récent en premier
        assert logs[1] == log1


@pytest.mark.django_db
class TestAuditHelpers:
    """Tests des helpers d'audit"""

    def test_get_client_ip_direct(self):
        """Test extraction IP directe"""
        factory = RequestFactory()
        request = factory.get('/', REMOTE_ADDR='192.168.1.100')
        
        ip = get_client_ip(request)
        assert ip == '192.168.1.100'

    def test_get_client_ip_forwarded(self):
        """Test extraction IP via X-Forwarded-For (proxy)"""
        factory = RequestFactory()
        request = factory.get('/', HTTP_X_FORWARDED_FOR='203.0.113.1, 192.168.1.1')
        
        ip = get_client_ip(request)
        assert ip == '203.0.113.1'  # Première IP de la liste

    def test_log_audit(self):
        """Test helper log_audit"""
        factory = RequestFactory()
        user = User.objects.create_user(username='testuser', password='testpass')
        request = factory.get('/')
        request.user = user
        request.session = {}
        
        log_audit(request, 'test.action', 'Resource', '123', {'extra': 'data'})
        
        log = AuditLog.objects.get(action='test.action')
        assert log.user == user
        assert log.resource_type == 'Resource'
        assert log.resource_id == '123'
        assert log.metadata == {'extra': 'data'}

    def test_log_authentication_attempt_success(self):
        """Test log tentative authentification réussie"""
        factory = RequestFactory()
        request = factory.post('/api/login/')
        request.session = {}
        
        log_authentication_attempt(request, success=True, username='testuser')
        
        log = AuditLog.objects.get(action='login.success')
        assert log.metadata['success'] is True
        # R5: username is hashed for RGPD compliance, not stored raw
        assert 'username_hash' in log.metadata

    def test_log_authentication_attempt_failed(self):
        """Test log tentative authentification échouée"""
        factory = RequestFactory()
        request = factory.post('/api/login/')
        request.session = {}
        
        log_authentication_attempt(request, success=False, username='baduser')
        
        log = AuditLog.objects.get(action='login.failed')
        assert log.metadata['success'] is False
        # R5: username is hashed for RGPD compliance, not stored raw
        assert 'username_hash' in log.metadata

    def test_log_data_access(self):
        """Test log accès données"""
        factory = RequestFactory()
        user = User.objects.create_user(username='testuser', password='testpass')
        request = factory.get('/api/copies/123/')
        request.user = user
        request.session = {}
        
        log_data_access(request, 'Copy', '123', 'download')
        
        log = AuditLog.objects.get(action='copy.download')
        assert log.resource_type == 'Copy'
        assert log.resource_id == '123'

    def test_log_workflow_action(self):
        """Test log action workflow"""
        factory = RequestFactory()
        user = User.objects.create_user(username='testuser', password='testpass')
        request = factory.post('/api/copies/123/lock/')
        request.user = user
        request.session = {}
        
        log_workflow_action(request, '123', 'lock', {'reason': 'correction'})
        
        log = AuditLog.objects.get(action='copy.lock')
        assert log.resource_id == '123'
        assert log.metadata == {'reason': 'correction'}

    def test_audit_log_student_session(self):
        """Test log avec session élève (pas de User Django)"""
        factory = RequestFactory()
        request = factory.get('/api/student/copies/')
        request.user = None
        request.session = {'student_id': 42}
        
        log_audit(request, 'student.access', 'Copy', 'list')
        
        log = AuditLog.objects.get(action='student.access')
        assert log.user is None
        assert log.student_id == 42
