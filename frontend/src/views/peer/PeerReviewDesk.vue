<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '../../icons/AppIcon.vue'
import CanvasLayer from '../../components/CanvasLayer.vue'
import peerReviewApi from '../../services/peerReviewApi'

const route = useRoute()
const router = useRouter()

const peerReview = ref(null)
const loading = ref(true)
const error = ref('')
const saving = ref(false)
const saveSuccess = ref(false)
const saveMessage = ref('')
const annotations = ref([])
const scores = ref({})
const remarks = ref({})
const globalAppreciation = ref('')
const finalComment = ref('')
const selectedTool = ref(null)
const annotationDraft = ref(null)
const annotationContent = ref('')
const pageDimensions = ref({})
const loadedPages = ref(new Set())

// Anonymization: mask header pages (1, 1+ppb, 1+2*ppb, …)
const isHeaderPage = (pageIndex) => {
  const ppb = peerReview.value?.pages_per_booklet || 4
  const page = pageIndex + 1
  return ((page - 1) % ppb) === 0
}

// Mobile tab navigation
const activeTab = ref('copy')
const isMobile = ref(false)
const showFinalizeModal = ref(false)

// Check mobile viewport
const checkMobile = () => {
  isMobile.value = window.innerWidth <= 900
}

// Watch for save success feedback
let saveSuccessTimer = null
watch(saveSuccess, (val) => {
  if (saveSuccessTimer) { clearTimeout(saveSuccessTimer); saveSuccessTimer = null }
  if (val) {
    saveSuccessTimer = setTimeout(() => { saveSuccess.value = false }, 2000)
  }
})

watch(saving, (val) => {
  saveMessage.value = val ? 'Sauvegarde en cours...' : ''
})

const leaves = computed(() => {
  const result = []
  const walk = (nodes, prefix = '') => {
    if (!Array.isArray(nodes)) return
    nodes.forEach((node, idx) => {
      const id = node.id || (prefix ? `${prefix}.${idx + 1}` : `${idx + 1}`)
      const children = node.children || node.sub_questions || []
      if (children.length) {
        walk(children, id)
      } else {
        result.push({
          id,
          label: node.label || node.title || id,
          points: Number(node.points || node.maxScore || node.max_score || 0),
        })
      }
    })
  }
  walk(peerReview.value?.grading_structure || [])
  return result
})

const totalScore = computed(() =>
  Object.values(scores.value || {}).reduce((sum, value) => {
    const n = Number(value)
    return Number.isFinite(n) ? sum + n : sum
  }, 0)
)

const statusLabel = computed(() => {
  const status = peerReview.value?.status
  if (status === 'FINALIZED') return 'Finalisée'
  if (status === 'IN_PROGRESS') return 'En cours'
  return 'Non commencée'
})

const isTeacherMode = computed(() => route.meta.mode === 'teacher')

const canEdit = computed(() =>
  !isTeacherMode.value && peerReview.value?.status !== 'FINALIZED'
)

function applyPayload(data) {
  peerReview.value = data
  annotations.value = Array.isArray(data.annotations) ? data.annotations : []
  scores.value = { ...(data.scores_data || {}) }
  remarks.value = {}
  ;(data.remarks || []).forEach((remark) => {
    remarks.value[remark.question_id] = remark.remark || ''
  })
  globalAppreciation.value = data.global_appreciation || ''
  finalComment.value = data.final_comment || ''
}

async function loadPeerReview() {
  loading.value = true
  error.value = ''
  try {
    const id = route.params.peerReviewId
    const data = isTeacherMode.value
      ? await peerReviewApi.getTeacherPeerReview(id)
      : await peerReviewApi.getStudentPeerReview(id)
    applyPayload(data)
  } catch (err) {
    error.value = err.response?.data?.detail || 'Impossible de charger la correction participative.'
  } finally {
    loading.value = false
  }
}

function annotationPayload() {
  return annotations.value.map((annotation) => ({
    page_index: annotation.page_index,
    x: annotation.x,
    y: annotation.y,
    w: annotation.w,
    h: annotation.h,
    content: annotation.content || '',
    type: annotation.type || 'COMMENTAIRE',
    color: annotation.color || '',
    metadata: annotation.metadata || {},
  }))
}

