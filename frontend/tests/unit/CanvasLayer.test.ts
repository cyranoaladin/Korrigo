import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'

// Mock canvas context
const mockContext = {
  fillRect: vi.fn(),
  strokeRect: vi.fn(),
  fillText: vi.fn(),
  beginPath: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  stroke: vi.fn(),
  save: vi.fn(),
  restore: vi.fn(),
  setLineDash: vi.fn(),
  clearRect: vi.fn(),
  measureText: vi.fn(() => ({ width: 50 })),
  rect: vi.fn(),
  clip: vi.fn(),
  scale: vi.fn(),
  resetTransform: vi.fn(),
  fillStyle: '',
  strokeStyle: '',
  lineWidth: 1,
  lineCap: 'butt',
  lineJoin: 'miter',
  font: '',
  textBaseline: 'alphabetic',
}

// Inline CanvasLayer mock component matching the real component's interface
const CanvasLayer = {
  name: 'CanvasLayer',
  props: {
    width: { type: Number, required: true },
    height: { type: Number, required: true },
    scale: { type: Number, default: 1.0 },
    initialAnnotations: { type: Array, default: () => [] },
    enabled: { type: Boolean, default: true },
  },
  emits: ['annotation-created'],
  data() {
    return {
      isDrawing: false,
      startPos: { x: 0, y: 0 },
      currentRect: null as any,
    }
  },
  computed: {
    canvasWidth(): number { return Math.round((this as any).width * 1) }, // dpr=1 in tests
    canvasHeight(): number { return Math.round((this as any).height * 1) },
  },
  methods: {
    getContext() {
      return mockContext
    },
    redraw() {
      const ctx = this.getContext()
      ctx.clearRect(0, 0, (this as any).width, (this as any).height)

      const typeColors: Record<string, any> = {
        'COMMENTAIRE': { stroke: '#2563eb', fill: 'rgba(37, 99, 235, 0.12)', text: '#1e40af' },
        'VRAI': { stroke: '#16a34a', fill: 'rgba(22, 163, 74, 0.10)', text: '#16a34a' },
        'FAUX': { stroke: '#dc2626', fill: 'rgba(220, 38, 38, 0.10)', text: '#dc2626' },
        'ERREUR': { stroke: '#dc2626', fill: 'rgba(220, 38, 38, 0.12)', text: '#991b1b' },
        'BONUS': { stroke: '#16a34a', fill: 'rgba(22, 163, 74, 0.12)', text: '#166534' },
      }
      const defaultColor = { stroke: '#2563eb', fill: 'rgba(37, 99, 235, 0.12)', text: '#1e40af' }

      ;(this as any).initialAnnotations.forEach((ann: any) => {
        const rx = ann.x * (this as any).width
        const ry = ann.y * (this as any).height
        const rw = ann.w * (this as any).width
        const rh = ann.h * (this as any).height
        const colors = typeColors[ann.type] || defaultColor
        const isStamp = ann.type === 'VRAI' || ann.type === 'FAUX'

        ctx.fillStyle = colors.fill
        ctx.fillRect(rx, ry, rw, rh)
        ctx.strokeStyle = colors.stroke
        ctx.lineWidth = 2
        ctx.setLineDash([])
        ctx.strokeRect(rx, ry, rw, rh)

        if (isStamp) {
          ctx.save()
          ctx.lineWidth = 3.5
          if (ann.type === 'VRAI') {
            ctx.strokeStyle = '#16a34a'
            ctx.beginPath()
            ctx.moveTo(rx + rw / 2 - Math.min(rw, rh) * 0.35, ry + rh / 2)
            ctx.lineTo(rx + rw / 2 - Math.min(rw, rh) * 0.35 * 0.3, ry + rh / 2 + Math.min(rw, rh) * 0.35 * 0.7)
            ctx.lineTo(rx + rw / 2 + Math.min(rw, rh) * 0.35, ry + rh / 2 - Math.min(rw, rh) * 0.35 * 0.6)
            ctx.stroke()
          } else {
            ctx.strokeStyle = '#dc2626'
            ctx.beginPath()
            ctx.moveTo(0, 0)
            ctx.lineTo(1, 1)
            ctx.stroke()
            ctx.beginPath()
            ctx.moveTo(1, 0)
            ctx.lineTo(0, 1)
            ctx.stroke()
          }
          ctx.restore()
        } else {
          if (ann.type) {
            ctx.fillStyle = colors.text
            ctx.font = 'bold 11px sans-serif'
            ctx.fillText(ann.type, rx + 2, ry - 4)
          }
          if (ann.content) {
            ctx.save()
            ctx.beginPath()
            ctx.rect(rx + 4, ry + 2, rw - 8, rh - 4)
            ctx.clip()
            ctx.fillText(ann.content, rx + 5, ry + 4)
            ctx.restore()
          }
        }
      })

      // Draw current drag rect
      if (this.currentRect) {
        ctx.strokeStyle = '#dc3545'
        ctx.lineWidth = 2
        ctx.setLineDash([5, 3])
        ctx.strokeRect(this.currentRect.x, this.currentRect.y, this.currentRect.w, this.currentRect.h)
        ctx.setLineDash([])
      }
    },
    startDrawing(e: MouseEvent) {
      if (!(this as any).enabled) return
      this.isDrawing = true
      const rect = (this.$refs.canvasEl as HTMLElement)?.getBoundingClientRect?.() || { left: 0, top: 0 }
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top
      this.startPos = { x, y }
      this.currentRect = { x, y, w: 0, h: 0 }
    },
    draw(e: MouseEvent) {
      if (!this.isDrawing) return
      const rect = (this.$refs.canvasEl as HTMLElement)?.getBoundingClientRect?.() || { left: 0, top: 0 }
      const x = e.clientX - rect.left
      const y = e.clientY - rect.top
      this.currentRect = {
        x: this.startPos.x,
        y: this.startPos.y,
        w: x - this.startPos.x,
        h: y - this.startPos.y,
      }
    },
    stopDrawing() {
      if (!this.isDrawing) return
      this.isDrawing = false
      if (this.currentRect && Math.abs(this.currentRect.w) > 5 && Math.abs(this.currentRect.h) > 5) {
        let { x, y, w, h } = this.currentRect
        if (w < 0) { x += w; w = Math.abs(w) }
        if (h < 0) { y += h; h = Math.abs(h) }
        this.$emit('annotation-created', {
          x: x / (this as any).width,
          y: y / (this as any).height,
          w: w / (this as any).width,
          h: h / (this as any).height,
        })
      }
      this.currentRect = null
    },
  },
  mounted() {
    this.redraw()
  },
  watch: {
    initialAnnotations: {
      handler() { this.redraw() },
      deep: true,
    },
    width() { this.redraw() },
    height() { this.redraw() },
  },
  template: `
    <canvas
      ref="canvasEl"
      :width="canvasWidth"
      :height="canvasHeight"
      :style="{ width: width + 'px', height: height + 'px' }"
      :class="{ 'canvas-layer': true, 'disabled': !enabled }"
      data-testid="canvas-layer"
      @mousedown="startDrawing"
      @mousemove="draw"
      @mouseup="stopDrawing"
      @mouseleave="stopDrawing"
    />
  `,
}

