import api from './api'

export const bilanService = {
  // Lister tous les bilans
  async list() {
    const response = await api.get('/bilan/')
    return response.data
  },

  // Générer un nouveau bilan
  async generate(payload) {
    const response = await api.post('/bilan/generate/', payload)
    return response.data
  },

  // Récupérer les détails d'un bilan
  async get(id) {
    const response = await api.get(`/bilan/${id}/`)
    return response.data
  },

  // Télécharger le PDF d'un bilan
  async downloadPDF(id) {
    const response = await api.get(`/bilan/${id}/pdf/`, {
      responseType: 'blob'
    })
    return response
  },

  // Supprimer un bilan
  async delete(id) {
    const response = await api.delete(`/bilan/${id}/`)
    return response.data
  },

  // Obtenir les statistiques système
  async getStats() {
    const response = await api.get('/bilan/stats/')
    return response.data
  }
}
