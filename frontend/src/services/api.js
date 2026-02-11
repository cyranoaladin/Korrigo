import axios from 'axios';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/api',
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    },
    timeout: 30000,
});

// P4 FIX: Extended timeout for upload requests (120s)
const UPLOAD_TIMEOUT = 120000;

const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1000;

function shouldRetry(error, config) {
    if (!error || config.__retryCount >= MAX_RETRIES) {
        return false;
    }

    // P5 FIX: NEVER retry mutating requests (POST/PUT/PATCH/DELETE) to prevent duplicates
    const method = (config.method || 'get').toLowerCase();
    if (method !== 'get') {
        return false;
    }

    // Only retry GET requests on network errors or 5xx
    if (!error.response) {
        return true;
    }

    const status = error.response.status;
    if (status >= 500 && status < 600) {
        return true;
    }

    return false;
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

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

api.interceptors.response.use(
    response => response,
    async error => {
        const config = error.config;

        if (!config) {
            return Promise.reject(error);
        }

        config.__retryCount = config.__retryCount || 0;

        if (error.response?.status === 401) {
            const { useAuthStore } = await import('../stores/auth');
            const router = (await import('../router')).default;
            const authStore = useAuthStore();
            
            authStore.user = null;
            if (router.currentRoute.value.path !== '/') {
                router.push('/');
            }
            
            return Promise.reject(error);
        }

        if (error.response?.status === 403) {
            const errorMessage = error.response?.data?.detail || '';
            if (errorMessage.toLowerCase().includes('csrf') && !config.__csrfRetried) {
                config.__csrfRetried = true;
                window.location.reload();
                return new Promise(() => {});
            }
        }

        if (shouldRetry(error, config)) {
            config.__retryCount += 1;
            const delayMs = RETRY_DELAY_MS * Math.pow(2, config.__retryCount - 1);
            await sleep(delayMs);
            return api.request(config);
        }

        return Promise.reject(error);
    }
);

export { UPLOAD_TIMEOUT };
export default api;
