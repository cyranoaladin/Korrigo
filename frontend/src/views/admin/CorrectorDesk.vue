<script setup>
import { ref, onMounted, computed, watch, nextTick, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import gradingApi from '../../services/gradingApi'
import CanvasLayer from '../../components/CanvasLayer.vue'
// Removed date-fns, using native Intl
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const copyId = route.params.copyId

// --- State ---
const copy = ref(null)
const isLoading = ref(true)
const isSaving = ref(false)
const error = ref(null)
const annotations = ref([])
const historyLogs = ref([])

// Viewer
const scale = ref(1.0)
const currentPage = ref(1) 
const pdfDimensions = ref({ width: 0, height: 0 }) 
const imageError = ref(false)

// Lock State
// Lock State
const softLock = ref(null) // { token, owner, expires_at }
const lockInterval = ref(null)
const isLockConflict = ref(false) // If true, we are read-only due to other owner


// Autosave State
// Autosave State
const restoreAvailable = ref(null) // { source: 'LOCAL'|'SERVER', payload: ... }
const autosaveTimer = ref(null)
const localSaveTimer = ref(null)
const clientId = ref(crypto.randomUUID())
const lastSaveStatus = ref(null) // { source: 'LOCAL'|'SERVER', time: Date }

// UI State
const activeTab = ref('editor') // 'editor' | 'history' | 'grading'

// Editor
const showEditor = ref(false) // Overlay editor
const draftAnnotation = ref(null) // { normalizedRect, type, content }
const editorInputRef = ref(null)

// Grading / Remarks / Scores
const questionRemarks = ref(new Map()) // Map<question_id, remark_text>
const questionScores = ref(new Map()) // Map<question_id, score_value>
const globalAppreciation = ref('')
const remarksSaving = ref(new Map()) // Map<question_id, boolean> for save indicators
const scoresSaving = ref(false)
const appreciationSaving = ref(false)
const remarkTimers = ref(new Map()) // Map<question_id, timerId> for debouncing
const scoresTimer = ref(null)
const appreciationTimer = ref(null)
const lastScoresSaveStatus = ref(null) // { time: Date, success: boolean }

// --- Computed ---
const isStaging = computed(() => copy.value?.status === 'STAGING')
const isReady = computed(() => copy.value?.status === 'READY')
const isLocked = computed(() => copy.value?.status === 'LOCKED')
const isGraded = computed(() => copy.value?.status === 'GRADED')

// Anonymization: hide student identity on page 1
const isAdmin = computed(() => authStore.user?.is_superuser || authStore.user?.role === 'Admin')
const showIdentity = ref(false) // Only admin can toggle this
const isFirstPage = computed(() => currentPage.value === 1)

const isReadOnly = computed(() => isGraded.value || isLockConflict.value)
const canAnnotate = computed(() => isReady.value && !isReadOnly.value)

const pages = computed(() => {
    if (!copy.value || !copy.value.booklets) return []
    let allPages = []
    copy.value.booklets.forEach(booklet => {
        if (booklet.pages_images) {
            allPages = allPages.concat(booklet.pages_images)
        }
    })
    return allPages
})

const hasPages = computed(() => pages.value.length > 0)

const currentPageImageUrl = computed(() => {
    if (!hasPages.value) return null;
    if (currentPage.value < 1 || currentPage.value > pages.value.length) return null
    const path = pages.value[currentPage.value - 1]
    return gradingApi.getMediaUrl(path)
})

const currentAnnotations = computed(() => {
    return annotations.value.filter(a => a.page_index === (currentPage.value - 1))
})

const displayWidth = computed(() => pdfDimensions.value.width * scale.value)
const displayHeight = computed(() => pdfDimensions.value.height * scale.value)

const gradingStructure = computed(() => {
    if (!copy.value?.exam?.grading_structure) return []
    return copy.value.exam.grading_structure
})

const flattenQuestions = (structure, parentId = '') => {
    let questions = []
    structure.forEach((item, index) => {
        const itemId = parentId ? `${parentId}.${index + 1}` : `${index + 1}`
        if (item.type === 'question') {
            questions.push({
                id: itemId,
                title: item.title || `Question ${itemId}`,
                maxScore: item.maxScore || 0
            })
        }
        if (item.children && Array.isArray(item.children)) {
            questions = questions.concat(flattenQuestions(item.children, itemId))
        }
    })
    return questions
}

const flatQuestions = computed(() => {
    return flattenQuestions(gradingStructure.value)
})

// --- Global Key Handling ---
const onGlobalKeydown = (e) => {
    if (showEditor.value) {
        if (e.key === 'Escape') {
            e.preventDefault()
            cancelEditor()
        }
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault()
            saveAnnotation()
        }
    }
}

// --- Watchers ---
watch(pages, (newPages) => {
    if (newPages.length === 0) {
        currentPage.value = 1
        pdfDimensions.value = { width: 0, height: 0 }
    } else {
        if (currentPage.value > newPages.length) currentPage.value = newPages.length
        else if (currentPage.value < 1) currentPage.value = 1
    }
})