async function savePeerReview() {
  if (!canEdit.value) return
  saving.value = true
  error.value = ''
  try {
    const data = await peerReviewApi.saveStudentPeerReview(peerReview.value.id, {
      scores_data: scores.value,
      global_appreciation: globalAppreciation.value,
      final_comment: finalComment.value,
      remarks: Object.entries(remarks.value).map(([question_id, remark]) => ({ question_id, remark })),
      annotations: annotationPayload(),
    })
    applyPayload(data)
    saveSuccess.value = true
    saveMessage.value = 'Enregistré'
  } catch (err) {
    error.value = err.response?.data?.detail || 'Sauvegarde impossible.'
    saveMessage.value = 'Erreur de sauvegarde'
  } finally {
    saving.value = false
  }
}

const hasAnyScore = computed(() => {
  const s = scores.value || {}
  return Object.values(s).some((v) => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v)))
})

async function finalizePeerReview() {
  if (!canEdit.value) return
  if (saving.value) return
  if (!hasAnyScore.value) {
    error.value = 'Impossible de finaliser : vous devez saisir au moins une note avant de finaliser.'
    return
  }
  if (isMobile.value) {
    showFinalizeModal.value = true
  } else {
    const ok = window.confirm('Finaliser cette correction participative ? Elle ne sera plus modifiable.')
    if (!ok) return
    await doFinalize()
  }
}

async function confirmFinalize() {
  showFinalizeModal.value = false
  await doFinalize()
}

async function doFinalize() {
  await savePeerReview()
  if (error.value) return
  try {
    const data = await peerReviewApi.finalizeStudentPeerReview(peerReview.value.id)
    applyPayload(data)
  } catch (err) {
    error.value = err.response?.data?.detail || 'Finalisation impossible.'
  }
}

function handlePageLoad(event, pageIndex) {
  const rect = event.target.getBoundingClientRect()
  pageDimensions.value = {
    ...pageDimensions.value,
    [pageIndex]: {
      width: rect.width || event.target.naturalWidth,
      height: rect.height || event.target.naturalHeight,
    },
  }
  loadedPages.value = new Set([...loadedPages.value, pageIndex])
}

function pageAnnotations(pageIndex) {
  return annotations.value.filter((annotation) => annotation.page_index === pageIndex)
}

function handleAnnotation(rect, type, pageIndex) {
  if (!canEdit.value) return
  const annotationType = type || selectedTool.value || 'COMMENTAIRE'
  if (annotationType === 'VRAI' || annotationType === 'FAUX') {
    annotations.value.push({
      id: `local-${Date.now()}`,
      page_index: pageIndex,
      ...rect,
      content: annotationType === 'VRAI' ? 'Vrai' : 'Faux',
      type: annotationType,
    })
    savePeerReview()
    return
  }
  annotationDraft.value = { page_index: pageIndex, ...rect, type: annotationType }
  annotationContent.value = ''
}

function confirmAnnotation() {
  if (!annotationDraft.value) return
  annotations.value.push({
    id: `local-${Date.now()}`,
    ...annotationDraft.value,
    content: annotationContent.value,
  })
  annotationDraft.value = null
  annotationContent.value = ''
  savePeerReview()
}

function deleteAnnotation(annotationId) {
  if (!canEdit.value) return
  annotations.value = annotations.value.filter((annotation) => annotation.id !== annotationId)
  savePeerReview()
}

function goBack() {
  router.push(isTeacherMode.value ? '/corrector-dashboard' : '/student/dashboard')
}

function switchTab(tab) {
  activeTab.value = tab
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  loadPeerReview()
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', checkMobile)
  if (saveSuccessTimer) { clearTimeout(saveSuccessTimer); saveSuccessTimer = null }
})
</script>

