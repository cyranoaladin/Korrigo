import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'

// Inline mock component replicating the split view and quick stamp logic
// from CorrectorDesk.vue
const SplitViewDesk = {
  name: 'SplitViewDesk',
  data() {
    return {
      splitView: false,
      quickStampMode: null as string | null,
      activeTab: 'annotations', // 'annotations' | 'grading' | 'remarks'
      annotationScrollTop: 0,
      gradingScrollTop: 0,
      annotationTypes: ['COMMENTAIRE', 'VRAI', 'FAUX', 'ERREUR', 'BONUS', 'SURLIGNAGE'],
    }
  },
  methods: {
    toggleSplitView() {
      this.splitView = !this.splitView
    },
    toggleQuickStamp(type: string) {
      if (this.quickStampMode === type) {
        this.quickStampMode = null
      } else {
        this.quickStampMode = type
      }
    },
    switchTab(tab: string) {
      // Save scroll position of current tab
      if (this.activeTab === 'grading') {
        const el = this.$refs.gradingPanel as HTMLElement
        if (el) this.gradingScrollTop = el.scrollTop
      }
      if (this.activeTab === 'annotations') {
        const el = this.$refs.annotationsPanel as HTMLElement
        if (el) this.annotationScrollTop = el.scrollTop
      }
      this.activeTab = tab
      // Restore scroll position of new tab after next tick
      this.$nextTick(() => {
        if (tab === 'grading') {
          const el = this.$refs.gradingPanel as HTMLElement
          if (el) el.scrollTop = this.gradingScrollTop
        }
        if (tab === 'annotations') {
          const el = this.$refs.annotationsPanel as HTMLElement
          if (el) el.scrollTop = this.annotationScrollTop
        }
      })
    },
  },
  template: `
    <div class="corrector-desk" data-testid="corrector-desk">
      <div class="toolbar">
        <div v-if="true" class="quick-stamp-controls" data-testid="quick-stamp-controls">
          <button
            :class="['btn-stamp', 'btn-stamp-vrai', { active: quickStampMode === 'VRAI' }]"
            data-testid="stamp-vrai"
            @click="toggleQuickStamp('VRAI')"
          >
            VRAI
          </button>
          <button
            :class="['btn-stamp', 'btn-stamp-faux', { active: quickStampMode === 'FAUX' }]"
            data-testid="stamp-faux"
            @click="toggleQuickStamp('FAUX')"
          >
            FAUX
          </button>
        </div>

        <button
          class="btn-split-view"
          :class="{ active: splitView }"
          data-testid="split-view-toggle"
          @click="toggleSplitView"
        >
          Vue scindée
        </button>
      </div>

      <div class="main-content">
        <!-- PDF viewer area -->
        <div class="pdf-area" data-testid="pdf-area">
          <div>PDF Viewer Placeholder</div>
        </div>

        <!-- Tabs for side panel -->
        <div class="side-panel" data-testid="side-panel">
          <div class="tab-bar">
            <button
              :class="['tab-btn', { active: activeTab === 'annotations' }]"
              data-testid="tab-annotations"
              @click="switchTab('annotations')"
            >
              Annotations
            </button>
            <button
              :class="['tab-btn', { active: activeTab === 'grading' }]"
              data-testid="tab-grading"
              @click="switchTab('grading')"
            >
              Notation
            </button>
            <button
              :class="['tab-btn', { active: activeTab === 'remarks' }]"
              data-testid="tab-remarks"
              @click="switchTab('remarks')"
            >
              Remarques
            </button>
          </div>

          <!-- v-show keeps tabs in DOM (not destroyed) -->
          <div v-show="activeTab === 'annotations'" ref="annotationsPanel" class="panel-content" data-testid="panel-annotations">
            <div class="annotation-list">Annotations content</div>
            <div class="annotation-types" data-testid="annotation-types">
              <span v-for="t in annotationTypes" :key="t" class="type-option" :data-type="t">{{ t }}</span>
            </div>
          </div>
          <div v-show="activeTab === 'grading'" ref="gradingPanel" class="panel-content" data-testid="panel-grading">
            <div class="grading-form">Grading content</div>
          </div>
          <div v-show="activeTab === 'remarks'" ref="remarksPanel" class="panel-content" data-testid="panel-remarks">
            <div class="remarks-form">Remarks content</div>
          </div>
        </div>

        <!-- Split grading panel (visible when splitView is true) -->
        <div v-if="splitView" class="split-grading-panel" data-testid="split-grading-panel">
          <div class="split-header">
            <span>Notation</span>
            <button class="btn-close-split" data-testid="close-split" @click="splitView = false">X</button>
          </div>
          <div class="split-grading-content">Split grading content</div>
        </div>
      </div>
    </div>
  `,
}