watch(canAnnotate, (newCanAnnotate) => {
    if (!newCanAnnotate && showEditor.value) cancelEditor()
})

// --- Actions ---

const fetchCopy = async () => {
  isLoading.value = true
  error.value = null
  imageError.value = false
  showIdentity.value = false
  try {
    copy.value = await gradingApi.getCopy(copyId)
    await refreshAnnotations()
    await fetchHistory()
    await fetchRemarks()
    await fetchScores()
    await fetchGlobalAppreciation()
  } catch (err) {
    if (err.response?.status === 403) {
        error.value = "Access Denied: You do not have permission to view this copy."
    } else {
        error.value = err.response?.data?.detail || "Failed to load copy"
    }
  } finally {
    isLoading.value = false
  }
}

const refreshAnnotations = async () => {
    try {
        annotations.value = await gradingApi.listAnnotations(copyId)
    } catch (err) { console.error(err) }
}

const fetchHistory = async () => {
    try {
        historyLogs.value = await gradingApi.listAuditLogs(copyId)
    } catch (err) { console.error("Failed to load history", err) }
}

const fetchRemarks = async () => {
    try {
        const remarks = await gradingApi.fetchRemarks(copyId)
        const remarksMap = new Map()
        remarks.forEach(r => {
            remarksMap.set(r.question_id, r.remark)
        })
        questionRemarks.value = remarksMap
    } catch (err) { console.error("Failed to load remarks", err) }
}

const fetchScores = async () => {
    try {
        const response = await gradingApi.fetchScores(copyId)
        const scoresMap = new Map()
        if (response.scores_data) {
            Object.entries(response.scores_data).forEach(([qid, val]) => {
                scoresMap.set(qid, val)
            })
        }
        questionScores.value = scoresMap
    } catch (err) { console.error("Failed to load scores", err) }
}

const fetchGlobalAppreciation = async () => {
    try {
        const response = await gradingApi.fetchGlobalAppreciation(copyId)
        globalAppreciation.value = response.global_appreciation || ''
    } catch (err) { console.error("Failed to load global appreciation", err) }
}

const saveRemark = async (questionId, remark) => {
    remarksSaving.value.set(questionId, true)
    try {
        await gradingApi.saveRemark(copyId, questionId, remark, softLock.value?.token)
    } catch (err) {
        console.error("Failed to save remark", err)
        error.value = "Failed to save remark"
    } finally {
        remarksSaving.value.set(questionId, false)
    }
}

const saveGlobalAppreciationToServer = async () => {
    appreciationSaving.value = true
    try {
        await gradingApi.saveGlobalAppreciation(copyId, globalAppreciation.value, softLock.value?.token)
    } catch (err) {
        console.error("Failed to save global appreciation", err)
        error.value = "Failed to save global appreciation"
    } finally {
        appreciationSaving.value = false
    }
}

const onRemarkChange = (questionId, value) => {
    questionRemarks.value.set(questionId, value)
    
    if (remarkTimers.value.has(questionId)) {
        clearTimeout(remarkTimers.value.get(questionId))
    }
    
    const timerId = setTimeout(() => {
        saveRemark(questionId, value)
    }, 1000)
    
    remarkTimers.value.set(questionId, timerId)
}

const onAppreciationChange = (value) => {
    globalAppreciation.value = value

    if (appreciationTimer.value) {
        clearTimeout(appreciationTimer.value)
    }

    appreciationTimer.value = setTimeout(() => {
        saveGlobalAppreciationToServer()
    }, 1000)
}

const saveScoresToServer = async () => {
    scoresSaving.value = true
    try {
        const scoresObj = {}
        questionScores.value.forEach((val, key) => {
            scoresObj[key] = val
        })
        await gradingApi.saveScores(copyId, scoresObj)
        lastScoresSaveStatus.value = { time: new Date(), success: true }
    } catch (err) {
        console.error("Failed to save scores", err)
        lastScoresSaveStatus.value = { time: new Date(), success: false }
    } finally {
        scoresSaving.value = false
    }
}

const onScoreChange = (questionId, value) => {
    questionScores.value.set(questionId, value === '' ? null : parseFloat(value))
    // Also save to localStorage as fallback
    try {
        const scoresObj = {}
        questionScores.value.forEach((val, key) => { scoresObj[key] = val })
        localStorage.setItem(`korrigo_scores_${copyId}`, JSON.stringify(scoresObj))
    } catch(e) { /* localStorage full, ignore */ }

    if (scoresTimer.value) {
        clearTimeout(scoresTimer.value)
    }
    scoresTimer.value = setTimeout(() => {
        saveScoresToServer()
    }, 800)
}