<template>
  <div class="peer-review-desk">
    <!-- Header compact -->
    <header class="peer-toolbar">
      <button class="icon-button text-button" @click="goBack">
        <AppIcon name="arrow-left" :size="16" /> <span class="btn-text-hide">Retour</span>
      </button>
      <div v-if="peerReview" class="peer-title">
        <strong>{{ peerReview.anonymous_id }}</strong>
        <span class="exam-name-hide">{{ peerReview.exam_name }}</span>
        <em :class="['status-badge', peerReview.status?.toLowerCase()]">{{ statusLabel }}</em>
      </div>
      <div class="toolbar-actions desktop-only">
        <span class="total">{{ totalScore.toFixed(2) }} / 20</span>
        <button v-if="canEdit" class="secondary-button" :disabled="saving" @click="savePeerReview">
          <AppIcon :name="saving ? 'refresh' : 'file-check'" :size="16" /> Enregistrer
        </button>
        <button v-if="canEdit" class="primary-button" @click="finalizePeerReview">
          <AppIcon name="check" :size="16" /> Finaliser
        </button>
      </div>
    </header>

    <div v-if="loading" class="state"><AppIcon name="refresh" :size="24" class="spin" /> Chargement...</div>
    <div v-else-if="error && !peerReview" class="state error">{{ error }}</div>

    <!-- Mobile Tab Navigation -->
    <nav v-if="peerReview && isMobile" class="mobile-tabs" role="tablist">
      <button
        :class="['tab-btn', { active: activeTab === 'copy' }]"
        @click="switchTab('copy')"
        role="tab"
        :aria-selected="activeTab === 'copy'"
      >
        <AppIcon name="document" :size="18" />
        <span>Copie</span>
      </button>
      <button
        :class="['tab-btn', { active: activeTab === 'grading' }]"
        @click="switchTab('grading')"
        role="tab"
        :aria-selected="activeTab === 'grading'"
      >
        <AppIcon name="check-circle-2" :size="18" />
        <span>Barème</span>
      </button>
      <button
        :class="['tab-btn', { active: activeTab === 'remarks' }]"
        @click="switchTab('remarks')"
        role="tab"
        :aria-selected="activeTab === 'remarks'"
      >
        <AppIcon name="message" :size="18" />
        <span>Remarques</span>
      </button>
      <button
        :class="['tab-btn', { active: activeTab === 'appreciation' }]"
        @click="switchTab('appreciation')"
        role="tab"
        :aria-selected="activeTab === 'appreciation'"
      >
        <AppIcon name="star" :size="18" />
        <span>Appréciation</span>
      </button>
    </nav>

    <div v-if="peerReview && isMobile" class="mobile-peer-banner">
      <AppIcon name="info" :size="16" />
      <span>Correction pédagogique, séparée de la correction officielle.</span>
    </div>

    <main v-if="peerReview" :class="['peer-layout', { 'mobile-view': isMobile }]">
      <!-- TAB: Copy (visible on desktop or mobile when copy tab active) -->
      <section v-show="!isMobile || activeTab === 'copy'" class="copy-pane">
        <div v-if="!isMobile" class="peer-banner">
          <AppIcon name="info" :size="16" class="banner-icon" />
          <div class="banner-text">
            <strong>Correction participative</strong>
            <span>Cette correction est réalisée par un élève à des fins pédagogiques.</span>
          </div>
        </div>

        <div v-if="canEdit && !isMobile" class="tool-strip">
          <button :class="{ active: selectedTool === 'COMMENTAIRE' }" title="Commentaire" aria-label="Outil commentaire" :aria-pressed="selectedTool === 'COMMENTAIRE'" @click="selectedTool = 'COMMENTAIRE'">
            <AppIcon name="message" :size="16" />
          </button>
          <button :class="{ active: selectedTool === 'SURLIGNAGE' }" title="Surligner" aria-label="Outil surlignage" :aria-pressed="selectedTool === 'SURLIGNAGE'" @click="selectedTool = 'SURLIGNAGE'">
            <AppIcon name="highlight" :size="16" />
          </button>
          <button :class="{ active: selectedTool === 'ERREUR' }" title="Erreur" aria-label="Outil erreur" :aria-pressed="selectedTool === 'ERREUR'" @click="selectedTool = 'ERREUR'">
            <AppIcon name="alert" :size="16" />
          </button>
          <button :class="{ active: selectedTool === 'VRAI' }" title="Vrai" aria-label="Marquer vrai" :aria-pressed="selectedTool === 'VRAI'" @click="selectedTool = 'VRAI'">V</button>
          <button :class="{ active: selectedTool === 'FAUX' }" title="Faux" aria-label="Marquer faux" :aria-pressed="selectedTool === 'FAUX'" @click="selectedTool = 'FAUX'">F</button>
        </div>

        <div v-if="error" class="inline-error">{{ error }}</div>

        <div v-if="peerReview.source_media?.pages?.length" class="pages" :class="{ 'mobile-pages': isMobile }">
          <div v-for="(pageUrl, idx) in peerReview.source_media.pages" :key="pageUrl || idx" class="page-frame">
            <!-- Anonymization overlay — shown immediately to prevent identity flash -->
            <div v-if="isHeaderPage(idx)" class="anonymization-overlay">
              <div class="anonymization-label">
                <AppIcon name="lock" :size="14" class="inline" /> Zone d'identification masquée
              </div>
            </div>
            <img
              :src="pageUrl"
              :alt="`Page ${idx + 1}`"
              :class="{ 'page-img-header-loading': !loadedPages.has(idx) && isHeaderPage(idx) }"
              :loading="idx === 0 ? 'eager' : 'lazy'"
              :fetchpriority="idx === 0 ? 'high' : 'auto'"
              @load="(event) => handlePageLoad(event, idx)"
            >
            <CanvasLayer
              v-if="pageDimensions[idx] && !isMobile"
              :width="pageDimensions[idx].width"
              :height="pageDimensions[idx].height"
              :initial-annotations="pageAnnotations(idx)"
              :enabled="canEdit"
              @annotation-created="(rect) => handleAnnotation(rect, null, idx)"
              @annotation-clicked="deleteAnnotation"
            />
          </div>
        </div>
        <iframe
          v-else-if="peerReview.source_media?.pdf_source_url"
          class="pdf-frame"
          :class="{ 'mobile-pdf': isMobile }"
          :src="peerReview.source_media.pdf_source_url"
          title="Copie anonymisée"
        />
        <div v-else class="state">Aucun support de copie disponible.</div>
      </section>

      <!-- TAB: Grading (visible on desktop or mobile when grading/remarks/appreciation tab active) -->
      <aside v-show="!isMobile || ['grading', 'remarks', 'appreciation'].includes(activeTab)" class="grading-pane">
        <h2 v-if="!isMobile">Barème</h2>

        <!-- Mobile Score Total Header -->
        <div v-if="isMobile" class="mobile-score-header">
          <div class="score-total">
            <span class="score-value">{{ totalScore.toFixed(2) }}</span>
            <span class="score-max">/ 20</span>
          </div>
          <div v-if="saveSuccess" class="save-feedback">✓ Enregistré</div>
        </div>

        <!-- Grading Cards (Mobile) or Table (Desktop) -->
        <div v-if="!isMobile" class="score-list">
          <label v-for="question in leaves" :key="question.id" class="score-row">
            <span>{{ question.label }}</span>
            <input
              v-model.number="scores[question.id]"
              type="number"
              inputmode="decimal"
              min="0"
              :max="question.points"
              step="0.25"
              :disabled="!canEdit"
              @blur="savePeerReview"
            >
            <em>/ {{ question.points }}</em>
            <textarea
              v-model="remarks[question.id]"
              :disabled="!canEdit"
              rows="2"
              placeholder="Remarque"
              @blur="savePeerReview"
            />
          </label>
        </div>

        <!-- Mobile Grading Cards (Tab: Grading) -->
        <div v-if="isMobile && activeTab === 'grading'" class="mobile-grading-cards">
          <div v-for="question in leaves" :key="question.id" class="grading-card">
            <div class="card-header">
              <span class="question-label">{{ question.label }}</span>
              <span class="question-max">/ {{ question.points }} pts</span>
            </div>
            <div class="card-input">
              <label :for="`score-${question.id}`">Points attribués</label>
              <input
                :id="`score-${question.id}`"
                v-model.number="scores[question.id]"
                type="number"
                inputmode="decimal"
                min="0"
                :max="question.points"
                step="0.25"
                :disabled="!canEdit"
                class="score-input"
                @blur="savePeerReview"
              >
            </div>
            <label class="card-remark">
              <span>Remarque courte</span>
              <textarea
                v-model="remarks[question.id]"
                :disabled="!canEdit"
                rows="2"
                placeholder="Remarque sur cette question"
                @blur="savePeerReview"
              />
            </label>
          </div>
        </div>

        <!-- Mobile Remarks (Tab: Remarks) -->
        <div v-if="isMobile && activeTab === 'remarks'" class="mobile-remarks-list">
          <div v-for="question in leaves" :key="question.id" class="remark-card">
            <div class="remark-header">{{ question.label }}</div>
            <textarea
              v-model="remarks[question.id]"
              :disabled="!canEdit"
              rows="3"
              placeholder="Votre remarque..."
              class="remark-textarea"
              @blur="savePeerReview"
            />
          </div>
        </div>

        <!-- Mobile/Global Appreciation (Tab: Appreciation) -->
        <div v-if="isMobile && activeTab === 'appreciation'" class="mobile-appreciation">
          <label class="appreciation-block">
            <span>Appréciation globale</span>
            <textarea
              v-model="globalAppreciation"
              :disabled="!canEdit"
              rows="6"
              placeholder="Votre appréciation générale sur la copie..."
              class="appreciation-textarea"
              @blur="savePeerReview"
            />
          </label>
          <label class="appreciation-block">
            <span>Commentaire final</span>
            <textarea
              v-model="finalComment"
              :disabled="!canEdit"
              rows="4"
              placeholder="Commentaire complémentaire..."
              class="appreciation-textarea"
              @blur="savePeerReview"
            />
          </label>
        </div>

        <!-- Desktop Global Appreciation -->
        <template v-if="!isMobile">
          <label class="text-area-block">
            <span>Appréciation globale</span>
            <textarea v-model="globalAppreciation" :disabled="!canEdit" rows="5" @blur="savePeerReview" />
          </label>
          <label class="text-area-block">
            <span>Commentaire final</span>
            <textarea v-model="finalComment" :disabled="!canEdit" rows="3" @blur="savePeerReview" />
          </label>
        </template>
      </aside>
    </main>

    <!-- Mobile Sticky Action Bar -->
    <div v-if="peerReview && isMobile && canEdit" class="mobile-action-bar">
      <div v-if="saveMessage || error" :class="['mobile-save-state', { error: !!error }]">
        {{ error || saveMessage }}
      </div>
      <div class="action-bar-content">
        <div class="score-display">
          <span class="score-label">Total</span>
          <span class="score-value">{{ totalScore.toFixed(2) }}/20</span>
        </div>
        <div class="action-buttons">
          <button
            class="btn-save"
            :disabled="saving"
            @click="savePeerReview"
          >
            <AppIcon :name="saving ? 'refresh' : 'file-check'" :size="18" />
            <span>{{ saving ? 'Sauvegarde' : 'Enregistrer' }}</span>
          </button>
          <button
            class="btn-finalize"
            :disabled="saving"
            @click="finalizePeerReview"
          >
            <AppIcon name="check" :size="18" />
            <span>Finaliser</span>
          </button>
        </div>
      </div>
      <div class="safe-area-spacer" />
    </div>

    <!-- Finalize Confirmation Modal -->
    <div v-if="showFinalizeModal" class="modal-overlay" @click.self="showFinalizeModal = false">
      <div class="modal-box">
        <h3>Finaliser la correction ?</h3>
        <p>Après finalisation, vous ne pourrez plus modifier cette correction participative.</p>
        <div class="modal-actions">
          <button class="btn-secondary" @click="showFinalizeModal = false">Annuler</button>
          <button class="btn-primary" @click="confirmFinalize">Confirmer</button>
        </div>
      </div>
    </div>

    <!-- Annotation Modal -->
    <div v-if="annotationDraft" class="annotation-modal">
      <div class="annotation-box">
        <h3>Nouvelle annotation</h3>
        <textarea v-model="annotationContent" rows="4" autofocus />
        <div class="modal-actions">
          <button class="secondary-button" @click="annotationDraft = null">Annuler</button>
          <button class="primary-button" @click="confirmAnnotation">Ajouter</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* ═══════════════════════════════════════════════════════════
   BASE STYLES
   ═══════════════════════════════════════════════════════════ */
