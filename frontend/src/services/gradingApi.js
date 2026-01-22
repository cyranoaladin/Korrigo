import api from './api';

const MEDIA_URL = import.meta.env.VITE_MEDIA_URL || 'http://localhost:8000/media';

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
        return response.data;
    },

    async getCopy(id) {
        const response = await api.get(`/copies/${id}/`);
        return response.data;
    },

    async readyCopy(id) {
        const response = await api.post(`/copies/${id}/ready/`);
        return response.data;
    },

    async acquireLock(id, ttlSeconds = 600) {
        const response = await api.post(`/copies/${id}/lock/`, { ttl_seconds: ttlSeconds });
        return response.data;
    },

    async heartbeatLock(id, token) {
        const response = await api.post(`/copies/${id}/lock/heartbeat/`, { token });
        return response.data;
    },

    async releaseLock(id, token) {
        // Use 'data' property for DELETE body in axios
        const response = await api.delete(`/copies/${id}/lock/release/`, { data: { token } });
        return response.data;
    },

    async getLockStatus(id) {
        const response = await api.get(`/copies/${id}/lock/status/`);
        return response.data;
    },

    async finalizeCopy(id, token = null) {
        const config = token ? { headers: { 'X-Lock-Token': token } } : {};
        const response = await api.post(`/copies/${id}/finalize/`, {}, config);
        return response.data;
    },

    async createAnnotation(copyId, payload, token = null) {
        const config = token ? { headers: { 'X-Lock-Token': token } } : {};
        const response = await api.post(`/copies/${copyId}/annotations/`, payload, config);
        return response.data;
    },

    async listAnnotations(copyId) {
        const response = await api.get(`/copies/${copyId}/annotations/`);
        return response.data;
    },

    async deleteAnnotation(copyId, annotationId, token = null) {
        try {
            const config = token ? { headers: { 'X-Lock-Token': token } } : {};
            const response = await api.delete(`/annotations/${annotationId}/`, config);
            return true;
        } catch (err) {
            throw err;
        }
    },

    // --- Autosave / Drafts ---

    async getDraft(copyId) {
        const response = await api.get(`/copies/${copyId}/draft/`);
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
        const response = await api.put(`/copies/${copyId}/draft/`, body, config);
        return response.data;
    },

    async deleteDraft(copyId, token = null) {
        const config = token ? { headers: { 'X-Lock-Token': token } } : {};
        const response = await api.delete(`/copies/${copyId}/draft/`, config);
        return response.data;
    },

    async listAuditLogs(copyId) {
        const response = await api.get(`/copies/${copyId}/audit/`);
        return response.data;
    },

    getFinalPdfUrl(id) {
        return `${api.defaults.baseURL}/copies/${id}/final-pdf/`;
    }
};