// Check if copy can be finalized (all scores filled + appreciation)
const canFinalize = computed(() => {
    if (flatQuestions.value.length === 0) return false
    // All questions must have a score
    for (const q of flatQuestions.value) {
        const score = questionScores.value.get(q.id)
        if (score === null || score === undefined || score === '') return false
    }
    // Appreciation must be filled
    if (!globalAppreciation.value || globalAppreciation.value.trim() === '') return false
    return true
})

const handleMarkReady = async () => {
    if (isSaving.value) return; isSaving.value = true;
    try { 
        await gradingApi.readyCopy(copyId); 
        await fetchCopy(); 
        // Try to acquire lock if now ready
        if (!softLock.value) await acquireLock();
    }
    catch (err) { error.value = err.response?.data?.detail || "Action failed"; } 
    finally { isSaving.value = false; }
}

// Soft Lock Management
const acquireLock = async () => {
    try {
        const response = await gradingApi.acquireLock(copyId);
        // Success
        softLock.value = response;
        isLockConflict.value = false;
        startHeartbeat();
        checkDrafts(); // Check for draft restoration
    } catch (err) {
        if (err.response?.status === 409) {
            // Conflict
            isLockConflict.value = true;
            softLock.value = null; // We don't have the token
            const owner = err.response.data.owner?.username || "Another user";
            error.value = `LOCKED by ${owner}. You are in Read-Only mode.`;
        } else {
            console.error("Lock acquire failed", err);
        }
    }
}

// --- Autosave Logic ---
// Stable Key using Auth Store
const getStorageKey = () => {
    // Safety: checkDrafts and Autosave are gated by authStore.user presence
    const userId = authStore.user?.id || 'anon';
    return `draft_${copyId}_${userId}`;
};

const checkDrafts = async () => {
    if (!authStore.user?.id) return; // Wait for hydration
    
    // 1. Get Server Draft
    let serverDraft = null;
    try {
        serverDraft = await gradingApi.getDraft(copyId);
    } catch (e) { console.error("Failed to fetch server draft", e); }

    // 2. Get Local Draft
    const localRaw = localStorage.getItem(getStorageKey());
    const localDraft = localRaw ? JSON.parse(localRaw) : null;

    // 3. Logic: Prefer Local if newer.
    const localTs = localDraft?.saved_at || 0;
    const serverTs = serverDraft?.updated_at ? new Date(serverDraft.updated_at).getTime() : 0;
    
    // Choose usage
    if (localDraft && localTs > serverTs) {
        restoreAvailable.value = { source: 'LOCAL', payload: localDraft };
    } else if (serverDraft?.payload) {
        restoreAvailable.value = { 
            source: 'SERVER', 
            payload: serverDraft.payload,
            client_id: serverDraft.client_id 
        };
    }
}

const restoreDraft = () => {
    if (!restoreAvailable.value) return;
    if (isReadOnly.value) return; // Banner handles this check, but safety here.
    
    // Adopt Session if Server
    if (restoreAvailable.value.source === 'SERVER' && restoreAvailable.value.client_id) {
        clientId.value = restoreAvailable.value.client_id;
    }

    // Check if we can restore (need to open editor?)
    const data = restoreAvailable.value.payload;
    if (data && data.rect) {
         // Restore Page
         if (typeof data.page_index === 'number') {
             currentPage.value = data.page_index + 1;
         }
         
         // It's a draft annotation
         handleDrawComplete(data.rect); // Opens editor
         draftAnnotation.value = { 
            rect: data.rect,
            type: data.type,
            content: data.content,
            score_delta: data.score_delta
         }; 
    }
    
    restoreAvailable.value = null;
}

const discardDraft = async () => {
    localStorage.removeItem(getStorageKey());
    // Also clear server to prevent 409 on next save (Start Fresh)
    if (softLock.value?.token) {
        try { await gradingApi.deleteDraft(copyId, softLock.value.token); } catch {}
    }
    restoreAvailable.value = null;
}

watch(draftAnnotation, (newVal) => {
    if (!newVal) return;
    if (isReadOnly.value) return;
    if (!authStore.user?.id) return; // Prevent saving to 'anon' key
    
    // Construct full payload with Context
    const savePayload = {
        ...newVal,
        page_index: currentPage.value - 1,
        saved_at: Date.now()
    };
    
    // 1. Local Save (Debounced)
    if (localSaveTimer.value) clearTimeout(localSaveTimer.value);
    localSaveTimer.value = setTimeout(() => {
        try {
            localStorage.setItem(getStorageKey(), JSON.stringify(savePayload));
            lastSaveStatus.value = { source: 'LOCAL', time: new Date() };
        } catch {}
    }, 300); // 300ms debounce for local storage optimization

    // 2. Server Save (Debounced)
    if (autosaveTimer.value) clearTimeout(autosaveTimer.value);
    autosaveTimer.value = setTimeout(async () => {
        if (!softLock.value?.token) return;
        try {
           await gradingApi.saveDraft(copyId, savePayload, softLock.value.token, clientId.value);
           lastSaveStatus.value = { source: 'SERVER', time: new Date() };
        } catch (e) { console.error("Autosave failed", e); }
    }, 2000); // 2s debounce

}, { deep: true });

