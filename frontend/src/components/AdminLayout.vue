<script setup>
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const handleLogout = async () => {
    await authStore.logout()
    router.push('/login')
}

const navItems = [
    { name: 'AdminDashboard', label: 'Gestion Examens', icon: '📋' },
    { name: 'UserManagement', label: 'Utilisateurs', icon: '👥' },
    { name: 'Settings', label: 'Paramètres', icon: '⚙️' },
]

const isActive = (name) => route.name === name
</script>

<template>
  <div class="admin-layout">
    <nav class="sidebar">
      <div class="logo" @click="router.push({ name: 'AdminDashboard' })">
        <img
          src="/images/Korrigo.png"
          alt="Korrigo Logo"
          class="sidebar-logo-img"
        >
        <span>Korrigo</span>
      </div>
      
      <ul class="nav-links">
        <li 
          v-for="item in navItems" 
          :key="item.name"
          :class="{ active: isActive(item.name) }"
          @click="router.push({ name: item.name })"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          {{ item.label }}
        </li>
      </ul>
      
      <div class="sidebar-footer">
        <div class="user-badge">
          <span class="user-icon">👤</span>
          <span class="user-name">{{ authStore.user?.username }}</span>
          <span class="user-role">({{ authStore.user?.role }})</span>
        </div>
        
        <button
          data-testid="logout-button"
          class="logout-btn"
          @click="handleLogout"
        >
          🚪 Déconnexion
        </button>
        
        <div class="attribution">
          Concepteur : Alaeddine BEN RHOUMA<br>Labo Maths ERT
        </div>
      </div>
    </nav>
        
    <main class="main-content">
      <header class="top-bar">
        <button class="back-btn" @click="router.back()" title="Retour">
          ← Retour
        </button>
        <div class="breadcrumb">
          <span @click="router.push({ name: 'AdminDashboard' })">Accueil</span>
          <span v-if="route.name !== 'AdminDashboard'"> / {{ route.meta.title || route.name }}</span>
        </div>
      </header>
      
      <div class="page-content">
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
.admin-layout {
  display: flex;
  min-height: 100vh;
  background: #f5f7fa;
}

.sidebar {
  width: 240px;
  background: linear-gradient(180deg, #1a237e 0%, #283593 100%);
  color: white;
  display: flex;
  flex-direction: column;
  position: fixed;
  height: 100vh;
  z-index: 100;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  cursor: pointer;
  transition: background 0.2s;
}

.logo:hover {
  background: rgba(255,255,255,0.1);
}

.sidebar-logo-img {
  width: 40px;
  height: 40px;
  border-radius: 8px;
}

.logo span {
  font-size: 1.4rem;
  font-weight: 700;
}

.nav-links {
  list-style: none;
  padding: 16px 0;
  margin: 0;
  flex: 1;
}

.nav-links li {
  padding: 14px 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.nav-links li:hover {
  background: rgba(255,255,255,0.1);
}

.nav-links li.active {
  background: rgba(255,255,255,0.15);
  border-left-color: #64b5f6;
  font-weight: 600;
}

.nav-icon {
  font-size: 1.2rem;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid rgba(255,255,255,0.1);
}

.user-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  background: rgba(255,255,255,0.1);
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 0.9rem;
}

.user-icon {
  font-size: 1.2rem;
}

.user-role {
  opacity: 0.7;
  font-size: 0.8rem;
}

.logout-btn {
  width: 100%;
  padding: 12px;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.2);
  color: white;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.95rem;
  transition: all 0.2s;
}

.logout-btn:hover {
  background: rgba(239, 83, 80, 0.8);
  border-color: transparent;
}

.attribution {
  margin-top: 16px;
  font-size: 0.7rem;
  opacity: 0.5;
  text-align: center;
  line-height: 1.4;
}

.main-content {
  flex: 1;
  margin-left: 240px;
  display: flex;
  flex-direction: column;
}

.top-bar {
  background: white;
  padding: 12px 24px;
  display: flex;
  align-items: center;
  gap: 20px;
  border-bottom: 1px solid #e0e0e0;
  position: sticky;
  top: 0;
  z-index: 50;
}

.back-btn {
  padding: 8px 16px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.back-btn:hover {
  background: #e0e0e0;
}

.breadcrumb {
  font-size: 0.95rem;
  color: #666;
}

.breadcrumb span {
  cursor: pointer;
}

.breadcrumb span:hover {
  color: #1a237e;
  text-decoration: underline;
}

.page-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
}
</style>
