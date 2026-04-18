"""
Wrapper conditionnel pour django-ratelimit.

Permet de désactiver le rate limiting via RATELIMIT_ENABLE=False dans settings,
utile pour les tests E2E sans fragiliser la production.

Usage:
    from core.utils.ratelimit import maybe_ratelimit, get_real_ip

    @method_decorator(maybe_ratelimit(key=get_real_ip, rate='5/15m', method='POST', block=True))
    def post(self, request):
        ...
"""
from django.conf import settings
from django_ratelimit.decorators import ratelimit


def get_real_ip(group, request):
    """
    Extrait l'IP réelle du client derrière un proxy Nginx.

    BUG-01 FIX: django-ratelimit avec key='ip' lit REMOTE_ADDR, qui vaut
    l'IP interne de Nginx (172.x.x.x) et non l'IP réelle de l'élève.
    Résultat : tous les élèves partagent le même compteur de rate limit.

    Stratégie de résolution (par ordre de fiabilité) :
    1. X-Real-IP  — positionné par Nginx à $remote_addr (IP directe du client)
    2. X-Forwarded-For — premier élément de la chaîne (le plus à gauche = client originel)
    3. REMOTE_ADDR — fallback (IP du dernier hop, souvent le proxy interne Docker)
    """
    # X-Real-IP est le plus fiable : Nginx le force à $remote_addr
    x_real_ip = request.META.get('HTTP_X_REAL_IP', '').strip()
    if x_real_ip:
        return x_real_ip

    # X-Forwarded-For : prendre le premier IP non vide (IP la plus à gauche = client)
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '').strip()
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()

    # Fallback : REMOTE_ADDR (peut être l'IP interne Docker derrière Nginx)
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


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
