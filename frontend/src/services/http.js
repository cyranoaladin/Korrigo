export const API_URL = import.meta.env.VITE_API_URL || ''

export function getCsrfToken() {
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';')
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim()
            if (cookie.substring(0, 'csrftoken'.length + 1) === 'csrftoken=') {
                return decodeURIComponent(cookie.substring('csrftoken'.length + 1))
            }
        }
    }
    return null
}

export function csrfHeader() {
    const token = getCsrfToken()
    return token ? { 'X-CSRFToken': token } : {}
}
