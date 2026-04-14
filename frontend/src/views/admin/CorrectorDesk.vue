<script setup>
import { ref, onMounted, computed, watch, nextTick, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import gradingApi from '../../services/gradingApi'
import CanvasLayer from '../../components/CanvasLayer.vue'
import AnnotationSuggestionsPanel from '../../components/AnnotationSuggestionsPanel.vue'
import CommentBank from '../../components/CommentBank.vue'
import AppIcon from '../../icons/AppIcon.vue'
import { computeGradingProgress } from '../../utils/gradingProgress'
// Removed date-fns, using native Intl
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
let copyId = route.params.copyId

// --- Labels FR ---
const statusLabels = {
  'READY': 'Prêt',
  'IN_PROGRESS': 'En cours',
  'FINALIZED': 'Finalisée',
}
const getStatusLabel = (status) => statusLabels[status] || status

// --- State ---
const copy = ref(null)
const isLoading = ref(true)
const isSaving = ref(false)
const error = ref(null)
const annotations = ref([])
const historyLogs = ref([])
const isTouch = ref(matchMedia('(pointer: coarse)').matches)

// --- Sibling copy navigation ---
const siblingCopies = ref([])  // [{id, anonymous_id, status}] ordered by anonymous_id
const currentSiblingIndex = computed(() => siblingCopies.value.findIndex(c => c.id === copyId))
const prevCopy = computed(() => currentSiblingIndex.value > 0 ? siblingCopies.value[currentSiblingIndex.value - 1] : null)
const nextCopy = computed(() => currentSiblingIndex.value >= 0 && currentSiblingIndex.value < siblingCopies.value.length - 1 ? siblingCopies.value[currentSiblingIndex.value + 1] : null)
const copyPositionLabel = computed(() => {
    if (currentSiblingIndex.value < 0 || siblingCopies.value.length === 0) return ''
    return `${currentSiblingIndex.value + 1} / ${siblingCopies.value.length}`
})

// Viewer
const scale = ref(1.0)
const currentPage = ref(1)
const pdfDimensions = ref({ width: 0, height: 0 })
const imageError = ref(false)
const imageLoaded = ref(false)
const scrollAreaRef = ref(null)

// Continuous scroll: all pages stacked vertically
const pageElements = ref([])
const loadedPages = ref(new Set())
const setPageRef = (el, idx) => { pageElements.value[idx] = el }
let scrollRaf = null
const updateCurrentPageFromScroll = () => {
    if (scrollRaf) return
    scrollRaf = requestAnimationFrame(() => {
        scrollRaf = null
        if (!scrollAreaRef.value || pageElements.value.length === 0) return
        const scrollRect = scrollAreaRef.value.getBoundingClientRect()
        const viewportCenter = scrollRect.top + scrollRect.height / 2
        let closest = 0
        let minDist = Infinity
        for (let i = 0; i < pageElements.value.length; i++) {
            const el = pageElements.value[i]
            if (!el) continue
            const elRect = el.getBoundingClientRect()
            const pageCenter = elRect.top + elRect.height / 2
            const dist = Math.abs(pageCenter - viewportCenter)
            if (dist < minDist) { minDist = dist; closest = i }
        }
        currentPage.value = closest + 1
    })
}

// Autosave State
const restoreAvailable = ref(null) // { source: 'LOCAL'|'SERVER', payload: ... }
const autosaveTimer = ref(null)
const localSaveTimer = ref(null)
const getSessionClientId = () => {
    const key = `korrigo_client_id_${copyId}`
    let id = sessionStorage.getItem(key)
    if (!id) {
        id = crypto.randomUUID()
        sessionStorage.setItem(key, id)
    }
    return id
}
const clientId = ref(getSessionClientId())
const lastSaveStatus = ref(null) // { source: 'LOCAL'|'SERVER', time: Date }

// UI State — Single annotation mode (structurally prevents conflicting active states)
// group: 'stamp' (V/F) | 'type' (Commentaire/Surlignage/Erreur/Bonus) | null
// value: 'VRAI'|'FAUX' | 'COMMENTAIRE'|'SURLIGNAGE'|'ERREUR'|'BONUS' | null
const annotationMode = ref({ group: null, value: null })
const setAnnotationMode = (group, value) => {
    if (annotationMode.value.group === group && annotationMode.value.value === value) {
        annotationMode.value = { group: null, value: null }
    } else {
        annotationMode.value = { group, value }
    }
}
const quickStampMode = computed(() => annotationMode.value.group === 'stamp' ? annotationMode.value.value : null)
const preSelectedAnnotationType = computed(() => annotationMode.value.group === 'type' ? annotationMode.value.value : null)

// Editor
const showEditor = ref(false) // Overlay editor
const draftAnnotation = ref(null) // { normalizedRect, type, content }
const editorInputRef = ref(null)

// Grading / Remarks / Scores
const questionRemarks = ref(new Map()) // Map<question_id, remark_text>
const questionScores = ref(new Map()) // Map<question_id, score_value>
const questionScoreTexts = ref(new Map()) // Map<question_id, raw_input_text> — preserves comma while typing
const globalAppreciation = ref('')
const remarksSaving = ref(new Map()) // Map<question_id, boolean> for save indicators
const scoresSaving = ref(false)
const appreciationSaving = ref(false)
const remarkTimers = ref(new Map()) // Map<question_id, timerId> for debouncing
const scoresTimer = ref(null)
const appreciationTimer = ref(null)
const lastScoresSaveStatus = ref(null) // { time: Date, success: boolean }

// --- Sync Protection State ---
const pendingScoresChange = ref(false)
const pendingRemarksChanges = ref(new Set()) // Set<question_id>
const pendingAppreciationChange = ref(false)
const syncErrors = ref([]) // Array<{ type: string, time: Date, message: string }>
const isOnline = ref(navigator.onLine)
const lastServerConfirm = ref(null) // Date of last successful server save
const consecutiveFailures = ref(0)

const hasPendingChanges = computed(() => {
    return pendingScoresChange.value || pendingRemarksChanges.value.size > 0 || pendingAppreciationChange.value
})

const syncStatusLevel = computed(() => {
    if (!isOnline.value) return 'offline'
    if (consecutiveFailures.value >= 3) return 'critical'
    if (syncErrors.value.length > 0 || hasPendingChanges.value) return 'warning'
    return 'ok'
})

// Suggestions panel
const showSuggestions = ref(false)
const suggestionsExercise = ref(null)
const suggestionsQuestion = ref(null)

const showCommentBank = ref(false)
const activeRemarkQuestionId = ref(null)

// --- Computed ---
const isStaging = computed(() => false)
const isReady = computed(() => copy.value?.status === 'READY')
const isInProgress = computed(() => copy.value?.status === 'IN_PROGRESS')
const isFinalized = computed(() => copy.value?.status === 'FINALIZED')
const isGraded = isFinalized // alias for backward compatibility

// Anonymization: hide student identity only on header pages (1+4*N, i.e. 1, 5, 9, 13…)
// Rule: mask pages at positions 1, 1+ppb, 1+2*ppb, … — strictly no other pages.
const isAdmin = computed(() => authStore.user?.is_superuser || authStore.user?.role === 'Admin')
const showIdentity = ref(false) // Only admin can toggle this
// Per-page anonymization helpers (used in v-for template)
const isHeaderPageForIndex = (pageIndex) => {
    const ppb = copy.value?.exam_details?.pages_per_booklet || 4
    const page = pageIndex + 1
    return ((page - 1) % ppb) === 0
}
// All masked pages use the same overlay height (identity header zone)
const overlayHeightForIndex = () => '23%'

const isAssignedCorrector = computed(() => {
    const userId = authStore.user?.id
    const correctorId = copy.value?.assigned_corrector?.id || copy.value?.assigned_corrector
    return userId && correctorId && String(userId) === String(correctorId)
})
const isReadOnly = computed(() => isFinalized.value && !isAdmin.value && !isAssignedCorrector.value)
const canAnnotate = computed(() => (isReady.value || isInProgress.value || (isFinalized.value && (isAdmin.value || isAssignedCorrector.value))) && !isReadOnly.value)
const examId = computed(() => copy.value?.exam_details?.id || copy.value?.exam || null)


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

// Continuous scroll: per-page URL and annotations helpers
const getPageUrl = (pageIndex) => {
    if (pageIndex < 0 || pageIndex >= pages.value.length) return null
    return gradingApi.getMediaUrl(pages.value[pageIndex])
}
const getAnnotationsForPage = (pageIndex) => {
    return annotations.value.filter(a => a.page_index === pageIndex)
}

const displayWidth = computed(() => pdfDimensions.value.width * scale.value)
const displayHeight = computed(() => pdfDimensions.value.height * scale.value)

const gradingStructure = computed(() => {
    if (!copy.value?.exam_details?.grading_structure) return []
    return copy.value.exam_details.grading_structure
})

// Build a grading node recursively using item.id from the structure (UUID or string).
// Returns: { id, label, points, isLeaf, questions: [...], groups: [...] }
// - isLeaf: no children → one score input for this item itself
// - questions: direct leaf children → score inputs
// - groups: intermediate children (sub-exercises) → recursive nodes
//
// When item.id is missing (legacy structures like BB_J1), a positional ID is generated
// using the same "exerciseIdx.questionIdx" scheme used in scores_data.
// Helper: get points from any field name variant
const getPoints = (item) => item.points || item.maxScore || item.max_score || item.max_points || 0

const buildGradingNode = (item, positionPrefix = '') => {
    const nodeId = item.id || positionPrefix || 'node'
    const hasChildren = item.children && item.children.length > 0
    if (!hasChildren) {
        const pts = getPoints(item)
        return {
            id: nodeId,
            label: item.label || item.title || nodeId,
            points: pts,
            isLeaf: true,
            questions: [{ id: nodeId, title: item.label || item.title || nodeId, maxScore: pts }],
            groups: [],
        }
    }
    const childrenAreLeaves = item.children.every(c => !c.children || c.children.length === 0)
    if (childrenAreLeaves) {
        const questions = item.children.map((c, idx) => ({
            id: c.id || `${positionPrefix}.${idx + 1}`,
            title: c.label || c.title || c.id || `Q${idx + 1}`,
            maxScore: getPoints(c),
        }))
        return {
            id: nodeId,
            label: item.label || item.title || nodeId,
            points: item.children.reduce((s, c) => s + getPoints(c), 0),
            isLeaf: false,
            questions,
            groups: [],
        }
    }
    // Children are intermediate nodes (sub-exercises)
    const groups = item.children.map((child, idx) => buildGradingNode(child, child.id || `${positionPrefix}.${idx + 1}`))
    return {
        id: nodeId,
        label: item.label || item.title || nodeId,
        points: groups.reduce((s, g) => s + g.points, 0),
        isLeaf: false,
        questions: [],
        groups,
    }
}

// Recursively collect all leaf questions from a node list
const collectLeafQuestions = (nodes) => {
    let result = []
    for (const node of nodes) {
        if (node.isLeaf || node.questions.length > 0) result = result.concat(node.questions)
        if (node.groups.length > 0) result = result.concat(collectLeafQuestions(node.groups))
    }
    return result
}

const flatQuestions = computed(() => collectLeafQuestions(exercisesWithQuestions.value))

// Accordion state: Set of open IDs for exercises and sub-groups independently
const openExerciseId = ref(null)
const openGroupId = ref(null)
const toggleExercise = (id) => {
    openExerciseId.value = openExerciseId.value === id ? null : id
    openGroupId.value = null // ferme tout sous-groupe quand on change d'exercice
}
const toggleGroup = (id) => {
    openGroupId.value = openGroupId.value === id ? null : id
}
// Compat: les templates utilisent .has() — on expose des pseudo-Sets via computed
const openExerciseIds = computed(() => ({ has: (id) => openExerciseId.value === id }))
const openGroupIds = computed(() => ({ has: (id) => openGroupId.value === id }))

// Hierarchical structure: top-level exercises, each may have groups (sub-exercises)
const exercisesWithQuestions = computed(() => {
    const structure = gradingStructure.value
    if (!structure || structure.length === 0) return []
    return structure.map((item, idx) => buildGradingNode(item, item.id || String(idx + 1)))
})

// --- Page Navigation Helpers (scroll to page in continuous view) ---
const goNextPage = () => {
    const next = currentPage.value // 0-based index of next page
    if (next < pages.value.length) {
        const el = pageElements.value[next]
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
}
const goPrevPage = () => {
    const prev = currentPage.value - 2 // 0-based index of previous page
    if (prev >= 0) {
        const el = pageElements.value[prev]
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
}

// --- Fit to width helper ---
const fitToWidth = () => {
    if (!scrollAreaRef.value || !pdfDimensions.value.width) return
    const availableWidth = scrollAreaRef.value.clientWidth - 40 // 20px padding each side
    const newScale = availableWidth / pdfDimensions.value.width
    scale.value = Math.max(0.3, Math.min(3.0, +(newScale.toFixed(2))))
}

// --- Scroll-wheel: Ctrl+wheel = zoom (natural scroll handles page navigation) ---
const onScrollAreaWheel = (e) => {
    if (!scrollAreaRef.value) return
    // Ctrl+wheel or pinch-zoom → zoom in/out
    if (e.ctrlKey || e.metaKey) {
        e.preventDefault()
        const delta = e.deltaY > 0 ? -0.1 : 0.1
        scale.value = Math.max(0.3, Math.min(3.0, +(scale.value + delta).toFixed(1)))
    }
    // Plain scroll: handled natively by the scroll-area (continuous scroll)
}

// --- Global Key Handling ---
const onGlobalKeydown = (e) => {
    // Skip navigation shortcuts when typing in an input/textarea
    const tag = e.target?.tagName
    const isTyping = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT'

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

    // Page navigation: ←→ arrows and PageUp/PageDown
    if (!isTyping && !showEditor.value) {
        if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
            e.preventDefault()
            goPrevPage()
        } else if (e.key === 'ArrowRight' || e.key === 'PageDown') {
            e.preventDefault()
            goNextPage()
        }
        // Annotation shortcuts: V=Vrai, F=Faux, C=Commentaire, E=Erreur
        if (e.key === 'v' || e.key === 'V') { e.preventDefault(); setAnnotationMode('stamp', 'VRAI') }
        if (e.key === 'f' || e.key === 'F') { e.preventDefault(); setAnnotationMode('stamp', 'FAUX') }
        if (e.key === 'c' || e.key === 'C') { e.preventDefault(); setAnnotationMode('type', 'COMMENTAIRE') }
        if (e.key === 'e' || e.key === 'E') { e.preventDefault(); setAnnotationMode('type', 'ERREUR') }
    }
}

// --- Watchers ---
// Continuous scroll: currentPage is tracked by scroll position, no image/scroll reset needed.

watch(pages, (newPages) => {
    if (newPages.length === 0) {
        currentPage.value = 1
        pdfDimensions.value = { width: 0, height: 0 }
    } else {
        if (currentPage.value > newPages.length) currentPage.value = newPages.length
        else if (currentPage.value < 1) currentPage.value = 1
    }
    // Reset page element refs array
    pageElements.value = new Array(newPages.length).fill(null)
    loadedPages.value = new Set()
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
        error.value = "Accès refusé : vous n'avez pas la permission de voir cette copie."
    } else {
        error.value = err.response?.data?.detail || "Échec du chargement de la copie"
    }
  } finally {
    isLoading.value = false
  }
}

const fetchSiblingCopies = async () => {
    if (!copy.value?.exam_details?.id) return
    try {
        const allCopies = await gradingApi.listCopies()
        const examId = copy.value.exam_details.id
        siblingCopies.value = allCopies
            .filter(c => c.exam === examId || c.exam_details?.id === examId)
            .map(c => ({ id: c.id, anonymous_id: c.anonymous_id, status: c.status }))
    } catch (err) {
        console.warn('Failed to load sibling copies for navigation', err)
    }
}

const navigateToCopy = (targetCopy) => {
    if (!targetCopy) return
    if (hasPendingChanges.value) {
        const ok = window.confirm('Des modifications sont en cours de synchronisation. Voulez-vous quitter cette copie ?')
        if (!ok) return
    }
    router.push(`/corrector/desk/${targetCopy.id}`)
}

const refreshAnnotations = async () => {
    try {
        annotations.value = await gradingApi.listAnnotations(copyId)
    } catch { /* annotations may not exist yet */ }
}

const fetchHistory = async () => {
    try {
        historyLogs.value = await gradingApi.listAuditLogs(copyId)
    } catch { /* history may not exist yet */ }
}

const fetchRemarks = async () => {
    try {
        const remarks = await gradingApi.fetchRemarks(copyId)
        const remarksMap = new Map()
        remarks.forEach(r => {
            remarksMap.set(r.question_id, r.remark)
        })
        questionRemarks.value = remarksMap
    } catch { /* 403/404 expected for copies without remarks yet */ }
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
    } catch { /* 403/404 expected for copies without scores yet */ }
}

