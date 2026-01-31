const ERROR_MESSAGES = {
    NETWORK_ERROR: 'Impossible de se connecter au serveur. Vérifiez votre connexion internet.',
    TIMEOUT: 'La requête a pris trop de temps. Veuillez réessayer.',
    INVALID_CREDENTIALS: 'Identifiants incorrects. Veuillez réessayer.',
    UNAUTHORIZED: 'Accès non autorisé. Veuillez vous reconnecter.',
    FORBIDDEN: 'Vous n\'avez pas les permissions nécessaires.',
    NOT_FOUND: 'Ressource introuvable.',
    SERVER_ERROR: 'Erreur serveur. Veuillez réessayer plus tard.',
    UNKNOWN_ERROR: 'Une erreur inattendue s\'est produite.',
    SESSION_EXPIRED: 'Votre session a expiré. Veuillez vous reconnecter.',
    CSRF_ERROR: 'Erreur de sécurité. La page va se recharger.',
};

export function getErrorMessage(error) {
    if (!error) {
        return ERROR_MESSAGES.UNKNOWN_ERROR;
    }

    if (!error.response) {
        if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
            return ERROR_MESSAGES.TIMEOUT;
        }
        return ERROR_MESSAGES.NETWORK_ERROR;
    }

    const status = error.response.status;
    const data = error.response.data;

    switch (status) {
        case 400:
            if (data?.detail) return data.detail;
            if (data?.error) return data.error;
            return 'Données invalides. Veuillez vérifier les informations saisies.';
        
        case 401:
            if (data?.detail?.toLowerCase().includes('credentials')) {
                return ERROR_MESSAGES.INVALID_CREDENTIALS;
            }
            return ERROR_MESSAGES.UNAUTHORIZED;
        
        case 403:
            if (data?.detail?.toLowerCase().includes('csrf')) {
                return ERROR_MESSAGES.CSRF_ERROR;
            }
            return ERROR_MESSAGES.FORBIDDEN;
        
        case 404:
            return ERROR_MESSAGES.NOT_FOUND;
        
        case 500:
        case 502:
        case 503:
        case 504:
            return ERROR_MESSAGES.SERVER_ERROR;
        
        default:
            if (data?.detail) return data.detail;
            if (data?.error) return data.error;
            return ERROR_MESSAGES.UNKNOWN_ERROR;
    }
}

export default { ERROR_MESSAGES, getErrorMessage };
