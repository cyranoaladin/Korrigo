"""
Validator Antivirus (Optionnel - P3)
Scan antivirus avec ClamAV pour fichiers uploadés

Conformité: docs/security/MANUEL_SECURITE.md — Validation PDF / Antivirus

IMPORTANT: Ce validator est OPTIONNEL et nécessite:
- ClamAV installé sur le serveur (clamd daemon)
- Package Python pyclamd

Installation:
    # Ubuntu/Debian
    sudo apt-get install clamav clamav-daemon
    sudo systemctl start clamav-daemon
    
    # Python
    pip install pyclamd
"""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)

# Flag pour activer/désactiver le scan antivirus
ANTIVIRUS_ENABLED = False

try:
    import pyclamd
    ANTIVIRUS_ENABLED = True
except ImportError:
    logger.warning("pyclamd not installed. Antivirus scanning disabled.")


def validate_pdf_antivirus(value):
    """
    Scan antivirus du fichier PDF avec ClamAV.
    
    OPTIONNEL: Nécessite ClamAV installé et configuré.
    Si ClamAV n'est pas disponible, le validator est ignoré (graceful degradation).
    
    Args:
        value: UploadedFile instance
        
    Raises:
        ValidationError: Si un virus est détecté
    """
    if not ANTIVIRUS_ENABLED:
        logger.debug("Antivirus scanning disabled (pyclamd not available)")
        return
    
    try:
        # Connexion au daemon ClamAV
        cd = pyclamd.ClamdUnixSocket()
        
        # Vérifier que le daemon est accessible
        if not cd.ping():
            logger.warning("ClamAV daemon not responding. Skipping antivirus scan.")
            return
        
        # Lire le fichier
        value.seek(0)
        file_data = value.read()
        value.seek(0)
        
        # Scanner le contenu
        scan_result = cd.scan_stream(file_data)
        
        if scan_result:
            # Virus détecté
            virus_name = scan_result.get('stream', ['UNKNOWN'])[1]
            logger.error(f"Virus detected in uploaded file: {virus_name}")
            
            raise ValidationError(
                _(f'Virus détecté: {virus_name}. Le fichier a été rejeté.'),
                code='virus_detected'
            )
        
        # Pas de virus détecté
        logger.info("File scanned successfully. No virus detected.")
        
    except ValidationError:
        # Re-raise ValidationError (virus détecté)
        raise
    except Exception as e:
        # Erreur de scan (daemon non disponible, etc.)
        # On log mais on ne bloque pas l'upload (graceful degradation)
        logger.warning(f"Antivirus scan failed: {e}. Allowing upload.")


def get_antivirus_status():
    """
    Retourne le statut du système antivirus.
    
    Returns:
        dict: {
            'enabled': bool,
            'available': bool,
            'version': str or None
        }
    """
    status = {
        'enabled': ANTIVIRUS_ENABLED,
        'available': False,
        'version': None
    }
    
    if not ANTIVIRUS_ENABLED:
        return status
    
    try:
        cd = pyclamd.ClamdUnixSocket()
        if cd.ping():
            status['available'] = True
            status['version'] = cd.version()
    except Exception as e:
        logger.debug(f"Could not get ClamAV status: {e}")
    
    return status
