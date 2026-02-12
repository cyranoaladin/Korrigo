<script setup>
import { ref, watch, computed } from 'vue'
import gradingApi from '../services/gradingApi'

const props = defineProps({
    examId: { type: String, required: true },
    exerciseNumber: { type: [Number, String], default: null },
    questionNumber: { type: String, default: null },
    visible: { type: Boolean, default: false },
})

const emit = defineEmits(['insert', 'close'])

const searchQuery = ref('')
const suggestions = ref({ official: [], personal: [] })
const isLoading = ref(false)
const activeTab = ref('official')
const searchTimeout = ref(null)

const fetchSuggestions = async () => {
    if (!props.examId) return
    isLoading.value = true
    try {
        suggestions.value = await gradingApi.fetchSuggestions(props.examId, {
            exercise: props.exerciseNumber || undefined,
            question: props.questionNumber || undefined,
            q: searchQuery.value || undefined,
        })
    } catch (err) {
        console.error('Erreur chargement suggestions:', err)
    } finally {
        isLoading.value = false
    }
}

watch(() => [props.visible, props.exerciseNumber, props.questionNumber], () => {
    if (props.visible) fetchSuggestions()
}, { immediate: true })

watch(searchQuery, () => {
    clearTimeout(searchTimeout.value)
    searchTimeout.value = setTimeout(fetchSuggestions, 300)
})

const criterionColors = {
    method: { bg: '#eff6ff', border: '#3b82f6', icon: '🔵' },
    result: { bg: '#f0fdf4', border: '#22c55e', icon: '🟢' },
    justification: { bg: '#fefce8', border: '#eab308', icon: '🟡' },
    redaction: { bg: '#faf5ff', border: '#a855f7', icon: '🟣' },
    error_typique: { bg: '#fef2f2', border: '#ef4444', icon: '🔴' },
    bonus: { bg: '#f0fdf4', border: '#16a34a', icon: '✅' },
    plafond: { bg: '#fff7ed', border: '#f97316', icon: '⚠️' },
}

const severityLabels = {
    info: 'Info',
    mineur: 'Mineur',
    majeur: 'Majeur',
    critique: 'Critique',
}

const getColor = (type) => criterionColors[type] || criterionColors.method

const handleInsert = (text, source, id) => {
    emit('insert', { text, source, id })
    if (source === 'personal' && id) {
        gradingApi.useMyAnnotation(id).catch(() => {})
    }
}

const contextLabel = computed(() => {
    const parts = []
    if (props.exerciseNumber) parts.push(`Ex ${props.exerciseNumber}`)
    if (props.questionNumber) parts.push(`Q${props.questionNumber}`)
    return parts.length ? parts.join(' – ') : 'Toutes les questions'
})
</script>

<template>
  <div
    v-if="visible"
    class="suggestions-panel"
  >
    <div class="suggestions-header">
      <div class="suggestions-title">
        <span class="suggestions-icon">💡</span>
        <span>Suggestions</span>
        <span class="context-badge">{{ contextLabel }}</span>
      </div>
      <button
        class="btn-close-panel"
        title="Fermer"
        @click="$emit('close')"
      >
        ×
      </button>
    </div>

    <div class="suggestions-search">
      <input
        v-model="searchQuery"
        type="text"
        placeholder="Rechercher une annotation..."
        class="search-input"
        @keydown.escape="searchQuery = ''"
      >
    </div>

    <div class="suggestions-tabs">
      <button
        :class="{ active: activeTab === 'official' }"
        @click="activeTab = 'official'"
      >
        Banque officielle
        <span class="tab-count">{{ suggestions.official?.length || 0 }}</span>
      </button>
      <button
        :class="{ active: activeTab === 'personal' }"
        @click="activeTab = 'personal'"
      >
        Mes annotations
        <span class="tab-count">{{ suggestions.personal?.length || 0 }}</span>
      </button>
    </div>

    <div
      v-if="isLoading"
      class="suggestions-loading"
    >
      Chargement...
    </div>

    <div
      v-else
      class="suggestions-list"
    >
      <!-- Banque officielle -->
      <template v-if="activeTab === 'official'">
        <div
          v-if="!suggestions.official?.length"
          class="suggestions-empty"
        >
          Aucune suggestion officielle pour ce contexte.
        </div>
        <div
          v-for="tpl in suggestions.official"
          :key="tpl.id"
          class="suggestion-card"
          :style="{
            borderLeftColor: getColor(tpl.criterion_type).border,
            backgroundColor: getColor(tpl.criterion_type).bg,
          }"
          @click="handleInsert(tpl.text, 'template', tpl.id)"
        >
          <div class="suggestion-meta">
            <span class="criterion-icon">{{ getColor(tpl.criterion_type).icon }}</span>
            <span class="criterion-label">{{ tpl.criterion_type_display }}</span>
            <span
              v-if="tpl.severity !== 'info'"
              class="severity-badge"
              :class="'severity-' + tpl.severity"
            >{{ severityLabels[tpl.severity] }}</span>
            <span class="question-ref">Ex{{ tpl.exercise_number }} Q{{ tpl.question_number }}</span>
          </div>
          <div class="suggestion-text">
            {{ tpl.text }}
          </div>
        </div>
      </template>

      <!-- Annotations personnelles -->
      <template v-if="activeTab === 'personal'">
        <div
          v-if="!suggestions.personal?.length"
          class="suggestions-empty"
        >
          Aucune annotation personnelle enregistrée.
        </div>
        <div
          v-for="ann in suggestions.personal"
          :key="ann.id"
          class="suggestion-card personal"
          @click="handleInsert(ann.text, 'personal', ann.id)"
        >
          <div class="suggestion-meta">
            <span class="criterion-icon">⭐</span>
            <span class="usage-count">×{{ ann.usage_count }}</span>
          </div>
          <div class="suggestion-text">
            {{ ann.text }}
          </div>
        </div>
      </template>
    </div>

    <div class="suggestions-hint">
      Cliquez pour insérer · Ctrl+K pour rechercher
    </div>
  </div>
