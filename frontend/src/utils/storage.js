/**
 * Utilitaires localStorage avec TTL et gestion quota
 * Conformité: Phase 3 - Review sécurité frontend
 */

const DEFAULT_TTL = 7 * 24 * 60 * 60 * 1000; // 7 jours en millisecondes

/**
 * Stocke un item dans localStorage avec TTL (Time To Live)
 * 
 * @param {string} key - Clé de stockage
 * @param {any} value - Valeur à stocker (sera JSON.stringify)
 * @param {number} ttl - Durée de vie en millisecondes (défaut: 7 jours)
 * @throws {Error} Si quota dépassé après nettoyage
 */
export function setItemWithTTL(key, value, ttl = DEFAULT_TTL) {
    const item = {
        data: value,
        timestamp: Date.now(),
        ttl: ttl
    };
    
    try {
        localStorage.setItem(key, JSON.stringify(item));
    } catch (e) {
        if (e.name === 'QuotaExceededError') {
            console.warn('localStorage quota exceeded. Cleaning old drafts...');
            
            // Nettoyer les anciens brouillons
            cleanExpiredDrafts();
            
            // Retry après nettoyage
            try {
                localStorage.setItem(key, JSON.stringify(item));
            } catch (retryError) {
                // Si toujours pas de place, supprimer le plus ancien
                removeOldestDraft();
                localStorage.setItem(key, JSON.stringify(item));
            }
        } else {
            throw e;
        }
    }
}

/**
 * Récupère un item depuis localStorage en vérifiant le TTL
 * 
 * @param {string} key - Clé de stockage
 * @returns {any|null} - Valeur stockée ou null si expiré/absent
 */
export function getItemWithTTL(key) {
    try {
        const itemStr = localStorage.getItem(key);
        if (!itemStr) {
            return null;
        }
        
        const item = JSON.parse(itemStr);
        
        // Vérifier si l'item a expiré
        if (Date.now() > item.timestamp + item.ttl) {
            console.log(`Item ${key} expired. Removing...`);
            localStorage.removeItem(key);
            return null;
        }
        
        return item.data;
    } catch (e) {
        console.error(`Error reading ${key} from localStorage:`, e);
        return null;
    }
}

/**
 * Supprime un item du localStorage
 * 
 * @param {string} key - Clé de stockage
 */
export function removeItem(key) {
    try {
        localStorage.removeItem(key);
    } catch (e) {
        console.error(`Error removing ${key} from localStorage:`, e);
    }
}

/**
 * Nettoie tous les items expirés du localStorage
 * Appelé automatiquement en cas de quota exceeded
 */
export function cleanExpiredDrafts() {
    const now = Date.now();
    let cleanedCount = 0;
    
    // Parcourir tous les items localStorage
    Object.keys(localStorage).forEach(key => {
        // Ne traiter que les brouillons (clés commençant par 'draft_')
        if (key.startsWith('draft_')) {
            try {
                const itemStr = localStorage.getItem(key);
                const item = JSON.parse(itemStr);
                
                // Vérifier expiration
                if (item.timestamp && item.ttl && now > item.timestamp + item.ttl) {
                    localStorage.removeItem(key);
                    cleanedCount++;
                }
            } catch (e) {
                // Item corrompu, le supprimer
                localStorage.removeItem(key);
                cleanedCount++;
            }
        }
    });
    
    console.log(`Cleaned ${cleanedCount} expired draft(s)`);
    return cleanedCount;
}

/**
 * Supprime le brouillon le plus ancien pour libérer de l'espace
 */
function removeOldestDraft() {
    let oldestKey = null;
    let oldestTimestamp = Infinity;
    
    Object.keys(localStorage).forEach(key => {
        if (key.startsWith('draft_')) {
            try {
                const itemStr = localStorage.getItem(key);
                const item = JSON.parse(itemStr);
                
                if (item.timestamp && item.timestamp < oldestTimestamp) {
                    oldestTimestamp = item.timestamp;
                    oldestKey = key;
                }
            } catch (e) {
                // Ignorer items corrompus
            }
        }
    });
    
    if (oldestKey) {
        console.log(`Removing oldest draft: ${oldestKey}`);
        localStorage.removeItem(oldestKey);
    }
}

/**
 * Obtient des statistiques sur l'utilisation du localStorage
 * 
 * @returns {object} Statistiques d'utilisation
 */
export function getStorageStats() {
    let totalSize = 0;
    let draftCount = 0;
    let expiredCount = 0;
    const now = Date.now();
    
    Object.keys(localStorage).forEach(key => {
        const itemStr = localStorage.getItem(key);
        totalSize += itemStr.length;
        
        if (key.startsWith('draft_')) {
            draftCount++;
            
            try {
                const item = JSON.parse(itemStr);
                if (item.timestamp && item.ttl && now > item.timestamp + item.ttl) {
                    expiredCount++;
                }
            } catch (e) {
                // Ignorer
            }
        }
    });
    
    return {
        totalSizeKB: (totalSize / 1024).toFixed(2),
        draftCount,
        expiredCount,
        estimatedQuotaMB: 5, // Généralement 5-10 MB par domaine
    };
}

/**
 * Initialise le nettoyage automatique au démarrage de l'application
 * À appeler dans main.js
 */
export function initStorageCleanup() {
    console.log('Initializing localStorage cleanup...');
    const cleaned = cleanExpiredDrafts();
    const stats = getStorageStats();
    console.log('localStorage stats:', stats);
}