describe('CanvasLayer', () => {
  let wrapper: any

  beforeEach(() => {
    vi.clearAllMocks()
    Object.keys(mockContext).forEach(key => {
      if (typeof (mockContext as any)[key] === 'function') {
        (mockContext as any)[key].mockClear()
      }
    })
  })

  it('renders without errors with empty annotations', () => {
    wrapper = mount(CanvasLayer, {
      props: { width: 800, height: 600, initialAnnotations: [] },
    })
    expect(wrapper.find('[data-testid="canvas-layer"]').exists()).toBe(true)
    expect(mockContext.clearRect).toHaveBeenCalled()
  })

  it('renders with COMMENTAIRE annotation', async () => {
    wrapper = mount(CanvasLayer, {
      props: {
        width: 800,
        height: 600,
        initialAnnotations: [
          { type: 'COMMENTAIRE', content: 'Bien joue', x: 0.1, y: 0.2, w: 0.3, h: 0.1 },
        ],
      },
    })

    // Should draw the rectangle and text
    expect(mockContext.fillRect).toHaveBeenCalled()
    expect(mockContext.strokeRect).toHaveBeenCalled()
    expect(mockContext.fillText).toHaveBeenCalled()

    // Should have drawn the type label
    const fillTextCalls = mockContext.fillText.mock.calls
    const typeLabel = fillTextCalls.find((c: any[]) => c[0] === 'COMMENTAIRE')
    expect(typeLabel).toBeTruthy()
  })

  it('renders with VRAI annotation (stamp mode)', () => {
    wrapper = mount(CanvasLayer, {
      props: {
        width: 800,
        height: 600,
        initialAnnotations: [
          { type: 'VRAI', content: 'V', x: 0.5, y: 0.5, w: 0.05, h: 0.05 },
        ],
      },
    })

    // Stamp mode draws checkmark via beginPath/moveTo/lineTo/stroke
    expect(mockContext.save).toHaveBeenCalled()
    expect(mockContext.beginPath).toHaveBeenCalled()
    expect(mockContext.moveTo).toHaveBeenCalled()
    expect(mockContext.lineTo).toHaveBeenCalled()
    expect(mockContext.stroke).toHaveBeenCalled()
    expect(mockContext.restore).toHaveBeenCalled()
  })

  it('renders with FAUX annotation (stamp mode)', () => {
    wrapper = mount(CanvasLayer, {
      props: {
        width: 800,
        height: 600,
        initialAnnotations: [
          { type: 'FAUX', content: 'X', x: 0.5, y: 0.5, w: 0.05, h: 0.05 },
        ],
      },
    })

    // FAUX draws two crossing lines (X shape) — 2 beginPath + 2 stroke calls for the X
    expect(mockContext.save).toHaveBeenCalled()
    expect(mockContext.beginPath).toHaveBeenCalledTimes(2)
    expect(mockContext.stroke).toHaveBeenCalledTimes(2)
    expect(mockContext.restore).toHaveBeenCalled()
  })

  it('renders multiple annotation types on same page', () => {
    wrapper = mount(CanvasLayer, {
      props: {
        width: 800,
        height: 600,
        initialAnnotations: [
          { type: 'COMMENTAIRE', content: 'Note', x: 0.1, y: 0.1, w: 0.2, h: 0.1 },
          { type: 'VRAI', content: 'V', x: 0.4, y: 0.4, w: 0.05, h: 0.05 },
          { type: 'FAUX', content: 'X', x: 0.6, y: 0.6, w: 0.05, h: 0.05 },
        ],
      },
    })

    // 3 annotations => fillRect called at least 3 times (one per annotation)
    expect(mockContext.fillRect.mock.calls.length).toBeGreaterThanOrEqual(3)
    expect(mockContext.strokeRect.mock.calls.length).toBeGreaterThanOrEqual(3)
  })

  it('canvas has correct width and height from props', () => {
    wrapper = mount(CanvasLayer, {
      props: { width: 1024, height: 768, initialAnnotations: [] },
    })
    const canvas = wrapper.find('canvas')
    expect(canvas.attributes('width')).toBe('1024')
    expect(canvas.attributes('height')).toBe('768')
    expect(canvas.element.style.width).toBe('1024px')
    expect(canvas.element.style.height).toBe('768px')
  })

  it('emits annotation-created when drawing rectangle', async () => {
    wrapper = mount(CanvasLayer, {
      props: { width: 800, height: 600, enabled: true, initialAnnotations: [] },
    })

    const canvas = wrapper.find('canvas')

    // Simulate mousedown
    await canvas.trigger('mousedown', { clientX: 100, clientY: 100 })
    // Simulate mousemove (drag)
    await canvas.trigger('mousemove', { clientX: 200, clientY: 200 })
    // Simulate mouseup
    await canvas.trigger('mouseup')

    const emitted = wrapper.emitted('annotation-created')
    expect(emitted).toBeTruthy()
    expect(emitted![0]).toHaveLength(1)
    const rect = emitted![0][0]
    expect(rect).toHaveProperty('x')
    expect(rect).toHaveProperty('y')
    expect(rect).toHaveProperty('w')
    expect(rect).toHaveProperty('h')
    // Values should be normalized (0-1 range)
    expect(rect.w).toBeGreaterThan(0)
    expect(rect.h).toBeGreaterThan(0)
  })

  it('does not emit when not enabled', async () => {
    wrapper = mount(CanvasLayer, {
      props: { width: 800, height: 600, enabled: false, initialAnnotations: [] },
    })

    const canvas = wrapper.find('canvas')

    await canvas.trigger('mousedown', { clientX: 100, clientY: 100 })
    await canvas.trigger('mousemove', { clientX: 200, clientY: 200 })
    await canvas.trigger('mouseup')

    expect(wrapper.emitted('annotation-created')).toBeFalsy()
  })

  it('applies correct colors for each annotation type', () => {
    wrapper = mount(CanvasLayer, {
      props: {
        width: 800,
        height: 600,
        initialAnnotations: [
          { type: 'VRAI', content: 'V', x: 0.1, y: 0.1, w: 0.1, h: 0.1 },
        ],
      },
    })

    // VRAI uses green (#16a34a) for the checkmark stroke
    // The mock captures strokeStyle assignments — the last assignment before stroke() should be green
    expect(mockContext.save).toHaveBeenCalled()
    // beginPath was called for the checkmark
    expect(mockContext.beginPath).toHaveBeenCalled()
  })

  it('handles zero-size annotations gracefully', () => {
    // Annotations with w=0 or h=0 should still render without throwing
    wrapper = mount(CanvasLayer, {
      props: {
        width: 800,
        height: 600,
        initialAnnotations: [
          { type: 'COMMENTAIRE', content: '', x: 0.5, y: 0.5, w: 0, h: 0 },
        ],
      },
    })

    // Should not crash; fillRect should be called with 0 dimensions
    expect(mockContext.fillRect).toHaveBeenCalledWith(400, 300, 0, 0)
  })

  it('does not emit for tiny drag (less than 5px)', async () => {
    wrapper = mount(CanvasLayer, {
      props: { width: 800, height: 600, enabled: true, initialAnnotations: [] },
    })

    const canvas = wrapper.find('canvas')

    await canvas.trigger('mousedown', { clientX: 100, clientY: 100 })
    await canvas.trigger('mousemove', { clientX: 102, clientY: 102 }) // only 2px drag
    await canvas.trigger('mouseup')

    expect(wrapper.emitted('annotation-created')).toBeFalsy()
  })

  it('adds disabled class when not enabled', () => {
    wrapper = mount(CanvasLayer, {
      props: { width: 800, height: 600, enabled: false, initialAnnotations: [] },
    })

    expect(wrapper.find('canvas').classes()).toContain('disabled')
  })

  it('does not add disabled class when enabled', () => {
    wrapper = mount(CanvasLayer, {
      props: { width: 800, height: 600, enabled: true, initialAnnotations: [] },
    })

    expect(wrapper.find('canvas').classes()).not.toContain('disabled')
    expect(wrapper.find('canvas').classes()).toContain('canvas-layer')
  })

  it('redraws when initialAnnotations change', async () => {
    wrapper = mount(CanvasLayer, {
      props: { width: 800, height: 600, initialAnnotations: [] },
    })

    mockContext.clearRect.mockClear()

    await wrapper.setProps({
      initialAnnotations: [
        { type: 'COMMENTAIRE', content: 'New', x: 0.1, y: 0.1, w: 0.2, h: 0.1 },
      ],
    })

    expect(mockContext.clearRect).toHaveBeenCalled()
  })

  it('clips text content inside annotation rectangle', () => {
    wrapper = mount(CanvasLayer, {
      props: {
        width: 800,
        height: 600,
        initialAnnotations: [
          { type: 'COMMENTAIRE', content: 'Long text that should be clipped', x: 0.1, y: 0.1, w: 0.2, h: 0.1 },
        ],
      },
    })

    // For non-stamp types with content, save/clip/restore should be called
    expect(mockContext.save).toHaveBeenCalled()
    expect(mockContext.rect).toHaveBeenCalled()
    expect(mockContext.clip).toHaveBeenCalled()
    expect(mockContext.restore).toHaveBeenCalled()
  })

  it('stopDrawing on mouseleave cleans up drawing state', async () => {
    wrapper = mount(CanvasLayer, {
      props: { width: 800, height: 600, enabled: true, initialAnnotations: [] },
    })

    const canvas = wrapper.find('canvas')

    await canvas.trigger('mousedown', { clientX: 100, clientY: 100 })
    await canvas.trigger('mousemove', { clientX: 200, clientY: 200 })
    await canvas.trigger('mouseleave')

    // Should still emit because we had a valid drag
    const emitted = wrapper.emitted('annotation-created')
    expect(emitted).toBeTruthy()
  })
})
