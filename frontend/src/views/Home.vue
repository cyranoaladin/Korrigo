<script setup>
import { useRouter } from 'vue-router'
import AppIcon from '../icons/AppIcon.vue'

const router = useRouter()

const navigateTo = (path) => {
  router.push(path)
}
</script>

<template>
  <div class="home-container">
    <header class="header">
      <div class="brand">
        <img 
          src="/images/logo_korrigo_pmf.svg" 
          alt="Korrigo PMF" 
          class="logo-img" 
        >
      </div>
      <p>
        Plateforme de Correction Numérique et de Consultation de Copies
      </p>
    </header>

    <main class="cards-container">
      <!-- Espace Élève -->
      <div 
        class="card student-card" 
        role="button" 
        tabindex="0"
        @click="navigateTo('/student/login')" 
      >
        <div class="card-icon-wrapper student-icon-bg">
          <AppIcon
            name="student"
            :size="32"
            class="card-icon-svg"
          />
        </div>
        <h2>Espace Élève</h2>
        <p>Consultez vos copies corrigées et vos résultats.</p>
        <button class="btn-link">
          <span>Accéder</span>
          <AppIcon
            name="chevron-right"
            :size="16"
          />
        </button>
      </div>

      <!-- Espace Enseignant -->
      <div 
        class="card teacher-card" 
        role="button" 
        tabindex="0"
        @click="navigateTo('/teacher/login')" 
      >
        <div class="card-icon-wrapper teacher-icon-bg">
          <AppIcon
            name="teacher"
            :size="32"
            class="card-icon-svg"
          />
        </div>
        <h2>Espace Enseignant</h2>
        <p>Corrigez, annotez et gérez vos examens.</p>
        <button class="btn-link">
          <span>Accéder</span>
          <AppIcon
            name="chevron-right"
            :size="16"
          />
        </button>
      </div>

      <!-- Espace Admin -->
      <div 
        class="card admin-card" 
        role="button" 
        tabindex="0"
        @click="navigateTo('/admin/login')" 
      >
        <div class="card-icon-wrapper admin-icon-bg">
          <AppIcon
            name="admin"
            :size="32"
            class="card-icon-svg"
          />
        </div>
        <h2>Administration</h2>
        <p>Gestion des examens, utilisateurs et imports.</p>
        <button class="btn-link">
          <span>Accéder</span>
          <AppIcon
            name="chevron-right"
            :size="16"
          />
        </button>
      </div>
    </main>

    <div class="info-link-container">
      <router-link
        to="/korrigo"
        class="info-link"
      >
        En savoir plus sur la plateforme Korrigo PMF
        <AppIcon
          name="chevron-right"
          :size="14"
        />
      </router-link>
    </div>

    <footer class="footer">
      <p>&copy; 2026 Lycée Pierre Mendès France - Tunis</p>
    </footer>
  </div>
</template>

<style scoped>
.home-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  font-family: 'Inter', sans-serif;
  color: #1e293b;
}

.header {
  text-align: center;
  margin-bottom: 3rem;
  margin-top: 2rem;
}

.brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.logo-img {
  height: 60px;
  width: auto;
}

h1 {
  font-size: 2.5rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
}

.subtitle {
  font-size: 1.1rem;
  color: #64748b;
  margin: 0;
}

.cards-container {
  display: flex;
  flex-wrap: wrap;
  gap: 2rem;
  justify-content: center;
  width: 100%;
  max-width: 1200px;
  padding: 0 1rem;
}

.card {
  background: white;
  border-radius: 16px;
  padding: 2rem;
  width: 100%;
  max-width: 300px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  transition: all 0.3s ease;
  cursor: pointer;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.card:hover {
  transform: translateY(-5px);
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

/* Premium icon wrapper replacing emoji-based .card-icon */
.card-icon-wrapper {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1rem;
}

.card-icon-svg {
  color: white;
}

.student-icon-bg {
  background: linear-gradient(135deg, #10b981, #059669);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}

.teacher-icon-bg {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.admin-icon-bg {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3);
}

.card h2 {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.card p {
  color: #64748b;
  font-size: 0.95rem;
  margin-bottom: 1.5rem;
  flex-grow: 1;
}

.btn-link {
  background: transparent;
  border: none;
  font-weight: 600;
  font-size: 1rem;
  cursor: pointer;
  padding: 0;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  transition: gap 0.2s ease;
}

.btn-link:hover {
  gap: 0.6rem;
}

.info-link-container {
  margin-top: 3rem;
  text-align: center;
}

.info-link {
  color: #3b82f6;
  text-decoration: none;
  font-weight: 500;
  font-size: 1rem;
  transition: color 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.info-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

/* Specific Card Styles */
.student-card { border-top: 4px solid #10b981; }
.student-card h2 { color: #047857; }
.student-card .btn-link { color: #059669; }

.teacher-card { border-top: 4px solid #3b82f6; }
.teacher-card h2 { color: #1d4ed8; }
.teacher-card .btn-link { color: #2563eb; }

.admin-card { border-top: 4px solid #ef4444; }
.admin-card h2 { color: #b91c1c; }
.admin-card .btn-link { color: #dc2626; }

.footer {
  margin-top: auto;
  padding: 2rem;
  color: #94a3b8;
  font-size: 0.875rem;
}

@media (max-width: 768px) {
  .cards-container {
    flex-direction: column;
    align-items: center;
  }
}
</style>