const fetchGlobalAppreciation = async () => {
    try {
        const response = await gradingApi.fetchGlobalAppreciation(copyId)
        globalAppreciation.value = response.global_appreciation || ''
    } catch { /* appreciation may not exist yet */ }
}

const saveRemark = async (questionId, remark) => {
    remarksSaving.value.set(questionId, true)
    try {
        await gradingApi.saveRemark(copyId, questionId, remark)
        // Auto-save substantial remarks to personal annotation bank for reuse across copies
        autoSaveRemarkToBank(questionId, remark)
        const newPending = new Set(pendingRemarksChanges.value)
        newPending.delete(questionId)
        pendingRemarksChanges.value = newPending
        consecutiveFailures.value = 0
        lastServerConfirm.value = new Date()
        syncErrors.value = syncErrors.value.filter(e => e.type !== `remark_${questionId}`)
    } catch (err) {
        console.error("Failed to save remark", err)
        consecutiveFailures.value++
        syncErrors.value = syncErrors.value.filter(e => e.type !== `remark_${questionId}`)
        syncErrors.value.push({ type: `remark_${questionId}`, time: new Date(), message: err.message || 'Échec sauvegarde remarque' })
    } finally {
        remarksSaving.value.set(questionId, false)
    }
}

const saveGlobalAppreciationToServer = async () => {
    appreciationSaving.value = true
    try {
        await gradingApi.saveGlobalAppreciation(copyId, globalAppreciation.value)
        pendingAppreciationChange.value = false
        consecutiveFailures.value = 0
        lastServerConfirm.value = new Date()
        syncErrors.value = syncErrors.value.filter(e => e.type !== 'appreciation')
    } catch (err) {
        console.error("Failed to save global appreciation", err)
        consecutiveFailures.value++
        syncErrors.value = syncErrors.value.filter(e => e.type !== 'appreciation')
        syncErrors.value.push({ type: 'appreciation', time: new Date(), message: err.message || 'Échec sauvegarde appréciation' })
    } finally {
        appreciationSaving.value = false
    }
}

const onRemarkChange = (questionId, value) => {
    questionRemarks.value.set(questionId, value)
    const newPending = new Set(pendingRemarksChanges.value)
    newPending.add(questionId)
    pendingRemarksChanges.value = newPending
    // localStorage fallback for remarks
    try {
        const remarksObj = {}
        questionRemarks.value.forEach((val, key) => { remarksObj[key] = val })
        localStorage.setItem(`korrigo_remarks_${copyId}`, JSON.stringify(remarksObj))
    } catch { /* localStorage full, ignore */ }

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
    pendingAppreciationChange.value = true
    // localStorage fallback for appreciation
    try {
        localStorage.setItem(`korrigo_appreciation_${copyId}`, value)
    } catch { /* localStorage full, ignore */ }

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
        pendingScoresChange.value = false
        consecutiveFailures.value = 0
        lastServerConfirm.value = new Date()
        syncErrors.value = syncErrors.value.filter(e => e.type !== 'scores')
    } catch (err) {
        console.error("Failed to save scores", err)
        lastScoresSaveStatus.value = { time: new Date(), success: false }
        consecutiveFailures.value++
        syncErrors.value = syncErrors.value.filter(e => e.type !== 'scores')
        syncErrors.value.push({ type: 'scores', time: new Date(), message: err.message || 'Échec sauvegarde notes' })
    } finally {
        scoresSaving.value = false
    }
}

const quickVals = (max) => {
    if (!max || max <= 0) return [0]
    const s = new Set([0])
    if (max >= 0.5) s.add(0.25)
    if (max >= 1) s.add(0.5)
    if (max >= 2) s.add(1)
    s.add(max)
    return [...s].sort((a, b) => a - b)
}

const EXERCISE_COLORS = [
    { bar: '#7F77DD', bg: '#EEEDFE', text: '#534AB7' },
    { bar: '#378ADD', bg: '#E6F1FB', text: '#185FA5' },
    { bar: '#1D9E75', bg: '#E1F5EE', text: '#0F6E56' },
    { bar: '#D85A30', bg: '#FAECE7', text: '#993C1D' },
    { bar: '#D4537E', bg: '#FBEAF0', text: '#993556' },
    { bar: '#639922', bg: '#EAF3DE', text: '#3B6D11' },
]
const getExerciseColor = (index) => EXERCISE_COLORS[index % EXERCISE_COLORS.length]

const stepScore = (questionId, maxScore, delta) => {
    const current = questionScores.value.get(questionId) || 0
    let next = Math.round((current + delta) * 4) / 4
    if (next < 0) next = 0
    if (next > maxScore) next = maxScore
    onScoreChange(questionId, String(next))
}