.peer-review-desk {
  min-height: 100vh;
  min-height: 100dvh;
  background: #f1f5f9;
  color: #1e293b;
  padding-bottom: env(safe-area-inset-bottom, 0);
  overflow-x: hidden;
}

.peer-review-desk,
.peer-review-desk * {
  box-sizing: border-box;
}

/* ═══════════════════════════════════════════════════════════
   TOOLBAR
   ═══════════════════════════════════════════════════════════ */
.peer-toolbar {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 0 16px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  position: sticky;
  top: 0;
  z-index: 100;
  padding-top: env(safe-area-inset-top, 0);
}

.peer-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.peer-title strong {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.peer-title .exam-name-hide {
  color: #64748b;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-badge {
  font-style: normal;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 999px;
  font-weight: 600;
  text-transform: uppercase;
}

.status-badge.not_started {
  background: #f1f5f9;
  color: #64748b;
}

.status-badge.in_progress {
  background: #fef3c7;
  color: #92400e;
}

.status-badge.finalized {
  background: #dcfce7;
  color: #166534;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.total {
  font-weight: 800;
  color: #0f172a;
  font-size: 15px;
}

.icon-button, .secondary-button, .primary-button, .tool-strip button {
  border: 1px solid #cbd5e1;
  background: #fff;
  border-radius: 8px;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 14px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.15s ease;
}

.icon-button:hover, .secondary-button:hover {
  background: #f8fafc;
  border-color: #94a3b8;
}

.primary-button {
  border-color: #2563eb;
  background: #2563eb;
  color: #fff;
}

.primary-button:hover:not(:disabled) {
  background: #1d4ed8;
  border-color: #1d4ed8;
}

.secondary-button:disabled {
  opacity: .6;
  cursor: not-allowed;
}

.text-button {
  color: #334155;
}

/* ═══════════════════════════════════════════════════════════
   MOBILE TABS NAVIGATION
   ═══════════════════════════════════════════════════════════ */
.mobile-tabs {
  display: flex;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  padding: 4px 8px;
  gap: 4px;
  overflow-x: auto;
  scrollbar-width: none;
  -webkit-overflow-scrolling: touch;
  position: sticky;
  top: calc(56px + env(safe-area-inset-top, 0px));
  z-index: 90;
}

.mobile-tabs::-webkit-scrollbar {
  display: none;
}

.tab-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px 4px;
  border: none;
  background: transparent;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s ease;
  min-width: 64px;
  min-height: 48px;
  -webkit-tap-highlight-color: transparent;
}

