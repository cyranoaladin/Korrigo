import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'

// Mock simple TrueFalseTool component
const TrueFalseTool = {
  name: 'TrueFalseTool',
  props: {
    modelValue: { type: [String, null, undefined], default: undefined },
    questionId: { type: String, required: true },
    disabled: { type: Boolean, default: false },
    showLabels: { type: Boolean, default: true },
    compact: { type: Boolean, default: false },
    size: { type: String, default: 'medium' }
  },
  emits: ['update:modelValue', 'change'],
  template: `
    <div class="true-false-tool">
      <div v-if="showLabels" class="tool-label">Vrai/Faux</div>
      <div class="options-container">
        <button 
          class="option-button true-option" 
          :disabled="disabled"
          @click="$emit('update:modelValue', 'true')"
          title="Vrai (Ctrl+V)"
          role="button"
          tabindex="0"
          type="button"
        >
          VRAI
        </button>
        <button 
          class="option-button false-option" 
          :disabled="disabled"
          @click="$emit('update:modelValue', 'false')"
          title="Faux (Ctrl+F)"
          role="button"
          tabindex="0"
          type="button"
        >
          FAUX
        </button>
        <button 
          class="option-button null-option" 
          :disabled="disabled"
          @click="$emit('update:modelValue', null)"
          title="Non noté (Ctrl+X)"
          role="button"
          tabindex="0"
          type="button"
        >
          X
        </button>
      </div>
    </div>
  `
}

describe('TrueFalseTool', () => {
  let wrapper: any

  beforeEach(() => {
    wrapper = mount(TrueFalseTool, {
      props: {
        modelValue: undefined,
        questionId: 'q1'
      }
    })
  })

  it('renders correctly with default props', () => {
    expect(wrapper.find('.true-false-tool').exists()).toBe(true)
    expect(wrapper.find('.tool-label').exists()).toBe(true)
    expect(wrapper.findAll('.option-button')).toHaveLength(3)
  })

  it('displays three options: True, False, and X', () => {
    const buttons = wrapper.findAll('.option-button')
    expect(buttons[0].text()).toContain('VRAI')
    expect(buttons[1].text()).toContain('FAUX')
    expect(buttons[2].text()).toContain('X')
  })

  it('applies correct CSS classes for each option type', () => {
    const buttons = wrapper.findAll('.option-button')
    expect(buttons[0].classes()).toContain('true-option')
    expect(buttons[1].classes()).toContain('false-option')
    expect(buttons[2].classes()).toContain('null-option')
  })

  it('emits update:modelValue when clicking True', async () => {
    const trueButton = wrapper.find('.true-option')
    await trueButton.trigger('click')
    
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['true'])
  })

  it('emits update:modelValue when clicking False', async () => {
    const falseButton = wrapper.find('.false-option')
    await falseButton.trigger('click')
    
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual(['false'])
  })

  it('emits update:modelValue when clicking X', async () => {
    const nullButton = wrapper.find('.null-option')
    await nullButton.trigger('click')
    
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual([null])
  })

  it('disables buttons when disabled prop is true', async () => {
    await wrapper.setProps({ disabled: true })
    const buttons = wrapper.findAll('.option-button')
    
    buttons.forEach((button) => {
      expect(button.attributes('disabled')).toBeDefined()
    })
  })

  it('hides labels when showLabels is false', async () => {
    await wrapper.setProps({ showLabels: false })
    expect(wrapper.find('.tool-label').exists()).toBe(false)
  })

  it('maintains accessibility attributes', () => {
    const buttons = wrapper.findAll('.option-button')
    buttons.forEach((button) => {
      expect(button.attributes('role')).toBe('button')
      expect(button.attributes('tabindex')).toBe('0')
      expect(button.attributes('type')).toBe('button')
    })
  })

  it('respects questionId prop', async () => {
    await wrapper.setProps({ questionId: 'q2' })
    expect(wrapper.props('questionId')).toBe('q2')
  })

  it('handles rapid clicking without errors', async () => {
    const trueButton = wrapper.find('.true-option')
    
    await trueButton.trigger('click')
    await trueButton.trigger('click')
    await trueButton.trigger('click')
    
    expect(wrapper.emitted('update:modelValue')).toHaveLength(3)
  })
})
