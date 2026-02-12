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
        return data;
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
        return data;
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
        return data;
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
    },

    // --- Per-question Scores ---

    async fetchScores(copyId) {
        const response = await api.get(`/grading/copies/${copyId}/scores/`);
        return response.data;
    },

    async saveScores(copyId, scoresData, finalComment = '') {
        const response = await api.put(`/grading/copies/${copyId}/scores/`, {
            scores_data: scoresData,
            final_comment: finalComment,
        });
        return response.data;
    },

    // --- Subject Variant (Sujet A/B) ---

    async updateSubjectVariant(copyId, variant) {
        const response = await api.patch(`/copies/${copyId}/`, { subject_variant: variant });
        return response.data;
    },

    // --- Corrector Stats ---

    async fetchExamStats(examId) {
        const response = await api.get(`/grading/exams/${examId}/stats/`);
        return response.data;
    },

    // --- Release Results ---

    async releaseResults(examId) {
        const response = await api.post(`/grading/exams/${examId}/release-results/`);
        return response.data;
    },

    async unreleaseResults(examId) {
        const response = await api.post(`/grading/exams/${examId}/unrelease-results/`);
        return response.data;
    },

    // --- Banque d'annotations ---

    async fetchSuggestions(examId, { exercise, question, q } = {}) {
        const params = {};
        if (exercise) params.exercise = exercise;
        if (question) params.question = question;
        if (q) params.q = q;
        const response = await api.get(`/grading/exams/${examId}/suggestions/`, { params });
        return response.data;
    },

    async fetchAnnotationTemplates(examId) {
        const response = await api.get(`/grading/exams/${examId}/annotation-templates/`);
        const data = response.data;
        if (data && typeof data === 'object' && Array.isArray(data.results)) {
            return data.results;
        }
        return data;
    },

    // --- Annotations personnelles ---

    async fetchMyAnnotations({ q, exercise } = {}) {
        const params = {};
        if (q) params.q = q;
        if (exercise) params.exercise = exercise;
        const response = await api.get('/grading/my-annotations/', { params });
        const data = response.data;
        if (data && typeof data === 'object' && Array.isArray(data.results)) {
            return data.results;
        }
        return data;
    },

    async createMyAnnotation(payload) {
        const response = await api.post('/grading/my-annotations/', payload);
        return response.data;
    },

    async updateMyAnnotation(id, payload) {
        const response = await api.patch(`/grading/my-annotations/${id}/`, payload);
        return response.data;
    },

    async deleteMyAnnotation(id) {
        await api.delete(`/grading/my-annotations/${id}/`);
        return true;
    },

    async useMyAnnotation(id) {
        const response = await api.post(`/grading/my-annotations/${id}/use/`);
        return response.data;
    },

    async autoSaveAnnotation(text, exerciseContext = null, questionContext = '') {
        const response = await api.post('/grading/my-annotations/auto-save/', {
            text,
            exercise_context: exerciseContext,
            question_context: questionContext,
        });
        return response.data;
    },
};
