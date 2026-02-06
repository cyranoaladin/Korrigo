import api from './api';

const MEDIA_URL = import.meta.env.VITE_MEDIA_URL || '/media';

export default {
    /**
     * Helper to get full media URL robustly
     */
    getMediaUrl(path) {
        if (!path) return '';
        if (path.startsWith('http')) return path;

        // Normalize Base and Path
        const base = MEDIA_URL.replace(/\/+$/, ''); // Remove trailing slash
        const cleanPath = path.startsWith('/') ? path.substring(1) : path;

        return `${base}/${cleanPath}`;
    },

    async listCopies(params = {}) {
        const response = await api.get('/copies/', { params });
        // Handle DRF pagination: extract results array if paginated response
        const data = response.data;
        if (data && typeof data === 'object' && Array.isArray(data.results)) {
            return data.results;
        }
        return data;
    },

    async getCopy(id) {
        const response = await api.get(`/copies/${id}/`);
        return response.data;
    },

    async readyCopy(id) {
        const response = await api.post(`/grading/copies/${id}/ready/`);
        return response.data;
    },

    async acquireLock(id, ttlSeconds = 600) {
        const response = await api.post(`/grading/copies/${id}/lock/`, { ttl_seconds: ttlSeconds });
        return response.data;
    },

    async heartbeatLock(id, token) {
        const response = await api.post(`/grading/copies/${id}/lock/heartbeat/`, { token });
        return response.data;
    },

    async releaseLock(id, token) {
        // Use 'data' property for DELETE body in axios
        const response = await api.delete(`/grading/copies/${id}/lock/release/`, { data: { token } });
        return response.data;
    },

    async getLockStatus(id) {
        const response = await api.get(`/grading/copies/${id}/lock/status/`);
        return response.data;
    },

    async finalizeCopy(id, token = null) {
        const config = token ? { headers: { 'X-Lock-Token': token } } : {};
        const response = await api.post(`/grading/copies/${id}/finalize/`, {}, config);
        return response.data;
    },

    async createAnnotation(copyId, payload, token = null) {
        const config = token ? { headers: { 'X-Lock-Token': token } } : {};
        const response = await api.post(`/grading/copies/${copyId}/annotations/`, payload, config);
        return response.data;
    },

    async listAnnotations(copyId) {
        const response = await api.get(`/grading/copies/${copyId}/annotations/`);
        // Handle DRF pagination: extract results array if paginated response
        const data = response.data;
        if (data && typeof data === 'object' && Array.isArray(data.results)) {
            return data.results;
        }
        return Array.isArray(data) ? data : [];
    },

    async deleteAnnotation(copyId, annotationId, token = null) {
        try {
            const config = token ? { headers: { 'X-Lock-Token': token } } : {};
            const response = await api.delete(`/grading/annotations/${annotationId}/`, config);
            return true;
        } catch (err) {
            throw err;
        }
    },

    // --- Autosave / Drafts ---

    async getDraft(copyId) {
        const response = await api.get(`/grading/copies/${copyId}/draft/`);
        // 204 returns null/undefined data usually, or empty string. 
        // Axios handles 204 by returning response with empty data.
        if (response.status === 204) return null;
        return response.data;
    },

    async saveDraft(copyId, payload, token, clientId = null) {
        const config = token ? { headers: { 'X-Lock-Token': token } } : {};
        const body = {
            payload,
            token,
            client_id: clientId
        };
        const response = await api.put(`/grading/copies/${copyId}/draft/`, body, config);
        return response.data;
    },

    async deleteDraft(copyId, token = null) {
        const config = token ? { headers: { 'X-Lock-Token': token } } : {};
        const response = await api.delete(`/grading/copies/${copyId}/draft/`, config);
        return response.data;
    },

    async listAuditLogs(copyId) {
        const response = await api.get(`/grading/copies/${copyId}/audit/`);
        // Handle DRF pagination: extract results array if paginated response
        const data = response.data;
        if (data && typeof data === 'object' && Array.isArray(data.results)) {
            return data.results;
        }
        return Array.isArray(data) ? data : [];
    },

    getFinalPdfUrl(id) {
        return `${api.defaults.baseURL}/grading/copies/${id}/final-pdf/`;
    },

    async fetchRemarks(copyId) {
        const response = await api.get(`/grading/copies/${copyId}/remarks/`);
        const data = response.data;
        if (data && typeof data === 'object' && Array.isArray(data.results)) {
            return data.results;
        }
        // Ensure we always return an array
        return Array.isArray(data) ? data : [];
    },

    async saveRemark(copyId, questionId, remark, token = null) {
        const config = token ? { headers: { 'X-Lock-Token': token } } : {};
        const response = await api.post(
            `/grading/copies/${copyId}/remarks/`,
            { question_id: questionId, remark },
            config
        );
        return response.data;
    },

    async saveQuestionScore(copyId, questionId, score, token = null) {
        const config = token ? { headers: { 'X-Lock-Token': token } } : {};
        const response = await api.post(
            `/grading/copies/${copyId}/scores/`,
            { question_id: questionId, score },
            config
        );
        return response.data;
    },

    async fetchQuestionScores(copyId) {
        const response = await api.get(`/grading/copies/${copyId}/scores/`);
        // Handle DRF pagination: extract results array if paginated response
        const data = response.data;
        if (data && typeof data === 'object' && Array.isArray(data.results)) {
            return data.results;
        }
        // Ensure we always return an array
        return Array.isArray(data) ? data : [];
    },

    async fetchGlobalAppreciation(copyId) {
        const response = await api.get(`/grading/copies/${copyId}/global-appreciation/`);
        return response.data;
    },

    async saveGlobalAppreciation(copyId, appreciation, token = null) {
        const config = token ? { headers: { 'X-Lock-Token': token } } : {};
        const response = await api.patch(
            `/grading/copies/${copyId}/global-appreciation/`,
            { global_appreciation: appreciation },
            config
        );
        return response.data;
    }
};
