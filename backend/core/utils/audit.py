"""
Audit Trail Utilities
Conformité RGPD/CNIL - Traçabilité des actions critiques

Référence: .antigravity/rules/01_security_rules.md § 7.3
"""
import logging
from django.utils import timezone
from django.http import HttpRequest

audit_logger = logging.getLogger('audit')


def get_client_ip(request: HttpRequest) -> str:
    """
    Extrait l'adresse IP réelle du client en tenant compte des proxies.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '0.0.0.0')  # nosec B104 - Fallback IP value, not binding
    return ip


def log_audit(request: HttpRequest, action: str, resource_type: str, resource_id, metadata: dict = None):
    """
    Log une action pour audit trail.
    
    Args:
        request: HttpRequest Django
        action: Action effectuée (ex: 'login.success', 'copy.download')
        resource_type: Type de ressource (ex: 'Copy', 'Exam', 'Student')
        resource_id: ID de la ressource (UUID, int, etc.)
        metadata: Données contextuelles additionnelles (dict)
    
    Examples:
        >>> log_audit(request, 'login.success', 'User', user.id)
        >>> log_audit(request, 'copy.download', 'Copy', copy.id, {'anonymous_id': copy.anonymous_id})
    """
    from core.models import AuditLog
    
    user = getattr(request, 'user', None)
    student_id = request.session.get('student_id')

    # Créer l'entrée d'audit
    audit_entry = AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        student_id=student_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id),
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],  # Limite pour éviter overflow
        metadata=metadata or {}
    )

    # Log structuré pour monitoring externe (Sentry, CloudWatch, etc.)
    audit_logger.info(
        "audit",
        extra={
            'action': action,
            'resource': f"{resource_type}:{resource_id}",
            'user': user.username if user and user.is_authenticated else 'anonymous',
            'student_id': student_id,
            'ip': get_client_ip(request),
            'timestamp': timezone.now().isoformat()
        }
    )
    
    return audit_entry


def log_authentication_attempt(request: HttpRequest, success: bool, username: str = None, student_id: int = None):
    """
    Log spécifique pour les tentatives d'authentification.
    
    Args:
        request: HttpRequest Django
        success: True si authentification réussie
        username: Nom d'utilisateur (prof/admin)
        student_id: ID élève si authentification élève
    """
    action = 'login.success' if success else 'login.failed'
    resource_type = 'Student' if student_id else 'User'
    resource_id = student_id if student_id else username or 'unknown'
    
    metadata = {
        'success': success,
        'username': username,
        'student_id': student_id,
    }
    
    return log_audit(request, action, resource_type, resource_id, metadata)


def log_data_access(request: HttpRequest, resource_type: str, resource_id, action_detail: str = 'view'):
    """
    Log spécifique pour l'accès aux données sensibles.
    
    Args:
        request: HttpRequest Django
        resource_type: Type de ressource accédée
        resource_id: ID de la ressource
        action_detail: Détail de l'action ('view', 'download', 'export')
    """
    action = f"{resource_type.lower()}.{action_detail}"
    return log_audit(request, action, resource_type, resource_id)


def log_workflow_action(request: HttpRequest, copy_id, workflow_action: str, metadata: dict = None):
    """
    Log spécifique pour les actions de workflow de correction.
    
    Args:
        request: HttpRequest Django
        copy_id: ID de la copie
        workflow_action: Action workflow ('lock', 'unlock', 'finalize', 'validate')
        metadata: Métadonnées additionnelles
    """
    action = f"copy.{workflow_action}"
    return log_audit(request, action, 'Copy', copy_id, metadata)