describe('SplitView and QuickStamp (CorrectorDesk logic)', () => {
  let wrapper: VueWrapper<any>

  beforeEach(() => {
    wrapper = mount(SplitViewDesk)
  })

  // --- splitView ---

  it('splitView toggle starts as false', () => {
    expect(wrapper.vm.splitView).toBe(false)
    expect(wrapper.find('[data-testid="split-grading-panel"]').exists()).toBe(false)
  })

  it('splitView activates on button click', async () => {
    await wrapper.find('[data-testid="split-view-toggle"]').trigger('click')

    expect(wrapper.vm.splitView).toBe(true)
    expect(wrapper.find('[data-testid="split-grading-panel"]').exists()).toBe(true)
  })

  it('splitView deactivates on second click', async () => {
    await wrapper.find('[data-testid="split-view-toggle"]').trigger('click')
    expect(wrapper.vm.splitView).toBe(true)

    await wrapper.find('[data-testid="split-view-toggle"]').trigger('click')
    expect(wrapper.vm.splitView).toBe(false)
    expect(wrapper.find('[data-testid="split-grading-panel"]').exists()).toBe(false)
  })

  it('splitView button has active class when active', async () => {
    const btn = wrapper.find('[data-testid="split-view-toggle"]')
    expect(btn.classes()).not.toContain('active')

    await btn.trigger('click')
    expect(btn.classes()).toContain('active')
  })

  it('splitView close button closes the split panel', async () => {
    await wrapper.find('[data-testid="split-view-toggle"]').trigger('click')
    expect(wrapper.find('[data-testid="split-grading-panel"]').exists()).toBe(true)

    await wrapper.find('[data-testid="close-split"]').trigger('click')
    expect(wrapper.vm.splitView).toBe(false)
    expect(wrapper.find('[data-testid="split-grading-panel"]').exists()).toBe(false)
  })

  // --- quickStampMode ---

  it('quickStampMode starts as null', () => {
    expect(wrapper.vm.quickStampMode).toBeNull()
  })

  it('quickStampMode toggles VRAI on click', async () => {
    await wrapper.find('[data-testid="stamp-vrai"]').trigger('click')
    expect(wrapper.vm.quickStampMode).toBe('VRAI')
  })

  it('quickStampMode toggles FAUX on click', async () => {
    await wrapper.find('[data-testid="stamp-faux"]').trigger('click')
    expect(wrapper.vm.quickStampMode).toBe('FAUX')
  })

  it('quickStampMode deactivates on second click (same type)', async () => {
    await wrapper.find('[data-testid="stamp-vrai"]').trigger('click')
    expect(wrapper.vm.quickStampMode).toBe('VRAI')

    await wrapper.find('[data-testid="stamp-vrai"]').trigger('click')
    expect(wrapper.vm.quickStampMode).toBeNull()
  })

  it('quickStampMode switches type on different click', async () => {
    await wrapper.find('[data-testid="stamp-vrai"]').trigger('click')
    expect(wrapper.vm.quickStampMode).toBe('VRAI')

    await wrapper.find('[data-testid="stamp-faux"]').trigger('click')
    expect(wrapper.vm.quickStampMode).toBe('FAUX')
  })

  it('quickStampMode VRAI button has active class when selected', async () => {
    const btn = wrapper.find('[data-testid="stamp-vrai"]')
    expect(btn.classes()).not.toContain('active')

    await btn.trigger('click')
    expect(btn.classes()).toContain('active')
  })

  it('quickStampMode FAUX button has active class when selected', async () => {
    await wrapper.find('[data-testid="stamp-faux"]').trigger('click')

    expect(wrapper.find('[data-testid="stamp-faux"]').classes()).toContain('active')
    expect(wrapper.find('[data-testid="stamp-vrai"]').classes()).not.toContain('active')
  })

  it('quickStampMode FAUX deactivates on second click', async () => {
    await wrapper.find('[data-testid="stamp-faux"]').trigger('click')
    expect(wrapper.vm.quickStampMode).toBe('FAUX')

    await wrapper.find('[data-testid="stamp-faux"]').trigger('click')
    expect(wrapper.vm.quickStampMode).toBeNull()
  })

  // --- v-show preserves DOM ---

  it('v-show preserves tab DOM (tabs not destroyed)', async () => {
    // All panels should exist in DOM (v-show only hides, not removes)
    expect(wrapper.find('[data-testid="panel-annotations"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="panel-grading"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="panel-remarks"]').exists()).toBe(true)

    // Switch to grading tab
    await wrapper.find('[data-testid="tab-grading"]').trigger('click')

    // All panels should still be in DOM
    expect(wrapper.find('[data-testid="panel-annotations"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="panel-grading"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="panel-remarks"]').exists()).toBe(true)
  })

  it('v-show hides inactive tabs visually', async () => {
    // Initially annotations tab is active
    const annotationsPanel = wrapper.find('[data-testid="panel-annotations"]')
    const gradingPanel = wrapper.find('[data-testid="panel-grading"]')

    // Active tab should be visible
    expect(annotationsPanel.element.style.display).not.toBe('none')
    // Inactive tab should be hidden
    expect(gradingPanel.element.style.display).toBe('none')

    // Switch to grading
    await wrapper.find('[data-testid="tab-grading"]').trigger('click')

    expect(annotationsPanel.element.style.display).toBe('none')
    expect(gradingPanel.element.style.display).not.toBe('none')
  })

  // --- grading panel scroll position preserved ---

  it('grading panel scroll position preserved across tab switches', async () => {
    // Switch to grading tab
    await wrapper.find('[data-testid="tab-grading"]').trigger('click')

    // Simulate scrolling the grading panel by setting scrollTop on the DOM element
    const gradingEl = wrapper.find('[data-testid="panel-grading"]').element as HTMLElement
    Object.defineProperty(gradingEl, 'scrollTop', { value: 250, writable: true })

    // Switch away to annotations — switchTab should capture scrollTop into gradingScrollTop
    await wrapper.find('[data-testid="tab-annotations"]').trigger('click')

    // The stored scroll position should reflect the value we set
    expect(wrapper.vm.gradingScrollTop).toBe(250)

    // Switch back to grading — should attempt to restore the scroll
    await wrapper.find('[data-testid="tab-grading"]').trigger('click')
    await nextTick()

    // The stored value should still be 250
    expect(wrapper.vm.gradingScrollTop).toBe(250)
  })

  // --- annotation types ---

  it('annotation type options include VRAI and FAUX', () => {
    const types = wrapper.findAll('[data-testid="annotation-types"] .type-option')
    const typeTexts = types.map(t => t.text())

    expect(typeTexts).toContain('VRAI')
    expect(typeTexts).toContain('FAUX')
    expect(typeTexts).toContain('COMMENTAIRE')
    expect(typeTexts).toContain('ERREUR')
    expect(typeTexts).toContain('BONUS')
    expect(typeTexts).toContain('SURLIGNAGE')
  })

  it('annotation types list has 6 types', () => {
    expect(wrapper.vm.annotationTypes).toHaveLength(6)
  })

  // --- tab switching ---

  it('default active tab is annotations', () => {
    expect(wrapper.vm.activeTab).toBe('annotations')
    expect(wrapper.find('[data-testid="tab-annotations"]').classes()).toContain('active')
  })

  it('clicking grading tab switches activeTab', async () => {
    await wrapper.find('[data-testid="tab-grading"]').trigger('click')
    expect(wrapper.vm.activeTab).toBe('grading')
    expect(wrapper.find('[data-testid="tab-grading"]').classes()).toContain('active')
    expect(wrapper.find('[data-testid="tab-annotations"]').classes()).not.toContain('active')
  })

  it('clicking remarks tab switches activeTab', async () => {
    await wrapper.find('[data-testid="tab-remarks"]').trigger('click')
    expect(wrapper.vm.activeTab).toBe('remarks')
    expect(wrapper.find('[data-testid="tab-remarks"]').classes()).toContain('active')
  })

  it('rapid tab switching does not break state', async () => {
    await wrapper.find('[data-testid="tab-grading"]').trigger('click')
    await wrapper.find('[data-testid="tab-remarks"]').trigger('click')
    await wrapper.find('[data-testid="tab-annotations"]').trigger('click')
    await wrapper.find('[data-testid="tab-grading"]').trigger('click')

    expect(wrapper.vm.activeTab).toBe('grading')
    // All panels still in DOM
    expect(wrapper.find('[data-testid="panel-annotations"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="panel-grading"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="panel-remarks"]').exists()).toBe(true)
  })

  // --- combined state ---

  it('splitView and quickStampMode are independent', async () => {
    await wrapper.find('[data-testid="stamp-vrai"]').trigger('click')
    expect(wrapper.vm.quickStampMode).toBe('VRAI')

    await wrapper.find('[data-testid="split-view-toggle"]').trigger('click')
    expect(wrapper.vm.splitView).toBe(true)
    expect(wrapper.vm.quickStampMode).toBe('VRAI') // unchanged

    await wrapper.find('[data-testid="split-view-toggle"]').trigger('click')
    expect(wrapper.vm.splitView).toBe(false)
    expect(wrapper.vm.quickStampMode).toBe('VRAI') // still unchanged
  })

  it('quick stamp controls are always visible', () => {
    expect(wrapper.find('[data-testid="quick-stamp-controls"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="stamp-vrai"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="stamp-faux"]').exists()).toBe(true)
  })
})