const onScoreChange = (questionId, value) => {
    // Keep raw text so Vue doesn't overwrite mid-typing (e.g. "0," → 0 → erases comma)
    questionScoreTexts.value.set(questionId, value)
    if (value === '' || value === null || value === undefined) {
        questionScores.value.set(questionId, null)
    } else {
        const normalized = String(value).replace(',', '.')
        // Allow trailing dot/comma so user can keep typing (e.g. "0." or "1,")
        if (normalized.endsWith('.') || !/\d/.test(normalized)) {
            // Don't parse yet — wait for more input
            pendingScoresChange.value = true
            return
        }
        let parsed = parseFloat(normalized)
        if (isNaN(parsed)) {
            questionScores.value.set(questionId, null)
        } else {
            // Clamp: score must be >= 0
            if (parsed < 0) parsed = 0
            // Clamp: score must not exceed question maxScore
            const question = flatQuestions.value.find(q => q.id === questionId)
            if (question && parsed > question.maxScore) parsed = question.maxScore
            questionScores.value.set(questionId, parsed)
        }
    }
    pendingScoresChange.value = true
    // Also save to localStorage as fallback
    try {
        const scoresObj = {}
        questionScores.value.forEach((val, key) => { scoresObj[key] = val })
        localStorage.setItem(`korrigo_scores_${copyId}`, JSON.stringify(scoresObj))
    } catch { /* localStorage full, ignore */ }

    if (scoresTimer.value) {
        clearTimeout(scoresTimer.value)
    }
    scoresTimer.value = setTimeout(() => {
        saveScoresToServer()
    }, 800)
}

const onScoreBlur = (questionId) => {
    // On blur, finalize: parse any trailing comma/dot, clear raw text so display shows clean number
    const raw = questionScoreTexts.value.get(questionId)
    if (raw != null && raw !== '') {
        const normalized = String(raw).replace(',', '.')
        let parsed = parseFloat(normalized)
        if (!isNaN(parsed)) {
            if (parsed < 0) parsed = 0
            const question = flatQuestions.value.find(q => q.id === questionId)
            if (question && parsed > question.maxScore) parsed = question.maxScore
            questionScores.value.set(questionId, parsed)
        }
    }
    // Clear raw text — display will fall back to the clean parsed number
    questionScoreTexts.value.delete(questionId)
    // Trigger save if there was a pending trailing comma/dot
    if (pendingScoresChange.value) {
        if (scoresTimer.value) clearTimeout(scoresTimer.value)
        saveScoresToServer()
    }
}

// Total score computed from ALL loaded scores (not just those matching grading_structure)
// This handles exams where grading_structure IDs don't match scores_data keys (e.g. BB_J1)
const totalScore = computed(() => {
    let sum = 0
    for (const [, val] of questionScores.value) {
        if (val !== null && val !== undefined && val !== '') {
            sum += parseFloat(val) || 0
        }
    }
    return Math.round(sum * 100) / 100
})

// Score validation: total must not exceed 20
const scoreExceeds20 = computed(() => totalScore.value > 20)

// Per-exercise score breakdown for corrector overview
const exerciseScoreBreakdown = computed(() => {
    const result = {}
    for (const exercise of exercisesWithQuestions.value) {
        const leaves = exercise.isLeaf ? exercise.questions : collectLeafQuestions([exercise])
        let sum = 0
        let filled = 0
        for (const q of leaves) {
            const score = questionScores.value.get(q.id)
            if (score !== null && score !== undefined && score !== '') {
                sum += parseFloat(score) || 0
                filled++
            }
        }
        result[exercise.id] = {
            obtained: Math.round(sum * 100) / 100,
            max: exercise.points,
            filled,
            total: leaves.length
        }
    }
    return result
})
const gradingProgress = computed(() => computeGradingProgress(flatQuestions.value, questionScores.value))
const hasIncompleteScores = computed(() => gradingProgress.value.total > 0 && gradingProgress.value.scored < gradingProgress.value.total)

// Check if copy can be finalized (all scores filled + total <= 20 + appreciation)
const canFinalize = computed(() => {
    // If grading_structure has mapped questions, check all are filled
    if (flatQuestions.value.length > 0) {
        for (const q of flatQuestions.value) {
            const score = questionScores.value.get(q.id)
            if (score === null || score === undefined || score === '') return false
        }
    } else {
        // No grading_structure: require at least one score entered
        if (questionScores.value.size === 0) return false
    }
    // Total must not exceed 20
    if (scoreExceeds20.value) return false
    // Appreciation must be filled
    if (!globalAppreciation.value || globalAppreciation.value.trim() === '') return false
    return true
})

const handleMarkReady = async () => {
    if (isSaving.value) return; isSaving.value = true;
    try { 
        await gradingApi.readyCopy(copyId); 
        await fetchCopy(); 
    }
    catch (err) { error.value = err.response?.data?.detail || "Échec de l'action"; } 
    finally { isSaving.value = false; }
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
         // Scroll to the page in continuous view
         if (typeof data.page_index === 'number') {
             currentPage.value = data.page_index + 1;
             nextTick(() => {
                 const el = pageElements.value[data.page_index]
                 if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
             })
         }

         // It's a draft annotation — open editor with page context
         const pageIdx = typeof data.page_index === 'number' ? data.page_index : currentPage.value - 1
         handleDrawComplete(data.rect, null, pageIdx);
         draftAnnotation.value = {
            rect: data.rect,
            type: data.type,
            content: data.content,
            page_index: pageIdx
         };
    }
    
    restoreAvailable.value = null;
}

const discardDraft = async () => {
    localStorage.removeItem(getStorageKey());
    // Also clear server to prevent 409 on next save (Start Fresh)
    try { await gradingApi.deleteDraft(copyId); } catch {}
    restoreAvailable.value = null;
}

watch(draftAnnotation, (newVal) => {
    if (!newVal) return;
    if (isReadOnly.value) return;
    if (!authStore.user?.id) return; // Prevent saving to 'anon' key
    
    // Construct full payload with Context (use draft's page_index if available)
    const savePayload = {
        ...newVal,
        page_index: newVal.page_index ?? (currentPage.value - 1),
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
        try {
           await gradingApi.saveDraft(copyId, savePayload, null, clientId.value);
           lastSaveStatus.value = { source: 'SERVER', time: new Date() };
        } catch (e) { console.error("Autosave failed", e); }
    }, 2000); // 2s debounce

}, { deep: true });

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
        const result = await gradingApi.finalizeCopy(copyId);
        if (result.warnings?.length) {
            alert('Avertissement : ' + result.warnings.join('\n'))
        }
        await fetchCopy();
    }
    catch (err) { error.value = err.response?.data?.detail || "Échec de l'action"; }
    finally { isSaving.value = false; }
}

const handleDownload = () => {
  const url = gradingApi.getFinalPdfUrl(copyId)
  window.open(url, '_blank')
}

const handleForceUnlock = async () => {
    if (!isAdmin.value) return
    if (!confirm('Êtes-vous sûr de vouloir déverrouiller cette copie ? Le correcteur en cours perdra son verrou.')) return
    if (isSaving.value) return
    isSaving.value = true
    try {
        await gradingApi.forceUnlockCopy(copyId)
        await fetchCopy()
    } catch (err) {
        error.value = err.response?.data?.detail || 'Échec du déverrouillage'
    } finally {
        isSaving.value = false
    }
}

const handleReopenCopy = async () => {
    if (!isAdmin.value || !isGraded.value) return
    if (!confirm('Rouvrir cette copie invalidera le PDF final généré. Êtes-vous sûr de vouloir continuer ?')) return
    if (isSaving.value) return
    isSaving.value = true
    try {
        await gradingApi.reopenCopy(copyId)
        await fetchCopy()
    } catch (err) {
        error.value = err.response?.data?.detail || 'Échec de la réouverture'
    } finally {
        isSaving.value = false
    }
}

const handleImageLoad = (e, pageIdx) => {
    imageError.value = false
    imageLoaded.value = true
    if (typeof pageIdx === 'number') loadedPages.value.add(pageIdx)
    // Set dimensions from first loaded image (all pages same size in an exam)
    if (pdfDimensions.value.width === 0) {
        pdfDimensions.value = { width: e.target.naturalWidth, height: e.target.naturalHeight }
    }
}

const handleImageError = () => {
    imageError.value = true
    error.value = "Échec du chargement de l'image de la page."
}

// --- Drag and Drop Handlers ---
const handleDragStart = (type, e) => {
    e.dataTransfer.setData('text/plain', type)
    e.dataTransfer.effectAllowed = 'copy'
}

// Feedback visuel pour le drag-and-drop (per-page via e.currentTarget)
const handleDragEnter = (e) => {
    e.preventDefault()
    e.currentTarget.classList.add('drag-over')
}

const handleDragLeave = (e) => {
    const wrapper = e.currentTarget
    if (wrapper && !wrapper.contains(e.relatedTarget)) {
        wrapper.classList.remove('drag-over')
    }
}

