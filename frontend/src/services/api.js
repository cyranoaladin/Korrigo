import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/api',
    withCredentials: true, // Important for session/cookie auth
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    },
    timeout: 10000,
});

// CSRF Token handling for Django
api.interceptors.request.use(config => {
    const getCookie = (name) => {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    };

    const csrftoken = getCookie('csrftoken');
    if (csrftoken) {
        config.headers['X-CSRFToken'] = csrftoken;
    }
    return config;
});

// Response interceptor for generic error handling if needed
api.interceptors.response.use(
    response => response,
    error => {
        return Promise.reject(error);
    }
);

// PRD-19: Multi-layer OCR API methods
export const ocrApi = {
    /**
     * Get top-k OCR candidates for a copy
     * @param {string} copyId - UUID of the copy
     * @returns {Promise} Array of top-5 student candidates with confidence scores
     */
    getCandidates: (copyId) => {
        return api.get(`/identification/copies/${copyId}/ocr-candidates/`);
    },

    /**
     * Select a candidate from the top-k list
     * @param {string} copyId - UUID of the copy
     * @param {number} rank - Rank of selected candidate (1-5)
     * @returns {Promise} Success response with assigned student
     */
    selectCandidate: (copyId, rank) => {
        return api.post(`/identification/copies/${copyId}/select-candidate/`, { rank });
    },

    /**
     * Perform OCR on a copy
     * @param {string} copyId - UUID of the copy
     * @returns {Promise} OCR result with suggestions
     */
    performOCR: (copyId) => {
        return api.post(`/identification/perform-ocr/${copyId}/`);
    }
};

export default api;