.tab-btn.active {
  background: #eff6ff;
  color: #2563eb;
}

.tab-btn:active {
  transform: scale(0.98);
}

/* ═══════════════════════════════════════════════════════════
   LAYOUT
   ═══════════════════════════════════════════════════════════ */
.peer-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 16px;
  padding: 16px;
  align-items: start;
}

.peer-layout.mobile-view {
  display: block;
  padding: 12px;
  padding-bottom: calc(132px + env(safe-area-inset-bottom, 0px));
}

.copy-pane, .grading-pane {
  min-width: 0;
}

/* ═══════════════════════════════════════════════════════════
   BANNER
   ═══════════════════════════════════════════════════════════ */
.peer-banner {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 10px;
  color: #9a3412;
  margin-bottom: 12px;
}

.mobile-peer-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 12px 0;
  padding: 10px 12px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
  border-radius: 10px;
  color: #9a3412;
  font-size: 13px;
  line-height: 1.35;
}

.banner-icon {
  flex-shrink: 0;
  margin-top: 2px;
}

.banner-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.banner-text strong {
  font-size: 13px;
  font-weight: 600;
}

.banner-text span {
  font-size: 12px;
  line-height: 1.4;
}

/* ═══════════════════════════════════════════════════════════
   TOOL STRIP
   ═══════════════════════════════════════════════════════════ */