const startHeartbeat = () => {
    if (lockInterval.value) clearInterval(lockInterval.value);
    let failCount = 0;
    
    lockInterval.value = setInterval(async () => {
        if (!softLock.value?.token) return;
        try {
            const res = await gradingApi.heartbeatLock(copyId, softLock.value.token);
            softLock.value.expires_at = res.expires_at;
            failCount = 0; // Reset on success
        } catch (err) {
             console.error("Heartbeat failed", err);
             const status = err.response?.status;
             
             if (status === 401) {
                 // Session Expired
                 window.location.href = '/login'; // Force login redirect
                 return; 
             }
             
             if (status === 409 || status === 404 || status === 403) {
                 // Lock stolen, expired, or forbidden
                 softLock.value = null;
                 isLockConflict.value = true;
                 error.value = "Lock lost (taken by another user or expired). Switching to Read-Only.";
                 clearInterval(lockInterval.value);
                 return;
             }
             
             // Network errors or 5xx: Tolerate small failures
             failCount++;
             if (failCount > 3) {
                 console.warn("Too many heartbeat failures. Assuming lock lost.");
                 softLock.value = null;
                 isLockConflict.value = true;
                 error.value = "Connection unstable. Lock maintenance failed. Read-Only.";
                 clearInterval(lockInterval.value);
             }
        }
    }, 30000); // 30s
}

const releaseLock = async () => {
    if (lockInterval.value) clearInterval(lockInterval.value);
    if (softLock.value?.token) {
        try {
            await gradingApi.releaseLock(copyId, softLock.value.token);
            softLock.value = null;
        } catch (e) { console.error("Release failed", e); }
    }
}

const handleFinalize = async () => {
    if (isSaving.value) return;
    // Validate all scores + appreciation before finalizing
    if (!canFinalize.value) {
        error.value = "Impossible de finaliser : toutes les notes doivent être remplies ET une appréciation générale est requise."
        return
    }
    if (!confirm('Êtes-vous sûr de vouloir finaliser cette copie ? Cette action est irréversible.')) return
    isSaving.value = true;
    try {
        // Save scores one last time before finalize
        await saveScoresToServer()
        await gradingApi.finalizeCopy(copyId, softLock.value?.token);
        await fetchCopy();
    }
    catch (err) { error.value = err.response?.data?.detail || "Action failed"; }
    finally { isSaving.value = false; }
}

const handleDownload = () => {
  const url = gradingApi.getFinalPdfUrl(copyId)
  window.open(url, '_blank')
}

const handleImageLoad = (e) => {
    imageError.value = false
    pdfDimensions.value = { width: e.target.naturalWidth, height: e.target.naturalHeight }
}

const handleImageError = () => {
    imageError.value = true
    error.value = "Failed to load page image."
}

// --- Annotation Editor ---
const handleDrawComplete = (normalizedRect) => {
    if (!canAnnotate.value) return;
    activeTab.value = 'editor' // Switch to editor tab/view implicitly
    draftAnnotation.value = {
        rect: normalizedRect,
        type: 'COMMENT',
        content: '',
        score_delta: 0
    }
    showEditor.value = true
    nextTick(() => { if (editorInputRef.value) editorInputRef.value.focus() })
}

const saveAnnotation = async () => {
    if (!draftAnnotation.value) return;
    isSaving.value = true;
    try {
        const payload = {
            page_index: currentPage.value - 1,
            x: draftAnnotation.value.rect.x,
            y: draftAnnotation.value.rect.y,
            w: draftAnnotation.value.rect.w,
            h: draftAnnotation.value.rect.h,
            type: draftAnnotation.value.type,
            content: draftAnnotation.value.content,
            score_delta: draftAnnotation.value.score_delta
        }
        await gradingApi.createAnnotation(copyId, payload, softLock.value?.token)
        
        // Clear Drafts on Success
        localStorage.removeItem(getStorageKey());
        try { await gradingApi.deleteDraft(copyId, softLock.value?.token); } catch{}
        restoreAvailable.value = null;

        await refreshAnnotations()
        await fetchHistory() // Update log
        cancelEditor()
    } catch (err) {
        error.value = err.response?.data?.detail || "Failed to create annotation"
    } finally { isSaving.value = false; }
}

const cancelEditor = () => {
    showEditor.value = false
    draftAnnotation.value = null
}

const handleDeleteAnnotation = async (id) => {
    if (!canAnnotate.value) return;
    if (!confirm("Delete this annotation?")) return;
    isSaving.value = true;
    try {
        await gradingApi.deleteAnnotation(copyId, id, softLock.value?.token)
        await refreshAnnotations()
        await fetchHistory()
    } catch (err) {
        error.value = err.response?.data?.detail || "Failed to delete annotation"
    } finally { isSaving.value = false; }
}

