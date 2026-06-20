import api from './api'

function normalize(data) {
  if (data && typeof data === 'object' && Array.isArray(data.results)) return data.results
  return data
}

export default {
  async listStudentPeerReviews() {
    const response = await api.get('/students/peer-reviews/')
    return normalize(response.data)
  },

  async getStudentPeerReview(id) {
    const response = await api.get(`/students/peer-reviews/${id}/`)
    return response.data
  },

  async saveStudentPeerReview(id, payload) {
    const response = await api.patch(`/students/peer-reviews/${id}/save/`, payload)
    return response.data
  },

  async finalizeStudentPeerReview(id) {
    const response = await api.post(`/students/peer-reviews/${id}/finalize/`)
    return response.data
  },

  async listTeacherPeerReviews(examId) {
    const response = await api.get(`/grading/teacher/exams/${examId}/peer-reviews/`)
    return normalize(response.data)
  },

  async getTeacherPeerReview(id) {
    const response = await api.get(`/grading/teacher/peer-reviews/${id}/`)
    return response.data
  },
}