.tool-strip {
  display: flex;
  gap: 6px;
  padding: 8px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  margin-bottom: 12px;
}

.tool-strip button {
  width: 40px;
  height: 40px;
  padding: 0;
  font-weight: 700;
}

.tool-strip button.active {
  border-color: #2563eb;
  background: #eff6ff;
  color: #2563eb;
}

/* ═══════════════════════════════════════════════════════════
   COPY / PAGES
   ═══════════════════════════════════════════════════════════ */
.pages {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;
  overflow-x: hidden;
}

.pages.mobile-pages {
  gap: 12px;
}

.page-frame {
  position: relative;
  background: #fff;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  overflow: hidden;
  max-width: 100%;
  width: 100%;
}

.page-frame img {
  display: block;
  max-width: 100%;
  height: auto;
  width: 100%;
  touch-action: pan-x pan-y pinch-zoom;
  transition: opacity 0.3s ease-in;
}

/* Hide header-page images completely until loaded (mask is already visible) */
.page-img-header-loading {
  opacity: 0;
}

/* Anonymization overlay — matches CorrectorDesk dimensions (23% = 67mm on A4) */
.anonymization-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 23%;
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
  z-index: 20;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 12px;
  border-bottom: 3px solid #7F77DD;
}

.anonymization-label {
  color: white;
  font-size: 1.1rem;
  font-weight: 600;
  letter-spacing: 0.5px;
  text-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.page-frame :deep(canvas) {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.pdf-frame {
  width: 100%;
  height: calc(100vh - 180px);
  border: 0;
  background: #fff;
  border-radius: 10px;
}

.pdf-frame.mobile-pdf {
  height: calc(100vh - 220px);
  min-height: 400px;
}

/* ═══════════════════════════════════════════════════════════
   GRADING PANE
   ═══════════════════════════════════════════════════════════ */
.grading-pane {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px;
  position: sticky;
  top: 72px;
  max-height: calc(100vh - 90px);
  overflow: auto;
}

.mobile-view .grading-pane {
  padding: 12px;
  border-radius: 10px;
}

.grading-pane h2 {
  margin: 0 0 16px;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

/* ═══════════════════════════════════════════════════════════
   MOBILE SCORE HEADER
   ═══════════════════════════════════════════════════════════ */
.mobile-score-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e2e8f0;
}

.score-total {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.score-value {
  font-size: 28px;
  font-weight: 800;
  color: #0f172a;
}

.score-max {
  font-size: 16px;
  font-weight: 500;
  color: #64748b;
}

.save-feedback {
  font-size: 13px;
  color: #16a34a;
  font-weight: 600;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ═══════════════════════════════════════════════════════════
   DESKTOP SCORE LIST
   ═══════════════════════════════════════════════════════════ */
.score-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.score-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 80px 50px;
  gap: 10px;
  align-items: center;
  padding-bottom: 12px;
  border-bottom: 1px solid #f1f5f9;
}

.score-row span {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}

.score-row input {
  height: 40px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 0 10px;
  font-size: 15px;
  text-align: center;
}

.score-row input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.score-row em {
  font-style: normal;
  color: #64748b;
  font-size: 13px;
}

.score-row textarea {
  grid-column: 1 / -1;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
  resize: vertical;
  min-height: 60px;
  font-size: 14px;
}

.text-area-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}

.text-area-block textarea {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 12px;
  resize: vertical;
  font-size: 14px;
  min-height: 100px;
}

/* ═══════════════════════════════════════════════════════════
   MOBILE GRADING CARDS
   ═══════════════════════════════════════════════════════════ */
.mobile-grading-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.grading-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.question-label {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  min-width: 0;
  line-height: 1.35;
}

.question-max {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
  white-space: nowrap;
}

.card-input {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.card-input label {
  font-size: 13px;
  color: #64748b;
  font-weight: 500;
}

.score-input {
  height: 48px;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  padding: 0 14px;
  font-size: 18px;
  font-weight: 600;
  text-align: center;
  color: #0f172a;
  background: #fff;
  width: 100%;
  transition: border-color 0.15s ease;
}

.card-remark {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 12px;
}

.card-remark span {
  font-size: 13px;
  color: #475569;
  font-weight: 600;
}

.card-remark textarea {
  width: 100%;
  min-height: 76px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
  font-size: 16px;
  line-height: 1.45;
  resize: vertical;
  background: #fff;
}

.card-remark textarea:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12);
}

.score-input:focus {
  outline: none;
  border-color: #2563eb;
}

.score-input:disabled {
  background: #f1f5f9;
  color: #94a3b8;
}

/* ═══════════════════════════════════════════════════════════
   MOBILE REMARKS
   ═══════════════════════════════════════════════════════════ */
.mobile-remarks-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.remark-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
}

