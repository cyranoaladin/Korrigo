<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: null
  },
  questionId: {
    type: String,
    required: true
  },
  disabled: {
    type: Boolean,
    default: false
  },
  showLabels: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['update:modelValue', 'change'])

const localValue = ref(props.modelValue)

// Watch for external changes
watch(() => props.modelValue, (newValue) => {
  localValue.value = newValue
})

// Watch for internal changes
watch(localValue, (newValue) => {
  emit('update:modelValue', newValue)
  emit('change', newValue)
})

const options = computed(() => [
  { value: 'true', label: 'VRAI', class: 'true-option', shortcut: 'V' },
  { value: 'false', label: 'FAUX', class: 'false-option', shortcut: 'F' },
  { value: null, label: 'X', class: 'null-option', shortcut: 'X' }
])

const selectOption = (value) => {
  if (props.disabled) return
  
  // Toggle logic: clicking the same option deselects it
  if (localValue.value === value) {
    localValue.value = null
  } else {
    localValue.value = value
  }
}

// Keyboard shortcuts
const handleKeydown = (e) => {
  if (props.disabled) return
  
  const key = e.key.toUpperCase()
  const option = options.value.find(opt => opt.shortcut === key)
  
  if (option && (e.ctrlKey || e.metaKey)) {
    e.preventDefault()
    selectOption(option.value)
  }
}

// Expose method for parent component
const setValue = (value) => {
  localValue.value = value
}

defineExpose({
  setValue
})
</script>

<template>
  <div class="true-false-tool" @keydown="handleKeydown">
    <div class="tool-label" v-if="showLabels">
      Vrai/Faux:
    </div>
    
    <div class="options-container">
      <button
        v-for="option in options"
        :key="option.value"
        :class="[
          'option-button',
          option.class,
          { 
            active: localValue === option.value,
            disabled: disabled
          }
        ]"
        @click="selectOption(option.value)"
        :disabled="disabled"
        :title="`${option.label} (Ctrl+${option.shortcut})`"
      >
        <span class="option-text">{{ option.label }}</span>
        <span class="option-shortcut">{{ option.shortcut }}</span>
      </button>
    </div>
    
    <div class="help-text" v-if="showLabels">
      Ctrl+V/F/X pour sélectionner rapidement
    </div>
  </div>
</template>

<style scoped>
.true-false-tool {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.tool-label {
  font-weight: 500;
  color: #333;
  font-size: 0.9rem;
}

.options-container {
  display: flex;
  gap: 0.5rem;
}

.option-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 60px;
  height: 50px;
  border: 2px solid #ddd;
  border-radius: 8px;
  background: white;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.option-button:hover:not(.disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.option-button.active {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.option-button.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* True option - green */
.option-button.true-option {
  border-color: #4caf50;
}

.option-button.true-option:hover:not(.disabled) {
  background: #e8f5e8;
  border-color: #388e3c;
}

.option-button.true-option.active {
  background: #4caf50;
  color: white;
  border-color: #388e3c;
}

/* False option - red */
.option-button.false-option {
  border-color: #f44336;
}

.option-button.false-option:hover:not(.disabled) {
  background: #ffebee;
  border-color: #d32f2f;
}

.option-button.false-option.active {
  background: #f44336;
  color: white;
  border-color: #d32f2f;
}

/* Null option - gray */
.option-button.null-option {
  border-color: #9e9e9e;
}

.option-button.null-option:hover:not(.disabled) {
  background: #f5f5f5;
  border-color: #757575;
}

.option-button.null-option.active {
  background: #9e9e9e;
  color: white;
  border-color: #757575;
}

.option-text {
  font-weight: bold;
  font-size: 1rem;
  line-height: 1;
}

.option-shortcut {
  font-size: 0.7rem;
  opacity: 0.7;
  margin-top: 2px;
}

.help-text {
  font-size: 0.8rem;
  color: #666;
  font-style: italic;
}

/* Compact version for use in grids */
.true-false-tool.compact {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}

.true-false-tool.compact .tool-label {
  margin-right: 0.5rem;
}

.true-false-tool.compact .options-container {
  gap: 0.25rem;
}

.true-false-tool.compact .option-button {
  min-width: 40px;
  height: 35px;
}

.true-false-tool.compact .option-text {
  font-size: 0.9rem;
}

.true-false-tool.compact .help-text {
  display: none;
}

/* Large version for accessibility */
.true-false-tool.large .option-button {
  min-width: 80px;
  height: 60px;
}

.true-false-tool.large .option-text {
  font-size: 1.2rem;
}

.true-false-tool.large .option-shortcut {
  font-size: 0.8rem;
}

/* Focus styles */
.option-button:focus-visible {
  outline: 2px solid #1976d2;
  outline-offset: 2px;
}

/* Animation for selection */
@keyframes selectPulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

.option-button.active {
  animation: selectPulse 0.2s ease-out;
}
</style>
