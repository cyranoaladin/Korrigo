"""
Wrapper conditionnel pour django-ratelimit.

Permet de désactiver le rate limiting via RATELIMIT_ENABLE=False dans settings,
utile pour les tests E2E sans fragiliser la production.

Usage:
    from core.utils.ratelimit import maybe_ratelimit

    @method_decorator(maybe_ratelimit(key='ip', rate='5/15m', method='POST', block=True))
    def post(self, request):
        ...
"""
from django.conf import settings
from django_ratelimit.decorators import ratelimit


def maybe_ratelimit(*args, **kwargs):
    """
    Wrapper conditionnel pour le décorateur ratelimit.
    
    Si settings.RATELIMIT_ENABLE est False, le décorateur est bypassé.
    Par défaut (si non défini), le rate limiting est actif.
    
    Args:
        *args, **kwargs: Arguments passés à django_ratelimit.decorators.ratelimit
        
    Returns:
        Décorateur ratelimit ou passthrough selon la configuration
    """
    def decorator(viewfunc):
        if getattr(settings, "RATELIMIT_ENABLE", True):
            return ratelimit(*args, **kwargs)(viewfunc)
        return viewfunc
    return decorator