.remark-header {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
  margin-bottom: 10px;
}

.remark-textarea {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
  font-size: 16px;
  resize: vertical;
  min-height: 80px;
}

.remark-textarea:focus {
  outline: none;
  border-color: #2563eb;
}

/* ═══════════════════════════════════════════════════════════
   MOBILE APPRECIATION
   ═══════════════════════════════════════════════════════════ */
.mobile-appreciation {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.appreciation-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.appreciation-block span {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}

.appreciation-textarea {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
  font-size: 16px;
  resize: vertical;
  min-height: 120px;
}

.appreciation-textarea:focus {
  outline: none;
  border-color: #2563eb;
}

/* ═══════════════════════════════════════════════════════════
   MOBILE STICKY ACTION BAR
   ═══════════════════════════════════════════════════════════ */
.mobile-action-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: #fff;
  border-top: 1px solid #e2e8f0;
  z-index: 1000;
  box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.08);
}

.mobile-save-state {
  padding: 8px 16px 0;
  color: #166534;
  font-size: 13px;
  font-weight: 700;
}

.mobile-save-state.error {
  color: #b91c1c;
}

.action-bar-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  gap: 16px;
}

.safe-area-spacer {
  height: env(safe-area-inset-bottom, 0);
  background: #fff;
}

.action-bar-content .score-display {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.score-label {
  font-size: 11px;
  color: #64748b;
  font-weight: 500;
  text-transform: uppercase;
}

.action-bar-content .score-value {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.btn-save, .btn-finalize {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 16px;
  height: 44px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
  min-width: 118px;
  justify-content: center;
}

.btn-save {
  background: #f1f5f9;
  color: #334155;
}

.btn-save:active:not(:disabled) {
  background: #e2e8f0;
}

.btn-save:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-finalize {
  background: #2563eb;
  color: #fff;
}

.btn-finalize:active:not(:disabled) {
  background: #1d4ed8;
}

.btn-finalize:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* ═══════════════════════════════════════════════════════════
   STATES & FEEDBACK
   ═══════════════════════════════════════════════════════════ */
.state {
  min-height: 220px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  gap: 8px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.error, .inline-error {
  color: #dc2626;
}

.inline-error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  padding: 10px 12px;
  border-radius: 8px;
  margin-bottom: 12px;
  font-size: 13px;
}

/* ═══════════════════════════════════════════════════════════
   MODALS
   ═══════════════════════════════════════════════════════════ */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 2000;
}

.modal-box {
  width: 100%;
  max-width: 360px;
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}

.modal-box h3 {
  margin: 0 0 12px;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.modal-box p {
  margin: 0 0 20px;
  font-size: 14px;
  color: #64748b;
  line-height: 1.5;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}

.btn-secondary, .btn-primary {
  flex: 1;
  height: 44px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-secondary {
  background: #f1f5f9;
  color: #334155;
}

.btn-primary {
  background: #2563eb;
  color: #fff;
}

.annotation-modal {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, .5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 1500;
}

.annotation-box {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, .2);
}

.annotation-box h3 {
  margin: 0 0 12px;
  font-size: 16px;
  font-weight: 700;
}

.annotation-box textarea {
  width: 100%;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
  font-size: 16px;
  resize: vertical;
  min-height: 100px;
}

.annotation-box .modal-actions {
  margin-top: 16px;
  justify-content: flex-end;
}

/* ═══════════════════════════════════════════════════════════
   RESPONSIVE BREAKPOINTS
   ═══════════════════════════════════════════════════════════ */
@media (max-width: 900px) {
  .peer-layout {
    grid-template-columns: 1fr;
    padding: 12px;
  }

  .grading-pane {
    position: static;
    max-height: none;
  }

  .desktop-only {
    display: none !important;
  }

  .btn-text-hide {
    display: none;
  }
}

@media (max-width: 768px) {
  .peer-toolbar {
    height: auto;
    min-height: 56px;
  }

  .peer-title {
    flex-wrap: wrap;
    row-gap: 4px;
  }

  .peer-title strong {
    font-size: 16px;
  }
}

@media (max-width: 600px) {
  .peer-layout.mobile-view {
    padding: 10px;
    padding-bottom: calc(138px + env(safe-area-inset-bottom, 0px));
  }

  .mobile-tabs {
    padding: 4px 6px;
  }

  .tab-btn {
    min-width: 70px;
  }

  .grading-card,
  .remark-card {
    padding: 12px;
  }
}

@media (min-width: 901px) {
  .mobile-tabs,
  .mobile-action-bar {
    display: none !important;
  }
}

@media (max-width: 430px) {
  .peer-toolbar {
    padding: 8px 10px;
    gap: 8px;
  }

  .exam-name-hide {
    display: none;
  }

  .tab-btn span {
    font-size: 10px;
  }

  .action-bar-content {
    padding: 10px 12px;
    gap: 10px;
  }

  .action-bar-content .score-value {
    font-size: 18px;
  }

  .btn-save span,
  .btn-finalize span {
    font-size: 13px;
  }

  .btn-save, .btn-finalize {
    min-width: 104px;
    padding: 0 10px;
  }
}

@media (max-width: 375px) {
  .score-value {
    font-size: 24px;
  }

  .action-buttons {
    gap: 6px;
  }

  .btn-save, .btn-finalize {
    padding: 0 8px;
    height: 44px;
    min-width: 96px;
  }

  .btn-save span,
  .btn-finalize span {
    font-size: 12px;
  }

  .action-bar-content {
    padding: 10px 8px;
  }

  .mobile-peer-banner {
    margin-inline: 8px;
  }
}
</style>
