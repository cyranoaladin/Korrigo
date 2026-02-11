<script setup>
defineProps({
  message: {
    type: String,
    default: 'Chargement en cours...'
  }
})
</script>

<template>
  <div class="loading-overlay">
    <div class="spinner-container">
      <div class="spinner" />
      <p class="loading-message">
        {{ message }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.loading-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 9999;
}

.spinner-container {
    text-align: center;
}

.spinner {
    border: 4px solid rgba(255, 255, 255, 0.3);
    border-top: 4px solid white;
    border-radius: 50%;
    width: 50px;
    height: 50px;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

.loading-message {
    color: white;
    font-size: 1rem;
    font-weight: 500;
    margin: 0;
}
</style>
