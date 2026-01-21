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

    async lockCopy(id) {
        const response = await api.post(`/copies/${id}/lock/`);
        return response.data;
    },

    async unlockCopy(id) {
        const response = await api.post(`/copies/${id}/unlock/`);
        return response.data;
    },

    async finalizeCopy(id) {
        const response = await api.post(`/copies/${id}/finalize/`);
        return response.data;
    },

    async createAnnotation(copyId, payload) {
        const response = await api.post(`/copies/${copyId}/annotations/`, payload);
        return response.data;
    },

    async listAnnotations(copyId) {
        const response = await api.get(`/copies/${copyId}/annotations/`);
        return response.data;
    },

    async deleteAnnotation(copyId, annotationId) {
        try {
            // Priority: Direct Delete Endpoint
            const response = await api.delete(`/annotations/${annotationId}/`);
            return true; // 204 or 200 is success
        } catch (err) {
            // Fallback: If direct endpoint is missing (404), try nested if structured that way
            // or just rethrow if we know our backend only has one.
            // For robustness P0, if we suspect backend might change, we could try fallback.
            // Currently backend urls.py confirms /annotations/<uuid>/
            // So we rethrow actual errors (403, 500)
            throw err;
        }
    },

    async listAuditLogs(copyId) {
        const response = await api.get(`/copies/${copyId}/audit/`);
        return response.data;
    },

    getFinalPdfUrl(id) {
        return `${api.defaults.baseURL}/copies/${id}/final-pdf/`;
    }
};
