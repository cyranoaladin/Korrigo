<template>
  <div class="min-h-screen bg-gray-50 text-neutralDark flex flex-col font-sans">
    <Navbar />
    <main class="flex-1 w-full">
      <router-view />
    </main>
    <Footer />
  </div>
</template>

<script setup>
import Navbar from '../components/Navbar.vue'
import Footer from '../components/Footer.vue'
</script>