</template>

<style scoped>
.suggestions-panel {
    display: flex;
    flex-direction: column;
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    max-height: 420px;
    overflow: hidden;
    font-size: 13px;
}

.suggestions-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 12px;
    border-bottom: 1px solid #e2e8f0;
    background: #f8fafc;
}

.suggestions-title {
    display: flex;
    align-items: center;
    gap: 6px;
    font-weight: 600;
    font-size: 13px;
}

.suggestions-icon {
    font-size: 15px;
}

.context-badge {
    font-size: 11px;
    background: #e0e7ff;
    color: #3730a3;
    padding: 1px 6px;
    border-radius: 4px;
    font-weight: 500;
}

.btn-close-panel {
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    color: #94a3b8;
    padding: 0 4px;
    line-height: 1;
}
.btn-close-panel:hover { color: #475569; }

.suggestions-search {
    padding: 6px 10px;
    border-bottom: 1px solid #f1f5f9;
}

.search-input {
    width: 100%;
    padding: 6px 10px;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    font-size: 12px;
    outline: none;
    transition: border-color 0.15s;
}
.search-input:focus {
    border-color: #3b82f6;
    box-shadow: 0 0 0 2px rgba(59,130,246,0.1);
}

.suggestions-tabs {
    display: flex;
    border-bottom: 1px solid #e2e8f0;
}
.suggestions-tabs button {
    flex: 1;
    padding: 6px 8px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 12px;
    cursor: pointer;
    color: #64748b;
    transition: all 0.15s;
}
.suggestions-tabs button.active {
    color: #1e40af;
    border-bottom-color: #3b82f6;
    font-weight: 600;
}
.suggestions-tabs button:hover:not(.active) {
    background: #f8fafc;
}

.tab-count {
    font-size: 10px;
    background: #e2e8f0;
    color: #475569;
    padding: 0 5px;
    border-radius: 8px;
    margin-left: 4px;
}

.suggestions-loading {
    padding: 20px;
    text-align: center;
    color: #94a3b8;
    font-size: 12px;
}

.suggestions-list {
    overflow-y: auto;
    flex: 1;
    padding: 6px;
    max-height: 280px;
}

.suggestions-empty {
    padding: 16px;
    text-align: center;
    color: #94a3b8;
    font-size: 12px;
}

.suggestion-card {
    padding: 8px 10px;
    margin-bottom: 4px;
    border-radius: 6px;
    border-left: 3px solid #3b82f6;
    cursor: pointer;
    transition: all 0.12s;
    background: #f8fafc;
}
.suggestion-card:hover {
    transform: translateX(2px);
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}
.suggestion-card.personal {
    border-left-color: #f59e0b;
    background: #fffbeb;
}
.suggestion-card.personal:hover {
    background: #fef3c7;
}

.suggestion-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 3px;
    font-size: 11px;
}

.criterion-icon {
    font-size: 12px;
}

.criterion-label {
    font-weight: 600;
    color: #475569;
    text-transform: capitalize;
}

.severity-badge {
    font-size: 10px;
    padding: 0 5px;
    border-radius: 4px;
    font-weight: 500;
}
.severity-mineur { background: #fef9c3; color: #854d0e; }
.severity-majeur { background: #fed7aa; color: #9a3412; }
.severity-critique { background: #fecaca; color: #991b1b; }

.question-ref {
    font-size: 10px;
    color: #94a3b8;
    margin-left: auto;
}

.usage-count {
    font-size: 10px;
    color: #92400e;
    font-weight: 600;
}

.suggestion-text {
    font-size: 12px;
    color: #334155;
    line-height: 1.4;
}

.suggestions-hint {
    padding: 4px 10px;
    text-align: center;
    font-size: 10px;
    color: #94a3b8;
    border-top: 1px solid #f1f5f9;
    background: #fafafa;
}
</style>
