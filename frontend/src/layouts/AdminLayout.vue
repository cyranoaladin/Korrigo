<template>
  <div class="flex h-screen bg-gray-100">
    <AdminSidebar class="flex-shrink-0" />
    <main class="flex-1 overflow-y-auto">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import AdminSidebar from '../components/admin/AdminSidebar.vue'
</script>