const handleDrop = async (e, pageIndex) => {
    e.preventDefault()
    e.currentTarget.classList.remove('drag-over')
    if (!canAnnotate.value || showEditor.value) return
    const dropPageIndex = typeof pageIndex === 'number' ? pageIndex : currentPage.value - 1

    const textData = e.dataTransfer.getData('text/plain')
    let typeValue = textData
    let contentValue = ''

    if (textData.startsWith('COMMENTBANK|')) {
        typeValue = 'COMMENTAIRE'
        contentValue = textData.replace('COMMENTBANK|', '')
    }

    if (!['VRAI', 'FAUX', 'COMMENTAIRE', 'SURLIGNAGE', 'ERREUR', 'BONUS'].includes(typeValue)) return

    const wrapper = e.currentTarget
    const rect = wrapper.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    const normX = x / rect.width
    const normY = y / rect.height

    // Calculate size based on content for COMMENTAIRE from CommentBank
    let normW, normH
    if (typeValue === 'COMMENTAIRE' && contentValue) {
        // Estimate dimensions based on text length
        // Approximate: 7px per character width, 14px line height, max 200px width
        const charWidth = 7
        const lineHeight = 18
        const padding = 16
        const maxWidth = 250
        const minWidth = 80
        const minHeight = 30

        const textWidth = Math.min(maxWidth, Math.max(minWidth, contentValue.length * charWidth + padding))
        const numLines = Math.ceil((contentValue.length * charWidth) / (maxWidth - padding))
        const textHeight = Math.max(minHeight, numLines * lineHeight + padding)

        normW = textWidth / rect.width
        normH = textHeight / rect.height
    } else {
        // Default size for stamps and other annotations
        normW = 30 / pdfDimensions.value.width
        normH = 30 / pdfDimensions.value.height
    }

    // Safety bounds
    const safeX = Math.max(0, Math.min(1 - normW, normX))
    const safeY = Math.max(0, Math.min(1 - normH, normY))

    const normalizedRect = { x: safeX, y: safeY, w: normW, h: normH }

    if (typeValue === 'COMMENTAIRE' && contentValue) {
        // Direct creation from CommentBank
        isSaving.value = true
        try {
            await gradingApi.createAnnotation(copyId, {
                page_index: dropPageIndex,
                x: normalizedRect.x,
                y: normalizedRect.y,
                w: normalizedRect.w,
                h: normalizedRect.h,
                type: 'COMMENTAIRE',
                content: contentValue
            })
            await refreshAnnotations()
        } catch (err) {
            error.value = err.response?.data?.detail || "Échec de l'ajout depuis l'historique"
        } finally { isSaving.value = false; }
        return
    }

    // Handle stamp types directly
    if (['VRAI', 'FAUX', 'BONUS'].includes(typeValue)) {
        isSaving.value = true
        try {
            const contentMap = { 'VRAI': 'V', 'FAUX': 'X', 'BONUS': '' }
            const payload = {
                page_index: dropPageIndex,
                x: normalizedRect.x,
                y: normalizedRect.y,
                w: normalizedRect.w,
                h: normalizedRect.h,
                type: typeValue,
                content: contentMap[typeValue] ?? ''
            }
            await gradingApi.createAnnotation(copyId, payload)
            await refreshAnnotations()
        } catch (err) {
            error.value = err.response?.data?.detail || "Échec de la création de l'annotation"
        } finally { isSaving.value = false }
        return
    }

    // Text-based annotation types - open editor
    setAnnotationMode('type', typeValue)
    await handleDrawComplete(normalizedRect, null, dropPageIndex)
    annotationMode.value = { group: null, value: null }
}

// CommentBank tap-to-insert fallback (for touch devices where drag-and-drop is unavailable)
const handleCommentBankInsert = async (text) => {
    if (!canAnnotate.value) return
    isSaving.value = true
    try {
        // Place annotation at center of current page, reasonable default size
        const normW = 0.25
        const normH = 0.06
        await gradingApi.createAnnotation(copyId, {
            page_index: currentPage.value - 1,
            x: 0.05,
            y: 0.5 - normH / 2,
            w: normW,
            h: normH,
            type: 'COMMENTAIRE',
            content: text
        })
        await refreshAnnotations()
    } catch (err) {
        error.value = err.response?.data?.detail || "Échec de l'ajout depuis l'historique"
    } finally { isSaving.value = false }
}

// --- Annotation Editor ---
const handleDrawComplete = async (normalizedRect, overrideType = null, pageIndex = null) => {
    if (!canAnnotate.value) return;
    const effectivePageIndex = typeof pageIndex === 'number' ? pageIndex : currentPage.value - 1

    // Stamp mode (V, F): instant annotation, no editor needed
    const stampType = overrideType || quickStampMode.value
    if (stampType) {
        isSaving.value = true
        try {
            const contentMap = { 'VRAI': 'V', 'FAUX': 'X', 'BONUS': '' }
            const payload = {
                page_index: effectivePageIndex,
                x: normalizedRect.x,
                y: normalizedRect.y,
                w: normalizedRect.w,
                h: normalizedRect.h,
                type: stampType,
                content: contentMap[stampType] ?? ''
            }
            await gradingApi.createAnnotation(copyId, payload)
            await refreshAnnotations()
        } catch (err) {
            error.value = err.response?.data?.detail || "Échec de la création de l'annotation"
        } finally { isSaving.value = false }
        return
    }

    // Text mode: open editor for text input, store page_index in draft
    draftAnnotation.value = {
        rect: normalizedRect,
        type: preSelectedAnnotationType.value || 'COMMENTAIRE',
        content: '',
        page_index: effectivePageIndex
    }
    showEditor.value = true
    nextTick(() => { if (editorInputRef.value) editorInputRef.value.focus() })
}

const saveAnnotation = async () => {
    if (!draftAnnotation.value) return;
    isSaving.value = true;
    try {
        const payload = {
            page_index: draftAnnotation.value.page_index ?? (currentPage.value - 1),
            x: draftAnnotation.value.rect.x,
            y: draftAnnotation.value.rect.y,
            w: draftAnnotation.value.rect.w,
            h: draftAnnotation.value.rect.h,
            type: draftAnnotation.value.type,
            content: draftAnnotation.value.content
        }
        await gradingApi.createAnnotation(copyId, payload)

        // Clear Drafts on Success
        localStorage.removeItem(getStorageKey());
        try { await gradingApi.deleteDraft(copyId); } catch{}
        restoreAvailable.value = null;

        await refreshAnnotations()
        // fetchHistory() is omitted during individual creations to avoid UI saturation
        cancelEditor()
    } catch (err) {
        error.value = err.response?.data?.detail || "Échec de la création de l'annotation"
    } finally { isSaving.value = false; }
}