// Helper to format date
const formatDate = (isoString) => {
    if (!isoString) return ''
    return new Date(isoString).toLocaleString()
}

onMounted(async () => {
  await fetchCopy()
  // Try acquire lock if ready
  if (isReady.value) {
      await acquireLock();
  }
  window.addEventListener('keydown', onGlobalKeydown)
  
    // Robust Release
    window.addEventListener('beforeunload', releaseLock)
    window.addEventListener('pagehide', releaseLock)
})

// Watch for Auth Hydration to load drafts
watch(() => authStore.user, (u) => {
    if (u?.id) checkDrafts();
}, { immediate: true })

onUnmounted(() => {
    releaseLock();
    window.removeEventListener('keydown', onGlobalKeydown)
    window.removeEventListener('beforeunload', releaseLock)
    window.removeEventListener('pagehide', releaseLock)
})
</script>

<template>
  <div class="corrector-desk">
    <div class="toolbar">
      <div class="left">
        <button
          class="back-btn"
          @click="router.push('/corrector-dashboard')"
        >
          ← Back
        </button>
        <span
          v-if="copy"
          class="copy-info"
        >
          <strong>{{ copy.anonymous_id }}</strong> 
          <span :class="'status-badge status-' + copy.status.toLowerCase()">{{ copy.status }}</span>
        </span>
      </div>
      
      <div
        v-if="lastSaveStatus"
        class="center-status"
      >
        <span
          class="save-indicator"
          data-testid="save-indicator"
        >
          Sauvegardé ({{ lastSaveStatus.source === 'LOCAL' ? 'Local' : 'Serveur' }}) à {{ lastSaveStatus.time.toLocaleTimeString() }}
        </span>
      </div>

      <div class="actions">
        <button
          v-if="isStaging"
          :disabled="isSaving"
          class="btn-primary"
          @click="handleMarkReady"
        >
          Mark READY
        </button>

        <button
          v-if="(isReady && softLock) || isLocked"
          :disabled="isSaving || isReadOnly || !canFinalize"
          :class="['btn-success', { 'btn-disabled': !canFinalize }]"
          :title="!canFinalize ? 'Toutes les notes + appréciation requises' : 'Finaliser la correction'"
          @click="handleFinalize"
        >
          Finaliser
        </button>
        <button
          v-if="isGraded"
          class="btn-info"
          @click="handleDownload"
        >
          Download
        </button>
      </div>
    </div>

    <div
      v-if="error"
      class="error-banner"
    >
      <span>{{ error }}</span>
      <button @click="error = null">
        Dismiss
      </button>
    </div>

    <!-- Restore Draft Banner -->
    <div
      v-if="restoreAvailable"
      class="info-banner"
    >
      <span>Restaurer le brouillon non sauvegardé ({{ restoreAvailable.source }}) ?</span>
      <button
        class="btn-sm btn-primary"
        @click="restoreDraft"
      >
        Oui, restaurer
      </button>
      <button
        class="btn-sm btn-secondary"
        @click="discardDraft"
      >
        Non, supprimer
      </button>
    </div>

    <div
      v-if="isLoading"
      class="loading-state"
    >
      Loading...
    </div>
    <div
      v-else
      class="workspace"
    >
      <!-- Viewer -->
      <div class="viewer-container">
        <div class="viewer-toolbar">
          <div
            v-if="hasPages"
            class="pagination"
          >
            <button
              :disabled="currentPage <= 1"
              @click="currentPage--"
            >
              Prev
            </button>
            <span>Page {{ currentPage }} / {{ pages.length }}</span>
            <button
              :disabled="currentPage >= pages.length"
              @click="currentPage++"
            >
              Next
            </button>
          </div>
          <div
            v-else
            class="pagination"
          >
            <span>No Pages</span>
          </div>
          <div class="zoom-controls">
            <button @click="scale = Math.max(0.2, scale - 0.1)">
              -
            </button>
            <span>{{ Math.round(scale * 100) }}%</span>
            <button @click="scale = Math.min(3.0, scale + 0.1)">
              +
            </button>
          </div>
        </div>
        <div class="scroll-area">
          <div
            v-if="currentPageImageUrl && !imageError"
            class="canvas-wrapper" 
            :style="{ width: displayWidth + 'px', height: displayHeight + 'px' }"
          >
            <img
              :src="currentPageImageUrl"
              class="page-image"
              draggable="false"
              @load="handleImageLoad"
              @error="handleImageError"
            >
            <!-- Anonymization overlay: covers student identity zone on page 1 -->
            <div
              v-if="isFirstPage && !showIdentity"
              class="anonymization-overlay"
              :style="{ width: displayWidth + 'px', height: (displayHeight * 0.35) + 'px' }"
            >
              <div class="anonymization-label">
                🔒 Zone d'identification masquée
              </div>
              <button
                v-if="isAdmin"
                class="btn-sm btn-reveal"
                @click="showIdentity = true"
              >
                Révéler l'identité (Admin)
              </button>
            </div>
            <CanvasLayer
              :width="displayWidth"
              :height="displayHeight"
              :scale="scale"
              :initial-annotations="currentAnnotations"
              :enabled="canAnnotate && !showEditor"
              @annotation-created="handleDrawComplete"
            />
          </div>
          <div
            v-else-if="imageError"
            class="empty-state error-state"
          >
            <p>⚠️ Error loading image.</p>
            <button @click="fetchCopy">
              Retry
            </button>
          </div>
          <div
            v-else
            class="empty-state"
          >
            <p>No pages available.</p>
          </div>
        </div>
      </div>

      <!-- Inspector -->
      <div class="inspector-panel">
        <div class="inspector-tabs">
          <button
            :class="{ active: activeTab === 'editor' }"
            @click="activeTab = 'editor'"
          >
            Annotations
          </button>
          <button
            :class="{ active: activeTab === 'grading' }"
            @click="activeTab = 'grading'"
          >
            Barème
          </button>
          <button
            :class="{ active: activeTab === 'history' }"
            @click="activeTab = 'history'"
          >
            History
          </button>
        </div>

        <!-- Tab: Editor/List -->
        <div
          v-if="activeTab === 'editor'"
          class="tab-content"
        >
          <div
            v-if="showEditor"
            class="editor-panel"
            data-testid="editor-panel"
          >
            <h4>New Annotation</h4>
            <div class="form-group">
              <label>Type</label>
              <select v-model="draftAnnotation.type">
                <option value="COMMENT">
                  Comment
                </option>
                <option value="HIGHLIGHT">
                  Highlight
                </option>
                <option value="ERROR">
                  Error
                </option>
                <option value="BONUS">
                  Bonus
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>Points</label>
              <input
                v-model.number="draftAnnotation.score_delta"
                type="number"
                placeholder="0"
              >
            </div>
            <div class="form-group">
              <label>Content</label>
              <textarea
                ref="editorInputRef"
                v-model="draftAnnotation.content"
                @keydown.ctrl.enter="saveAnnotation"
              />
            </div>
            <div class="editor-actions">
              <button
                class="btn-sm btn-secondary"
                @click="cancelEditor"
              >
                Cancel
              </button>
              <button
                class="btn-sm btn-primary"
                @click="saveAnnotation"
              >
                Save
              </button>
            </div>
          </div>
          <div
            v-else
            class="list-panel"
          >
            <ul class="annotation-list">
              <li
                v-for="ann in currentAnnotations"
                :key="ann.id"
                class="annotation-item"
                data-testid="annotation-item"
              >
                <div class="ann-header">
                  <span class="ann-type">{{ ann.type }}</span>
                  <span
                    v-if="ann.score_delta"
                    class="ann-score"
                  >{{ ann.score_delta > 0 ? '+' : '' }}{{ ann.score_delta }}</span>
                  <button
                    v-if="canAnnotate"
                    class="btn-sm btn-delete"
                    @click="handleDeleteAnnotation(ann.id)"
                  >
                    ×
                  </button>
                </div>
                <div class="ann-content">
                  {{ ann.content }}
                </div>
              </li>
              <li
                v-if="currentAnnotations.length === 0"
                class="empty-list"
              >
                No annotations on this page.
              </li>
            </ul>
          </div>
        </div>

        <!-- Tab: Grading -->
        <div
          v-if="activeTab === 'grading'"
          class="tab-content grading-panel"
        >
          <div
            v-if="flatQuestions.length === 0"
            class="empty-list"
          >
            Aucun barème disponible pour cet examen.
          </div>
          <div
            v-else
            class="grading-content"
          >
            <div class="questions-list">
              <div
                v-for="question in flatQuestions"
                :key="question.id"
                class="question-item"
              >
                <div class="question-header">
                  <span class="question-title">{{ question.title }}</span>
                  <span class="question-max-score">/ {{ question.maxScore }} pts</span>
                </div>
                <div class="question-score-field">
                  <label :for="'score-' + question.id">Note</label>
                  <input
                    :id="'score-' + question.id"
                    type="number"
                    step="0.25"
                    min="0"
                    :max="question.maxScore"
                    :value="questionScores.get(question.id) ?? ''"
                    :disabled="isReadOnly"
                    :placeholder="isReadOnly ? '-' : '0'"
                    class="score-input"
                    :class="{ 'score-filled': questionScores.get(question.id) != null && questionScores.get(question.id) !== '' }"
                    @input="onScoreChange(question.id, $event.target.value)"
                  />
                </div>
                <div class="question-remark-field">
                  <label :for="'remark-' + question.id">Remarque (facultatif)</label>
                  <textarea
                    :id="'remark-' + question.id"
                    :value="questionRemarks.get(question.id) || ''"
                    :disabled="isReadOnly"
                    :placeholder="isReadOnly ? 'Lecture seule' : 'Ajouter une remarque...'"
                    rows="2"
                    @input="onRemarkChange(question.id, $event.target.value)"
                  />
                  <span
                    v-if="remarksSaving.get(question.id)"
                    class="save-indicator small"
                  >
                    Enregistrement...
                  </span>
                </div>
              </div>
              <div
                v-if="scoresSaving"
                class="scores-save-status"
              >
                Sauvegarde des notes...
              </div>
              <div
                v-else-if="lastScoresSaveStatus"
                class="scores-save-status"
                :class="{ 'save-ok': lastScoresSaveStatus.success, 'save-err': !lastScoresSaveStatus.success }"
              >
                {{ lastScoresSaveStatus.success ? 'Notes sauvegardées' : 'Erreur sauvegarde notes' }}
              </div>
            </div>
            
            <div class="global-appreciation-section">
              <label for="global-appreciation">Appréciation globale</label>
              <textarea
                id="global-appreciation"
                v-model="globalAppreciation"
                :disabled="isReadOnly"
                :placeholder="isReadOnly ? 'Lecture seule' : 'Ajouter une appréciation globale...'"
                rows="5"
                @input="onAppreciationChange($event.target.value)"
              />
              <span
                v-if="appreciationSaving"
                class="save-indicator small"
              >
                Enregistrement...
              </span>
            </div>
          </div>
        </div>

        <!-- Tab: History -->
        <div
          v-if="activeTab === 'history'"
          class="tab-content history-panel"
        >
          <ul class="history-list">
            <li
              v-for="log in historyLogs"
              :key="log.id"
              class="history-item"
            >
              <div class="log-meta">
                <span class="log-actor">{{ log.actor_username }}</span>
                <span class="log-date">{{ formatDate(log.timestamp) }}</span>
              </div>
              <div class="log-action">
                <strong>{{ log.action_display }}</strong>
              </div>
            </li>
            <li
              v-if="historyLogs.length === 0"
              class="empty-list"
            >
              No history available.
            </li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.corrector-desk { display: flex; flex-direction: column; height: 100vh; background: #e9ecef; }
.toolbar { padding: 10px 20px; background: #343a40; color: white; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.copy-info { margin-left: 15px; font-size: 1.1rem; }
.status-badge { padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 5px; text-transform: uppercase; font-weight: bold; }
.status-ready { background: #28a745; color: white; }
.status-locked { background: #dc3545; color: white; }
.status-staging { background: #6c757d; color: white; }
.status-graded { background: #17a2b8; color: white; }
.save-indicator { font-size: 0.8rem; color: #adb5bd; margin-right: 15px; font-style: italic; }

.actions button { margin-left: 10px; padding: 6px 12px; border-radius: 4px; cursor: pointer; font-weight: 500; }
.actions button:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-primary { background: #007bff; color: white; border: none; }
.btn-danger { background: #dc3545; color: white; border: none; }
.btn-success { background: #28a745; color: white; border: none; }
.btn-warning { background: #ffc107; border: none; }
.btn-info { background: #17a2b8; color: white; border: none; }
.btn-secondary { background: #6c757d; color: white; border: none; }
.btn-sm { padding: 2px 6px; font-size: 0.85rem; }

.workspace { display: flex; flex: 1; overflow: hidden; }
.viewer-container { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.viewer-toolbar { padding: 10px; background: white; border-bottom: 1px solid #dee2e6; display: flex; justify-content: center; gap: 20px; align-items: center; }
.scroll-area { flex: 1; overflow: auto; background: #525659; display: flex; justify-content: center; padding: 20px; }

.canvas-wrapper { position: relative; background: white; box-shadow: 0 0 15px rgba(0,0,0,0.3); }
.page-image { width: 100%; height: 100%; display: block; }

.anonymization-overlay {
    position: absolute;
    top: 0;
    left: 0;
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    z-index: 10;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: 12px;
    border-bottom: 3px solid #f59e0b;
}
.anonymization-label {
    color: white;
    font-size: 1.1rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-shadow: 0 1px 3px rgba(0,0,0,0.3);
}
.btn-reveal {
    background: rgba(255,255,255,0.15);
    color: #fbbf24;
    border: 1px solid rgba(251,191,36,0.4);
    padding: 4px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8rem;
    transition: background 0.2s;
}
.btn-reveal:hover { background: rgba(255,255,255,0.25); }

.inspector-panel { width: 320px; background: white; border-left: 1px solid #dee2e6; display: flex; flex-direction: column; }
.inspector-tabs { display: flex; border-bottom: 1px solid #dee2e6; }
.inspector-tabs button { flex: 1; padding: 10px; border: none; background: #f8f9fa; cursor: pointer; font-weight: bold; color: #666; }
.inspector-tabs button.active { background: white; color: #007bff; border-bottom: 2px solid #007bff; }

.tab-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }

.list-panel, .history-panel { flex: 1; overflow-y: auto; }
.editor-panel { padding: 15px; background: #fff3cd; border-bottom: 1px solid #ffeeba; }

.form-group { margin-bottom: 15px; display: flex; flex-direction: column; }
.form-group label { font-weight: bold; margin-bottom: 5px; font-size: 0.9rem; }
.form-group textarea { height: 80px; resize: vertical; padding: 8px; }
.form-group input, .form-group select { padding: 8px; }
.editor-actions { display: flex; gap: 10px; justify-content: flex-end; }

.annotation-list, .history-list { list-style: none; padding: 0; margin: 0; }
.annotation-item { padding: 10px 15px; border-bottom: 1px solid #eee; }
.ann-header { display: flex; justify-content: space-between; margin-bottom: 5px; }
.ann-type { font-weight: bold; font-size: 0.9rem; color: #007bff; }
.ann-score { font-size: 0.85rem; color: #666; font-weight: bold; }
.ann-content { font-size: 0.9rem; color: #555; white-space: pre-wrap; }
.btn-delete { background: none; border: none; color: #dc3545; font-size: 1.2rem; cursor: pointer; padding: 0 5px; }

.history-item { padding: 10px 15px; border-bottom: 1px solid #eee; font-size: 0.9rem; }
.log-meta { display: flex; justify-content: space-between; color: #666; font-size: 0.8rem; margin-bottom: 3px; }
.log-action { color: #333; }

.error-banner { background: #f8d7da; color: #721c24; padding: 10px; text-align: center; border-bottom: 1px solid #f5c6cb; }
.info-banner { background: #d1ecf1; color: #0c5460; padding: 10px; text-align: center; border-bottom: 1px solid #bee5eb; display: flex; justify-content: center; gap: 10px; align-items: center; }
.loading-state { flex: 1; display: flex; justify-content: center; align-items: center; font-size: 1.5rem; color: #666; }
.empty-list, .empty-state { padding: 20px; text-align: center; color: #999; }
.error-state p { color: #dc3545; font-weight: bold; }

.grading-panel { flex: 1; overflow-y: auto; }
.grading-content { padding: 15px; }
.questions-list { margin-bottom: 20px; }
.question-item { margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 6px; border: 1px solid #dee2e6; }
.question-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.question-title { font-weight: bold; font-size: 0.95rem; color: #333; }
.question-max-score { font-size: 0.85rem; color: #666; background: #e9ecef; padding: 2px 8px; border-radius: 4px; }
.question-score-field { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.question-score-field label { font-size: 0.85rem; color: #333; font-weight: 600; min-width: 40px; }
.score-input { width: 80px; padding: 6px 8px; border: 2px solid #ced4da; border-radius: 4px; font-size: 1rem; font-weight: 600; text-align: center; transition: border-color 0.2s; }
.score-input:focus { outline: none; border-color: #007bff; box-shadow: 0 0 0 0.2rem rgba(0,123,255,0.25); }
.score-input.score-filled { border-color: #28a745; background: #f0fff4; }
.score-input:disabled { background: #e9ecef; cursor: not-allowed; }
.question-remark-field { display: flex; flex-direction: column; }
.question-remark-field label { font-size: 0.85rem; color: #666; margin-bottom: 5px; }
.question-remark-field textarea { padding: 8px; border: 1px solid #ced4da; border-radius: 4px; font-size: 0.9rem; font-family: inherit; resize: vertical; }
.question-remark-field textarea:focus { outline: none; border-color: #007bff; box-shadow: 0 0 0 0.2rem rgba(0,123,255,0.25); }
.question-remark-field textarea:disabled { background: #e9ecef; cursor: not-allowed; }
.save-indicator.small { font-size: 0.75rem; color: #28a745; margin-top: 3px; font-style: italic; }
.scores-save-status { text-align: center; padding: 6px; font-size: 0.8rem; font-style: italic; margin-top: 8px; }
.scores-save-status.save-ok { color: #28a745; }
.scores-save-status.save-err { color: #dc3545; }
.btn-disabled { opacity: 0.5; cursor: not-allowed; }

.global-appreciation-section { padding: 20px; background: #fff3cd; border-radius: 6px; border: 1px solid #ffeeba; }
.global-appreciation-section label { font-weight: bold; font-size: 1rem; color: #333; margin-bottom: 10px; display: block; }
.global-appreciation-section textarea { width: 100%; padding: 10px; border: 1px solid #ced4da; border-radius: 4px; font-size: 0.95rem; font-family: inherit; resize: vertical; }
.global-appreciation-section textarea:focus { outline: none; border-color: #ffc107; box-shadow: 0 0 0 0.2rem rgba(255,193,7,0.25); }
.global-appreciation-section textarea:disabled { background: #e9ecef; cursor: not-allowed; }
</style>