const cancelEditor = () => {
    showEditor.value = false
    draftAnnotation.value = null
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
const handleSuggestionInsert = ({ text, source, id }) => {
    if (showEditor.value && draftAnnotation.value) {
        const current = draftAnnotation.value.content || ''
        draftAnnotation.value.content = current ? current + '\n' + text : text
        nextTick(() => { if (editorInputRef.value) editorInputRef.value.focus() })
    } else if (activeRemarkQuestionId.value) {
        const qid = activeRemarkQuestionId.value
        const current = questionRemarks.value.get(qid) || ''
        const newVal = current ? current + '\n' + text : text
        questionRemarks.value.set(qid, newVal)
        onRemarkChange(qid, newVal)
    }
    if (source === 'manual' || source === 'template') {
        gradingApi.autoSaveAnnotation(text, suggestionsExercise.value, suggestionsQuestion.value).catch(() => {})
    }
}

const openSuggestionsForRemark = (questionId) => {
    const parts = questionId.split('.')
    suggestionsExercise.value = parts.length > 0 ? parseInt(parts[0]) || null : null
    suggestionsQuestion.value = parts.length > 1 ? parts.slice(1).join('.') : null
    activeRemarkQuestionId.value = questionId
    showSuggestions.value = true
}

// Auto-save remarks to personal annotation bank when they are substantial
const autoSaveRemarkToBank = (questionId, remark) => {
    if (!remark || remark.trim().length < 5) return
    const parts = questionId.split('.')
    const exercise = parts.length > 0 ? parseInt(parts[0]) || null : null
    const question = parts.length > 1 ? parts.slice(1).join('.') : null
    gradingApi.autoSaveAnnotation(remark.trim(), exercise, question).catch(() => {})
}

const closeSuggestions = () => {
    showSuggestions.value = false
    activeRemarkQuestionId.value = null
}

const handleDeleteAnnotation = async (id) => {
    if (!canAnnotate.value) return;
    if (!confirm("Supprimer cette annotation ?")) return;
    isSaving.value = true;
    try {
        await gradingApi.deleteAnnotation(copyId, id)
        await refreshAnnotations()
        await fetchHistory()
    } catch (err) {
        error.value = err.response?.data?.detail || "Échec de la suppression de l'annotation"
    } finally { isSaving.value = false; }
}

const handleAnnotationClick = (id) => {
    if (!canAnnotate.value || showEditor.value) return;
    handleDeleteAnnotation(id);
}

// --- Sync Protection: beforeunload + connectivity ---
const onBeforeUnload = (e) => {
    if (hasPendingChanges.value) {
        e.preventDefault()
        e.returnValue = 'Des modifications non sauvegardées sur le serveur seront perdues.'
        return e.returnValue
    }
}

const onOnline = () => {
    isOnline.value = true
    retryAllPending()
}
const onOffline = () => { isOnline.value = false }

const retryAllPending = async () => {
    if (pendingScoresChange.value) {
        await saveScoresToServer()
    }
    if (pendingAppreciationChange.value) {
        await saveGlobalAppreciationToServer()
    }
    for (const questionId of pendingRemarksChanges.value) {
        const remark = questionRemarks.value.get(questionId) || ''
        await saveRemark(questionId, remark)
    }
}

// --- Touch gesture handlers (pinch-to-zoom + swipe page navigation) ---
const touchState = { startX: 0, startY: 0, startDistance: 0, startScale: 1.0, isMultiTouch: false }

const onScrollAreaTouchStart = (e) => {
    if (e.touches.length === 2) {
        touchState.isMultiTouch = true
        const dx = e.touches[0].clientX - e.touches[1].clientX
        const dy = e.touches[0].clientY - e.touches[1].clientY
        touchState.startDistance = Math.hypot(dx, dy)
        touchState.startScale = scale.value
    } else if (e.touches.length === 1) {
        touchState.isMultiTouch = false
        touchState.startX = e.touches[0].clientX
        touchState.startY = e.touches[0].clientY
    }
}

const onScrollAreaTouchMove = (e) => {
    if (e.touches.length === 2) {
        e.preventDefault()
        const dx = e.touches[0].clientX - e.touches[1].clientX
        const dy = e.touches[0].clientY - e.touches[1].clientY
        const distance = Math.hypot(dx, dy)
        const ratio = distance / touchState.startDistance
        scale.value = Math.max(0.3, Math.min(3.0, +(touchState.startScale * ratio).toFixed(2)))
    }
}

const onScrollAreaTouchEnd = () => {
    // Continuous scroll handles page navigation natively — just reset multi-touch state
    touchState.isMultiTouch = false
}

onMounted(async () => {
  await fetchCopy()
  fetchSiblingCopies()  // non-blocking, runs in background
  if (isReady.value || isInProgress.value) checkDrafts()
  window.addEventListener('keydown', onGlobalKeydown)
  window.addEventListener('beforeunload', onBeforeUnload)
  window.addEventListener('online', onOnline)
  window.addEventListener('offline', onOffline)

    // Scroll-wheel zoom + continuous scroll tracking
    nextTick(() => {
        if (scrollAreaRef.value) {
            scrollAreaRef.value.addEventListener('wheel', onScrollAreaWheel, { passive: false })
            scrollAreaRef.value.addEventListener('scroll', updateCurrentPageFromScroll, { passive: true })
            scrollAreaRef.value.addEventListener('touchstart', onScrollAreaTouchStart, { passive: true })
            scrollAreaRef.value.addEventListener('touchmove', onScrollAreaTouchMove, { passive: false })
            scrollAreaRef.value.addEventListener('touchend', onScrollAreaTouchEnd, { passive: true })
        }
    })
})

// Watch route param changes for prev/next copy navigation
watch(() => route.params.copyId, async (newId, oldId) => {
    if (newId && newId !== oldId) {
        copyId = newId
        // Reset state for clean load
        copy.value = null
        annotations.value = []
        historyLogs.value = []
        questionRemarks.value = new Map()
        questionScores.value = new Map()
        globalAppreciation.value = ''
        error.value = null
        currentPage.value = 1
        lastSaveStatus.value = null
        restoreAvailable.value = null
        pendingScoresChange.value = false
        pendingRemarksChanges.value = new Set()
        pendingAppreciationChange.value = false
        syncErrors.value = []
        clientId.value = getSessionClientId()
        // Reload the new copy
        await fetchCopy()
        fetchSiblingCopies()
        if (isReady.value || isInProgress.value) checkDrafts()
    }
})

// Watch for Auth Hydration to load drafts
watch(() => authStore.user, (u) => {
    if (u?.id) checkDrafts();
}, { immediate: true })

onUnmounted(() => {
    window.removeEventListener('keydown', onGlobalKeydown)
    window.removeEventListener('beforeunload', onBeforeUnload)
    window.removeEventListener('online', onOnline)
    window.removeEventListener('offline', onOffline)
    if (scrollAreaRef.value) {
        scrollAreaRef.value.removeEventListener('wheel', onScrollAreaWheel)
        scrollAreaRef.value.removeEventListener('scroll', updateCurrentPageFromScroll)
        scrollAreaRef.value.removeEventListener('touchstart', onScrollAreaTouchStart)
        scrollAreaRef.value.removeEventListener('touchmove', onScrollAreaTouchMove)
        scrollAreaRef.value.removeEventListener('touchend', onScrollAreaTouchEnd)
    }
})
</script>

<template>
  <div class="corrector-desk">
    <div class="toolbar">
      <div class="left">
        <button
          class="back-btn"
          @click="router.push(isAdmin ? '/admin/dashboard' : '/corrector-dashboard')"
        >
          <AppIcon
            name="arrow-left"
            :size="14"
            class="inline"
          /> Retour
        </button>
        <div
          v-if="siblingCopies.length > 1"
          class="copy-nav"
        >
          <button
            class="nav-arrow"
            :disabled="!prevCopy"
            :title="prevCopy ? `Copie précédente : ${prevCopy.anonymous_id}` : 'Première copie'"
            @click="navigateToCopy(prevCopy)"
          >
            <AppIcon
              name="chevron-left"
              :size="14"
            />
          </button>
          <span class="nav-position">{{ copyPositionLabel }}</span>
          <button
            class="nav-arrow"
            :disabled="!nextCopy"
            :title="nextCopy ? `Copie suivante : ${nextCopy.anonymous_id}` : 'Dernière copie'"
            @click="navigateToCopy(nextCopy)"
          >
            <AppIcon
              name="chevron-right"
              :size="14"
            />
          </button>
        </div>
        <span
          v-if="copy"
          class="copy-info"
        >
          <strong>{{ copy.anonymous_id }}</strong>
          <span :class="'status-badge status-' + copy.status.toLowerCase()">{{ getStatusLabel(copy.status) }}</span>
          <span
            class="sync-indicator"
            :class="'sync-' + syncStatusLevel"
            :title="syncStatusLevel === 'ok' ? 'Synchronisé' : syncStatusLevel === 'offline' ? 'Hors ligne' : syncStatusLevel === 'critical' ? 'Erreur de sync' : 'En attente...'"
          >
            <span class="sync-dot" />
          </span>
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
          Marquer Prêt
        </button>

        <button
          v-if="isReady"
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
          Télécharger
        </button>

        <button
          v-if="isAdmin"
          :disabled="isSaving"
          class="btn-warning"
          @click="handleForceUnlock"
        >
          Déverrouiller
        </button>

        <button
          v-if="isAdmin && isGraded"
          :disabled="isSaving"
          class="btn-orange"
          @click="handleReopenCopy"
        >
          Rouvrir
        </button>
      </div>
    </div>

    <div
      v-if="gradingProgress.total > 0"
      class="grading-progress-strip"
    >
      <div class="grading-progress-copy">
        <strong>{{ gradingProgress.scored }}/{{ gradingProgress.total }}</strong> questions notées ({{ gradingProgress.percent }}%)
      </div>
      <div class="grading-progress-bar">
        <div
          class="grading-progress-fill"
          :style="{ width: gradingProgress.percent + '%' }"
        />
      </div>
      <div
        v-if="hasIncompleteScores"
        class="grading-progress-remaining"
      >
        {{ gradingProgress.remaining }} question{{ gradingProgress.remaining > 1 ? 's' : '' }} restante{{ gradingProgress.remaining > 1 ? 's' : '' }}
      </div>
      <div
        v-else
        class="grading-progress-complete"
      >
        Barème complet
      </div>
    </div>

    <div
      v-if="error"
      class="error-banner"
    >
      <span>{{ error }}</span>
      <button @click="error = null">
        Fermer
      </button>
    </div>

    <!-- Sync Status Banner -->
    <div
      v-if="syncStatusLevel === 'offline'"
      class="sync-banner sync-offline"
    >
      <span><AppIcon
        name="warning"
        :size="14"
        class="inline"
      /> Hors ligne — Les modifications sont sauvegardées localement mais ne peuvent pas être envoyées au serveur.</span>
    </div>
    <div
      v-else-if="syncStatusLevel === 'critical'"
      class="sync-banner sync-critical"
    >
      <span><AppIcon
        name="alert"
        :size="14"
        class="inline"
      /> {{ syncErrors.length }} erreur(s) de synchronisation — Vos notes ne sont PAS sauvegardées sur le serveur !</span>
      <button
        class="btn-sm btn-retry"
        @click="retryAllPending"
      >
        Réessayer maintenant
      </button>
    </div>
    <div
      v-else-if="syncStatusLevel === 'warning' && hasPendingChanges"
      class="sync-banner sync-warning"
    >
      <span><AppIcon
        name="info"
        :size="14"
        class="inline"
      /> Synchronisation en cours…</span>
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
      Chargement...
    </div>
    <div
      v-else
      class="workspace"
    >
      <!-- Panneau des commentaires mémorisés (à gauche, hors du sidebar barème) -->
      <CommentBank
        :visible="showCommentBank"
        @close="showCommentBank = false"
        @insert="handleCommentBankInsert"
      />

      <!-- Viewer -->
      <div class="viewer-container">
        <div class="viewer-toolbar">
          <div
            v-if="hasPages"
            class="pagination"
          >
            <button
              :disabled="currentPage <= 1"
              title="Page précédente (← ou PageUp)"
              @click="goPrevPage"
            >
              <AppIcon
                name="chevron-left"
                :size="12"
                class="inline"
              /> Préc.
            </button>
            <span>Page {{ currentPage }} / {{ pages.length }}</span>
            <button
              :disabled="currentPage >= pages.length"
              title="Page suivante (→ ou PageDown)"
              @click="goNextPage"
            >
              Suiv. <AppIcon
                name="chevron-right"
                :size="12"
                class="inline"
              />
            </button>
          </div>
          <div
            v-else
            class="pagination"
          >
            <span>Aucune page</span>
          </div>
          <!-- Quick Stamp Buttons V/X -->
          <div
            v-if="canAnnotate"
            class="quick-stamp-controls"
          >
            <button
              :class="['btn-stamp', 'btn-stamp-vrai', { active: quickStampMode === 'VRAI' }]"
              title="Tampon Vrai (Glisser-Déposer ou Clic)"
              :draggable="!isTouch"
              @dragstart="handleDragStart('VRAI', $event)"
              @click="setAnnotationMode('stamp', 'VRAI')"
            >
              <AppIcon
                name="check-mark"
                :size="14"
                class="inline"
              /> V
            </button>
            <button
              :class="['btn-stamp', 'btn-stamp-faux', { active: quickStampMode === 'FAUX' }]"
              title="Tampon Faux (Glisser-Déposer ou Clic)"
              :draggable="!isTouch"
              @dragstart="handleDragStart('FAUX', $event)"
              @click="setAnnotationMode('stamp', 'FAUX')"
            >
              <AppIcon
                name="x-mark"
                :size="14"
                class="inline"
              /> F
            </button>
          </div>
          <!-- Annotation Type Quick Selectors -->
          <div
            v-if="canAnnotate"
            class="annotation-type-controls"
          >
            <button
              :class="['btn-annot-type', { active: preSelectedAnnotationType === 'COMMENTAIRE' }]"
              title="Commentaire (Glisser-Déposer)"
              :draggable="!isTouch"
              @dragstart="handleDragStart('COMMENTAIRE', $event)"
              @click="setAnnotationMode('type', 'COMMENTAIRE')"
            >
              <AppIcon
                name="comment"
                :size="16"
              />
            </button>
            <button
              :class="['btn-annot-type', { active: preSelectedAnnotationType === 'SURLIGNAGE' }]"
              title="Surlignage (Glisser-Déposer)"
              :draggable="!isTouch"
              @dragstart="handleDragStart('SURLIGNAGE', $event)"
              @click="setAnnotationMode('type', 'SURLIGNAGE')"
            >
              <AppIcon
                name="highlight"
                :size="16"
              />
            </button>
            <button
              :class="['btn-annot-type', { active: preSelectedAnnotationType === 'ERREUR' }]"
              title="Erreur (Glisser-Déposer)"
              :draggable="!isTouch"
              @dragstart="handleDragStart('ERREUR', $event)"
              @click="setAnnotationMode('type', 'ERREUR')"
            >
              <AppIcon
                name="error-mark"
                :size="16"
              />
            </button>
            <button
              :class="['btn-annot-type', 'btn-comment-bank', { active: showCommentBank }]"
              title="Mes commentaires mémorisés"
              @click="showCommentBank = !showCommentBank"
            >
              <AppIcon
                name="star"
                :size="16"
              />
            </button>
          </div>
          <div class="zoom-controls">
            <button @click="scale = Math.max(0.3, +(scale - 0.1).toFixed(1))">
              -
            </button>
            <button
              class="zoom-reset"
              title="Réinitialiser zoom"
              @click="scale = 1.0"
            >
              {{ Math.round(scale * 100) }}%
            </button>
            <button @click="scale = Math.min(3.0, +(scale + 0.1).toFixed(1))">
              +
            </button>
            <button
              title="Ajuster à la largeur"
              class="btn-fit"
              @click="fitToWidth"
            >
              <AppIcon
                name="fit-width"
                :size="14"
              />
            </button>
          </div>
        </div>
        <div
          ref="scrollAreaRef"
          class="scroll-area"
        >
          <!-- Continuous scroll: all pages stacked vertically -->
          <template v-if="hasPages">
            <div
              v-for="(page, idx) in pages"
              :key="idx"
              :ref="(el) => setPageRef(el, idx)"
              :data-page-index="idx"
              class="canvas-wrapper"
              :style="{ width: displayWidth + 'px', height: displayHeight + 'px' }"
              @dragover.prevent
              @dragenter="handleDragEnter"
              @dragleave="handleDragLeave"
              @drop="(e) => handleDrop(e, idx)"
            >
              <!-- Anonymization overlay per page (only after image loaded to prevent 0x0 flash) -->
              <div
                v-if="loadedPages.has(idx)"
                v-show="isHeaderPageForIndex(idx) && !showIdentity"
                class="anonymization-overlay"
                :style="{ height: overlayHeightForIndex(idx) }"
              >
                <div class="anonymization-label">
                  <AppIcon
                    name="lock"
                    :size="14"
                    class="inline"
                  /> Zone d'identification masquée
                </div>
                <button
                  v-if="isAdmin"
                  class="btn-sm btn-reveal"
                  @click="showIdentity = true"
                >
                  Révéler l'identité (Admin)
                </button>
              </div>
              <img
                :src="getPageUrl(idx)"
                :class="['page-image', { 'page-image--loading': !loadedPages.has(idx) }]"
                draggable="false"
                loading="lazy"
                style="pointer-events: none; user-select: none;"
                @load="(e) => handleImageLoad(e, idx)"
                @error="handleImageError"
                @contextmenu.prevent
              >
              <CanvasLayer
                v-if="loadedPages.has(idx)"
                :width="displayWidth"
                :height="displayHeight"
                :scale="scale"
                :initial-annotations="getAnnotationsForPage(idx)"
                :enabled="canAnnotate && !showEditor"
                @annotation-created="(rect) => handleDrawComplete(rect, null, idx)"
                @annotation-clicked="handleAnnotationClick"
              />
            </div>
          </template>
          <div
            v-else-if="imageError"
            class="empty-state error-state"
          >
            <p>
              <AppIcon
                name="warning"
                :size="14"
                class="inline"
              /> Erreur de chargement de l'image.
            </p>
            <button @click="fetchCopy">
              Réessayer
            </button>
          </div>
          <div
            v-else
            class="empty-state"
          >
            <p>Aucune page disponible.</p>
          </div>
        </div>
      </div>

      <!-- Annotation Editor Overlay (floats above copy when editing) -->
      <div
        v-if="showEditor"
        class="annotation-editor-overlay"
        data-testid="editor-panel"
      >
        <h4>Nouvelle annotation</h4>
        <div class="form-group">
          <label>Type</label>
          <select v-model="draftAnnotation.type">
            <option value="COMMENTAIRE">
              Commentaire
            </option>
            <option value="SURLIGNAGE">
              Surlignage
            </option>
            <option value="ERREUR">
              Erreur
            </option>
            <option value="BONUS">
              Bonus
            </option>
            <option value="VRAI">
              ✓ Vrai
            </option>
            <option value="FAUX">
              ✗ Faux
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>Contenu</label>
          <textarea
            ref="editorInputRef"
            v-model="draftAnnotation.content"
            placeholder="Saisir le texte de l'annotation..."
            autocorrect="off"
            autocapitalize="none"
            spellcheck="false"
            @keydown.ctrl.enter="saveAnnotation"
          />
        </div>
        <div class="editor-actions">
          <button
            v-if="examId"
            class="btn-sm btn-suggestions"
            title="Suggestions"
            @click="showSuggestions = !showSuggestions"
          >
            <AppIcon
              name="lightbulb"
              :size="14"
            />
          </button>
          <button
            class="btn-sm btn-secondary"
            @click="cancelEditor"
          >
            Annuler
          </button>
          <button
            class="btn-sm btn-primary"
            @click="saveAnnotation"
          >
            Enregistrer
          </button>
        </div>
        <AnnotationSuggestionsPanel
          v-if="examId"
          :exam-id="examId"
          :exercise-number="suggestionsExercise"
          :question-number="suggestionsQuestion"
          :visible="showSuggestions"
          @insert="handleSuggestionInsert"
          @close="closeSuggestions"
        />
      </div>

      <!-- Sidebar: Barème (always visible) -->
      <div class="inspector-panel">
        <div class="inspector-header">
          <strong>Barème</strong>
          <span
            class="inspector-total"
            :class="{ 'score-overflow': scoreExceeds20 }"
          >{{ totalScore.toFixed(2) }} / 20</span>
          <span
            v-if="scoresSaving"
            class="save-indicator small"
          >...</span>
        </div>

        <div class="grading-panel">
          <div
            v-if="exercisesWithQuestions.length === 0"
            class="empty-list"
          >
            Aucun barème disponible.
          </div>
          <div
            v-else
            class="grading-content"
          >
            <div class="exercises-list">
              <div
                v-for="(exercise, exerciseIndex) in exercisesWithQuestions"
                :key="exercise.id"
                class="exercise-block"
              >
                <!-- Level 1: Exercise header (collapsible) -->
                <div
                  class="exercise-header"
                  :class="{ collapsed: !openExerciseIds.has(exercise.id) }"
                  :style="{ borderLeft: '3px solid ' + getExerciseColor(exerciseIndex).bar }"
                  @click="toggleExercise(exercise.id)"
                >
                  <span class="exercise-toggle"><AppIcon
                    :name="openExerciseIds.has(exercise.id) ? 'chevron-down' : 'chevron-right'"
                    :size="12"
                  /></span>
                  <span class="exercise-label">{{ exercise.label }}</span>
                  <span
                    class="exercise-points"
                    :style="{ background: getExerciseColor(exerciseIndex).bg, color: getExerciseColor(exerciseIndex).text }"
                  >
                    {{ exercise.points }} pts
                  </span>
                </div>

                <div
                  v-show="openExerciseIds.has(exercise.id)"
                  class="exercise-body"
                >
                  <!-- Level 2a: Sub-exercise groups (Exercice 2, 3, …) -->
                  <template v-if="exercise.groups.length > 0">
                    <div
                      v-for="group in exercise.groups"
                      :key="group.id"
                      class="group-block"
                    >
                      <div
                        class="group-header"
                        :class="{ collapsed: !openGroupIds.has(group.id) }"
                        @click="toggleGroup(group.id)"
                      >
                        <span class="group-toggle"><AppIcon
                          :name="openGroupIds.has(group.id) ? 'chevron-down' : 'chevron-right'"
                          :size="12"
                        /></span>
                        <span class="group-label">{{ group.label }}</span>
                        <span class="group-points">{{ group.points }} pts</span>
                      </div>
                      <div
                        v-show="openGroupIds.has(group.id)"
                        class="group-questions"
                      >
                        <div
                          v-for="question in group.questions"
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
                              type="text"
                              inputmode="decimal"
                              pattern="[0-9]*[.,]?[0-9]*"
                              autocomplete="off"
                              :value="questionScoreTexts.get(question.id) ?? questionScores.get(question.id) ?? ''"
                              :disabled="isReadOnly"
                              :placeholder="isReadOnly ? '-' : '0'"
                              class="score-input"
                              :class="{
                                'score-filled': questionScores.get(question.id) != null && questionScores.get(question.id) !== '',
                                'score-missing': questionScores.get(question.id) == null || questionScores.get(question.id) === ''
                              }"
                              @wheel.prevent
                              @input="onScoreChange(question.id, $event.target.value)"
                              @blur="onScoreBlur(question.id)"
                            >
                            <div
                              v-if="!isReadOnly"
                              class="score-slider-row"
                            >
                              <button
                                class="score-step-btn"
                                type="button"
                                @click.stop="stepScore(question.id, question.maxScore, -0.25)"
                              >
                                −
                              </button>
                              <input
                                type="range"
                                class="score-slider"
                                min="0"
                                :max="question.maxScore * 4"
                                step="1"
                                :value="(questionScores.get(question.id) || 0) * 4"
                                @input="onScoreChange(question.id, String(parseInt($event.target.value) / 4))"
                              >
                              <button
                                class="score-step-btn"
                                type="button"
                                @click.stop="stepScore(question.id, question.maxScore, 0.25)"
                              >
                                +
                              </button>
                            </div>
                            <div
                              v-if="!isReadOnly"
                              class="quick-btns"
                            >
                              <button
                                v-for="v in quickVals(question.maxScore)"
                                :key="v"
                                class="qb"
                                @click="onScoreChange(question.id, String(v))"
                              >
                                {{ v }}
                              </button>
                            </div>
                          </div>
                          <div class="question-remark-field">
                            <div class="remark-label-row">
                              <label :for="'remark-' + question.id">Remarque</label>
                              <button
                                v-if="examId && !isReadOnly"
                                class="btn-suggestion-trigger"
                                title="Suggestions"
                                @click="openSuggestionsForRemark(question.id)"
                              >
                                <AppIcon
                                  name="lightbulb"
                                  :size="14"
                                />
                              </button>
                            </div>
                            <textarea
                              :id="'remark-' + question.id"
                              :value="questionRemarks.get(question.id) || ''"
                              :disabled="isReadOnly"
                              :placeholder="isReadOnly ? 'Lecture seule' : 'Remarque...'"
                              rows="2"
                              autocorrect="off"
                              autocapitalize="none"
                              spellcheck="false"
                              @focus="activeRemarkQuestionId = question.id"
                              @input="onRemarkChange(question.id, $event.target.value)"
                            />
                            <AnnotationSuggestionsPanel
                              v-if="examId && activeRemarkQuestionId === question.id && showSuggestions"
                              :exam-id="examId"
                              :exercise-number="suggestionsExercise"
                              :question-number="suggestionsQuestion"
                              :visible="true"
                              @insert="handleSuggestionInsert"
                              @close="closeSuggestions"
                            />
                            <span
                              v-if="remarksSaving.get(question.id)"
                              class="save-indicator small"
                            >Enregistrement...</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </template>

                  <!-- Level 2b: Direct questions (no sub-groups) -->
                  <template v-else>
                    <div
                      v-for="question in exercise.questions"
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
                          type="text"
                          inputmode="decimal"
                          pattern="[0-9]*[.,]?[0-9]*"
                          autocomplete="off"
                          :value="questionScoreTexts.get(question.id) ?? questionScores.get(question.id) ?? ''"
                          :disabled="isReadOnly"
                          :placeholder="isReadOnly ? '-' : '0'"
                          class="score-input"
                          :class="{
                            'score-filled': questionScores.get(question.id) != null && questionScores.get(question.id) !== '',
                            'score-missing': questionScores.get(question.id) == null || questionScores.get(question.id) === ''
                          }"
                          @wheel.prevent
                          @input="onScoreChange(question.id, $event.target.value)"
                          @blur="onScoreBlur(question.id)"
                        >
                        <div
                          v-if="!isReadOnly"
                          class="score-slider-row"
                        >
                          <button
                            class="score-step-btn"
                            type="button"
                            @click.stop="stepScore(question.id, question.maxScore, -0.25)"
                          >
                            −
                          </button>
                          <input
                            type="range"
                            class="score-slider"
                            min="0"
                            :max="question.maxScore * 4"
                            step="1"
                            :value="(questionScores.get(question.id) || 0) * 4"
                            @input="onScoreChange(question.id, String(parseInt($event.target.value) / 4))"
                          >
                          <button
                            class="score-step-btn"
                            type="button"
                            @click.stop="stepScore(question.id, question.maxScore, 0.25)"
                          >
                            +
                          </button>
                        </div>
                        <div
                          v-if="!isReadOnly"
                          class="quick-btns"
                        >
                          <button
                            v-for="v in quickVals(question.maxScore)"
                            :key="v"
                            class="qb"
                            @click="onScoreChange(question.id, String(v))"
                          >
                            {{ v }}
                          </button>
                        </div>
                      </div>
                      <div class="question-remark-field">
                        <div class="remark-label-row">
                          <label :for="'remark-' + question.id">Remarque</label>
                          <button
                            v-if="examId && !isReadOnly"
                            class="btn-suggestion-trigger"
                            title="Suggestions"
                            @click="openSuggestionsForRemark(question.id)"
                          >
                            <AppIcon
                              name="lightbulb"
                              :size="14"
                            />
                          </button>
                        </div>
                        <textarea
                          :id="'remark-' + question.id"
                          :value="questionRemarks.get(question.id) || ''"
                          :disabled="isReadOnly"
                          :placeholder="isReadOnly ? 'Lecture seule' : 'Remarque...'"
                          rows="2"
                          @focus="activeRemarkQuestionId = question.id"
                          @input="onRemarkChange(question.id, $event.target.value)"
                        />
                        <AnnotationSuggestionsPanel
                          v-if="examId && activeRemarkQuestionId === question.id && showSuggestions"
                          :exam-id="examId"
                          :exercise-number="suggestionsExercise"
                          :question-number="suggestionsQuestion"
                          :visible="true"
                          @insert="handleSuggestionInsert"
                          @close="closeSuggestions"
                        />
                        <span
                          v-if="remarksSaving.get(question.id)"
                          class="save-indicator small"
                        >Enregistrement...</span>
                      </div>
                    </div>
                  </template>
                </div>
              </div>
              <!-- Total -->
              <div
                class="total-score-bar"
                :class="{ 'score-overflow': scoreExceeds20 }"
              >
                <span class="total-label">Note totale :</span>
                <strong>{{ totalScore.toFixed(2) }}</strong> / 20
                <span
                  v-if="scoreExceeds20"
                  class="overflow-warning"
                ><AppIcon
                  name="warning"
                  :size="12"
                  class="inline"
                /> Dépasse 20 !</span>
              </div>
              <!-- Per-exercise score breakdown -->
              <div
                v-if="exercisesWithQuestions.length > 0"
                class="exercise-scores-breakdown"
              >
                <div
                  v-for="(exercise, exIdx) in exercisesWithQuestions"
                  :key="'score-' + exercise.id"
                  class="exercise-score-row"
                >
                  <span class="exercise-score-label">{{ exercise.label }}</span>
                  <div class="exercise-score-right">
                    <div class="exercise-mini-bar">
                      <div
                        class="exercise-mini-fill"
                        :style="{ width: exercise.points > 0 ? Math.min(100, ((exerciseScoreBreakdown[exercise.id]?.obtained || 0) / exercise.points) * 100) + '%' : '0%', background: getExerciseColor(exIdx).bar }"
                      />
                    </div>
                    <span class="exercise-score-value">{{ exerciseScoreBreakdown[exercise.id]?.obtained ?? '-' }} / {{ exercise.points }}</span>
                  </div>
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
                {{ lastScoresSaveStatus.success ? 'Notes sauvegardées' : 'Erreur sauvegarde' }}
              </div>
            </div>
            <!-- Appréciation -->
            <div class="global-appreciation-section">
              <label for="global-appreciation">Appréciation globale</label>
              <textarea
                id="global-appreciation"
                v-model="globalAppreciation"
                :disabled="isReadOnly"
                :placeholder="isReadOnly ? 'Lecture seule' : 'Appréciation globale...'"
                rows="4"
                autocorrect="off"
                autocapitalize="none"
                spellcheck="false"
                @input="onAppreciationChange($event.target.value)"
              />
              <span
                v-if="appreciationSaving"
                class="save-indicator small"
              >Enregistrement...</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.corrector-desk { display: flex; flex-direction: column; height: 100vh; height: 100dvh; background: #e9ecef; }
.toolbar { padding: 10px 20px; background: #343a40; color: white; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.copy-info { margin-left: 15px; font-size: 1.1rem; }
.copy-nav { display: flex; align-items: center; gap: 6px; margin-left: 12px; }
.nav-arrow { background: rgba(255,255,255,0.15); color: white; border: 1px solid rgba(255,255,255,0.25); border-radius: 4px; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 0.85rem; transition: background 0.15s; }
.nav-arrow:hover:not(:disabled) { background: rgba(255,255,255,0.3); }
.nav-arrow:disabled { opacity: 0.3; cursor: not-allowed; }
.nav-position { font-size: 0.85rem; color: #adb5bd; min-width: 40px; text-align: center; }
.status-badge { padding: 2px 8px; border-radius: 4px; font-size: 0.8rem; margin-left: 5px; text-transform: uppercase; font-weight: bold; }
.status-ready { background: #28a745; color: white; }
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
.btn-orange { background: #f97316; color: white; border: none; }
.btn-secondary { background: #6c757d; color: white; border: none; }
.btn-sm { padding: 2px 6px; font-size: 0.85rem; }

.workspace { display: flex; flex: 1; overflow: hidden; }
.viewer-container { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.viewer-toolbar { padding: 8px 12px; background: white; border-bottom: 1px solid #dee2e6; display: flex; justify-content: center; gap: 12px; align-items: center; flex-wrap: wrap; }
.zoom-controls { display: flex; align-items: center; gap: 4px; }
.zoom-controls button { padding: 4px 8px; border: 1px solid #ced4da; border-radius: 4px; background: #f8f9fa; cursor: pointer; font-weight: 600; font-size: 0.85rem; }
.zoom-controls button:hover { background: #e9ecef; }
.zoom-reset { min-width: 52px; text-align: center; }
.btn-fit { font-size: 1rem; }
.scroll-area { flex: 1; overflow: auto; background: #525659; display: flex; flex-direction: column; align-items: center; gap: 16px; padding: 20px; -webkit-overflow-scrolling: touch; will-change: scroll-position; }

.canvas-wrapper { position: relative; background: white; box-shadow: 0 0 15px rgba(0,0,0,0.3); will-change: transform; flex-shrink: 0; }
.page-image { width: 100%; height: 100%; display: block; opacity: 1; transition: opacity 0.15s ease-in; image-rendering: auto; }
.page-image--loading { opacity: 0; }

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
.btn-reveal {
    background: rgba(255,255,255,0.15);
    color: #EEEDFE;
    border: 1px solid rgba(175,169,236,0.55);
    padding: 4px 12px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8rem;
    transition: background 0.2s;
}
.btn-reveal:hover { background: rgba(255,255,255,0.25); }

.inspector-panel { width: 340px; background: white; border-left: 1px solid #e2e8f0; display: flex; flex-direction: column; }
.inspector-header { display: flex; align-items: center; gap: 10px; padding: 14px 16px; background: #fff; border-bottom: 1px solid #e2e8f0; }
.inspector-header strong { font-size: 0.85rem; color: #94a3b8; font-weight: 500; text-transform: uppercase; letter-spacing: 0.3px; }
.inspector-total { margin-left: auto; font-weight: 500; font-size: 1.25rem; color: #1e293b; padding: 0; background: none; border: none; border-radius: 0; }
.inspector-total.score-overflow { color: #E24B4A; background: none; border: none; }

/* Annotation editor overlay (floats above copy area) */
.annotation-editor-overlay { 
  position: fixed; 
  top: 120px; 
  left: 50%; 
  transform: translateX(-50%); 
  z-index: 100; 
  width: 380px; 
  max-width: calc(100vw - 40px); 
  max-height: calc(100svh - 80px);
  overflow-y: auto;
  background: #EEEDFE; 
  border: 2px solid #AFA9EC; 
  border-radius: 10px; 
  box-shadow: 0 8px 30px rgba(0,0,0,0.2); 
  padding: 16px; 
}

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
.grading-progress-strip { display: flex; align-items: center; gap: 12px; padding: 10px 20px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; font-size: 0.9rem; }
.grading-progress-copy { min-width: 180px; color: #64748b; }
.grading-progress-bar { flex: 1; height: 6px; background: #e2e8f0; border-radius: 3px; overflow: hidden; }
.grading-progress-fill { height: 100%; border-radius: 3px; background: #5DCAA5; transition: width 0.3s ease; }
.grading-progress-remaining { color: #94a3b8; font-weight: 500; white-space: nowrap; }
.grading-progress-complete { color: #0F6E56; font-weight: 500; white-space: nowrap; }
.sync-banner { padding: 10px 20px; text-align: center; font-weight: 600; font-size: 0.9rem; display: flex; justify-content: center; align-items: center; gap: 12px; animation: syncPulse 2s ease-in-out infinite; }
.sync-offline { background: #fef3c7; color: #92400e; border-bottom: 2px solid #f59e0b; }
.sync-critical { background: #fecaca; color: #991b1b; border-bottom: 2px solid #dc2626; animation: syncPulse 1s ease-in-out infinite; }
.sync-warning { background: #dbeafe; color: #1e40af; border-bottom: 1px solid #93c5fd; }
.btn-retry { background: #dc2626; color: white; border: none; padding: 4px 12px; border-radius: 4px; cursor: pointer; font-weight: 600; }
.btn-retry:hover { background: #b91c1c; }
@keyframes syncPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.85; } }
.loading-state { flex: 1; display: flex; justify-content: center; align-items: center; font-size: 1.5rem; color: #666; }
.empty-list, .empty-state { padding: 20px; text-align: center; color: #999; }
.error-state p { color: #dc3545; font-weight: bold; }

.grading-panel { flex: 1; overflow-y: auto; }
.grading-content { padding: 15px; }
.exercises-list { margin-bottom: 20px; }
.exercise-block { margin-bottom: 8px; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
.exercise-header { display: flex; align-items: center; gap: 8px; padding: 10px 12px; background: #fff; cursor: pointer; user-select: none; transition: background 0.15s; border-radius: 0; }
.exercise-header:hover { background: #f8fafc; }
.exercise-header.collapsed { border-bottom: none; }
.exercise-toggle { font-size: 0.7rem; color: #64748b; width: 14px; }
.exercise-label { flex: 1; font-weight: 600; font-size: 0.95rem; color: #1e293b; }
.exercise-points { font-size: 0.8rem; font-weight: 500; padding: 3px 10px; border-radius: 12px; }
.exercise-body { padding: 4px 0 4px; }
.group-block { margin: 4px 8px; border: 1px solid #e9edf2; border-radius: 6px; overflow: hidden; }
.group-header { display: flex; align-items: center; gap: 8px; padding: 7px 10px; background: #f8fafc; cursor: pointer; user-select: none; transition: background 0.15s; }
.group-header:hover { background: #edf2f7; }
.group-header.collapsed { border-bottom: none; }
.group-toggle { font-size: 0.65rem; color: #64748b; width: 12px; }
.group-label { flex: 1; font-size: 0.82rem; font-weight: 600; color: #4a5568; }
.group-points { font-size: 0.78rem; font-weight: 600; color: #6366f1; background: #eef2ff; padding: 1px 6px; border-radius: 4px; }
.group-questions { padding: 2px 6px 6px; }
.question-item { margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 6px; border: 1px solid #dee2e6; }
.question-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.question-title { font-weight: bold; font-size: 0.95rem; color: #333; }
.question-max-score { font-size: 0.85rem; color: #666; background: #e9ecef; padding: 2px 8px; border-radius: 4px; }
.question-score-field { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; flex-wrap: wrap; }
.question-score-field label { font-size: 0.85rem; color: #333; font-weight: 600; min-width: 40px; }
.score-input { width: 65px; min-height: 36px; padding: 4px 6px; border: 1.5px solid #e2e8f0; border-radius: 6px; font-size: 0.95rem; font-weight: 500; text-align: center; transition: border-color 0.2s, background 0.2s; }
.score-input:focus { outline: none; border-color: #7F77DD; box-shadow: 0 0 0 3px rgba(127,119,221,0.1); }
.score-input.score-filled { border-color: #5DCAA5; background: #f0fdf9; }
.score-input.score-missing { border-color: #e2e8f0; background: #fff; }
.score-input:disabled { background: #f1f5f9; cursor: not-allowed; border-color: #e2e8f0; }
.score-slider-row { display: flex; align-items: center; gap: 6px; width: 100%; margin-top: 4px; }
.score-slider { flex: 1; height: 6px; -webkit-appearance: none; appearance: none; background: #e2e8f0; border-radius: 3px; outline: none; cursor: pointer; }
.score-slider::-webkit-slider-thumb { -webkit-appearance: none; appearance: none; width: 18px; height: 18px; border-radius: 50%; background: #7F77DD; border: 2px solid #fff; cursor: pointer; box-shadow: 0 0 0 1px #e2e8f0; }
.score-slider::-moz-range-thumb { width: 18px; height: 18px; border-radius: 50%; background: #7F77DD; border: 2px solid #fff; cursor: pointer; }
.score-step-btn { width: 26px; height: 26px; border-radius: 50%; border: 1px solid #e2e8f0; background: #fff; color: #64748b; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: all 0.15s; line-height: 1; }
.score-step-btn:hover { background: #f1f5f9; border-color: #cbd5e1; }
.score-step-btn:active { transform: scale(0.95); }
.question-remark-field { display: flex; flex-direction: column; }
.question-remark-field label { font-size: 0.85rem; color: #666; margin-bottom: 5px; }
.question-remark-field textarea { padding: 8px; border: 1px solid #ced4da; border-radius: 4px; font-size: 0.9rem; font-family: inherit; resize: vertical; }
.question-remark-field textarea:focus { outline: none; border-color: #007bff; box-shadow: 0 0 0 0.2rem rgba(0,123,255,0.25); }
.question-remark-field textarea:disabled { background: #e9ecef; cursor: not-allowed; }
.save-indicator.small { font-size: 0.75rem; color: #28a745; margin-top: 3px; font-style: italic; }
.total-score-bar { display: flex; align-items: center; gap: 6px; padding: 12px 14px; margin-top: 12px; border-radius: 8px; font-size: 0.95rem; background: #f8fafc; color: #334155; border: 1px solid #e2e8f0; }
.total-score-bar strong { font-size: 1.1rem; }
.total-score-bar.score-overflow { background: #fef2f2; color: #991b1b; border-color: #fecaca; }
.total-label { font-weight: 500; }
.overflow-warning { font-size: 0.85rem; font-weight: 400; margin-left: auto; }
.scores-save-status { text-align: center; padding: 6px; font-size: 0.8rem; font-style: italic; margin-top: 8px; }
.scores-save-status.save-ok { color: #28a745; }
.scores-save-status.save-err { color: #dc3545; }
.btn-disabled { opacity: 0.5; cursor: not-allowed; }

/* Exercise score breakdown */
.exercise-scores-breakdown { margin-top: 8px; padding: 10px 14px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; }
.exercise-score-row { display: flex; justify-content: space-between; align-items: center; padding: 4px 0; }
.exercise-score-label { font-size: 0.8rem; color: #64748b; }
.exercise-score-right { display: flex; align-items: center; gap: 8px; }
.exercise-mini-bar { width: 60px; height: 4px; background: #e2e8f0; border-radius: 2px; overflow: hidden; }
.exercise-mini-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }
.exercise-score-value { font-size: 0.8rem; color: #94a3b8; min-width: 45px; text-align: right; }

.global-appreciation-section { padding: 16px; background: #fff; border-top: 1px solid #e2e8f0; }
.global-appreciation-section label { font-weight: 500; font-size: 0.85rem; color: #64748b; margin-bottom: 8px; display: block; text-transform: uppercase; letter-spacing: 0.3px; }
.global-appreciation-section textarea { width: 100%; padding: 10px 12px; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 0.9rem; font-family: inherit; resize: vertical; background: #f8fafc; transition: border-color 0.2s, background 0.2s; }
.global-appreciation-section textarea:focus { outline: none; border-color: #7F77DD; box-shadow: 0 0 0 3px rgba(127,119,221,0.1); background: #fff; }
.global-appreciation-section textarea:disabled { background: #f1f5f9; cursor: not-allowed; }


/* Suggestions */
.btn-suggestions { background: #fff; border: 1px solid #AFA9EC; border-radius: 4px; cursor: pointer; font-size: 14px; padding: 4px 8px; transition: background 0.15s, border-color 0.15s; color: #534AB7; }
.btn-suggestions:hover { background: #EEEDFE; }
.btn-suggestion-trigger { background: none; border: none; cursor: pointer; font-size: 14px; padding: 0 2px; opacity: 0.6; transition: opacity 0.15s; }
.btn-suggestion-trigger:hover { opacity: 1; }
.remark-label-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px; }
.remark-label-row label { margin-bottom: 0; }

/* Quick Stamp Buttons */
.quick-stamp-controls { display: flex; gap: 4px; align-items: center; }
.btn-stamp { padding: 4px 10px; border-radius: 4px; cursor: pointer; font-weight: 700; font-size: 0.9rem; border: 2px solid transparent; transition: all 0.15s; }
.btn-stamp-vrai { background: #dcfce7; color: #16a34a; border-color: #bbf7d0; }
.btn-stamp-vrai:hover, .btn-stamp-vrai.active { background: #16a34a; color: white; border-color: #16a34a; }
.btn-stamp-faux { background: #fee2e2; color: #dc2626; border-color: #fecaca; }
.btn-stamp-faux:hover, .btn-stamp-faux.active { background: #dc2626; color: white; border-color: #dc2626; }


/* Annotation Type Quick Selectors */
.annotation-type-controls { display: flex; gap: 3px; align-items: center; }
.btn-annot-type { padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 1rem; border: 2px solid transparent; background: #f1f5f9; transition: all 0.15s; line-height: 1; }
.btn-annot-type:hover { background: #e2e8f0; border-color: #94a3b8; }
.btn-annot-type.active { background: #3b82f6; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.3); }

/* Bouton banque de commentaires */
.btn-comment-bank { background: #EEEDFE; border-color: #AFA9EC; color: #534AB7; }
.btn-comment-bank:hover { background: #EEEDFE; border-color: #AFA9EC; }
.btn-comment-bank.active { background: #7F77DD; border-color: #534AB7; color: white; }

/* Zone de drop visuelle sur le canvas */
.canvas-wrapper.drag-over { box-shadow: 0 0 0 4px #3b82f6, 0 0 20px rgba(59,130,246,0.3); }

/* ── Responsive — Tablette paysage (768–1023px) ─────────────────────────── */
@media (max-width: 1180px) and (min-width: 768px) {
  .inspector-panel { width: 280px; }
  .toolbar { flex-wrap: wrap; gap: 8px; padding: 8px 12px; }
  .actions button { min-height: 44px; padding: 8px 12px; }
  .btn-stamp { min-height: 44px; padding: 6px 12px; }
  .btn-annot-type { min-height: 44px; min-width: 44px; }
  .zoom-controls button { min-height: 44px; min-width: 44px; }
}

/* ── Responsive — Tablette portrait / mobile (<768px) ──────────────────── */
@media (max-width: 767px) {
  .workspace { flex-direction: column; }
  .viewer-container { min-height: 50vh; min-height: 50dvh; }
  .inspector-panel {
    width: 100%;
    border-left: none;
    border-top: 1px solid #dee2e6;
    max-height: 35vh;
    max-height: 35dvh;
    overflow-y: auto;
  }
  .toolbar { flex-wrap: wrap; gap: 6px; padding: 6px 10px; }
  .actions button { min-height: 44px; padding: 8px 12px; }
  .viewer-toolbar { gap: 6px; flex-wrap: wrap; }
  .btn-stamp { min-height: 44px; padding: 6px 12px; font-size: 1rem; }
  .btn-annot-type { min-height: 44px; min-width: 44px; }
  .zoom-controls button { min-height: 44px; min-width: 44px; }
  .annotation-editor-overlay { width: calc(100vw - 32px); left: 16px; transform: none; top: 80px; }
}

/* Sync dot indicator */
.sync-indicator { display: inline-flex; align-items: center; margin-left: 8px; }
.sync-dot { width: 8px; height: 8px; border-radius: 50%; }
.sync-ok .sync-dot { background: #22c55e; }
.sync-warning .sync-dot { background: #f59e0b; animation: pulse-sync 1.5s infinite; }
.sync-critical .sync-dot { background: #ef4444; animation: pulse-sync 1s infinite; }
.sync-offline .sync-dot { background: #94a3b8; }
@keyframes pulse-sync { 0%,100% { opacity:1; } 50% { opacity:0.4; } }

/* Quick score buttons */
.quick-btns { display: flex; gap: 4px; margin-top: 6px; flex-wrap: wrap; }
.qb { padding: 2px 8px; font-size: 11px; border: 1px solid #e2e8f0; border-radius: 999px; background: #fff; cursor: pointer; color: #64748b; transition: all 0.15s; }
.qb:hover { background: #EEEDFE; border-color: #AFA9EC; color: #534AB7; }
</style>
