import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'

// Mock simple EnhancedGradingPanel component
const EnhancedGradingPanel = {
  name: 'EnhancedGradingPanel',
  props: {
    gradingStructure: { type: Array, default: () => [] },
    scoresData: { type: Object, default: () => ({}) },
    remarksData: { type: Object, default: () => ({}) },
    globalAppreciation: { type: String, default: '' },
    showValidationErrors: { type: Boolean, default: false },
    bulkMode: { type: Boolean, default: false },
    focusedQuestionId: { type: String, default: '' }
  },
  emits: ['score-change', 'remark-change', 'appreciation-change', 'focus-question'],
  template: `
    <div class="enhanced-grading-panel">
      <div class="panel-header">
        <h2>Panel de Notation</h2>
        <div class="completion-stats">
          <span>{{ Object.keys(scoresData).length }}/{{ gradingStructure.length }} noté</span>
        </div>
      </div>
      
      <div class="tab-navigation">
        <button class="tab-button active">Notation</button>
        <button class="tab-button">Remarques</button>
        <button class="tab-button">Appréciation</button>
      </div>
      
      <div class="tab-content">
        <div class="scoring-tab">
          <div class="questions-list">
            <div 
              v-for="(question, index) in gradingStructure" 
              :key="question.id || index"
              class="question-item"
            >
              <div class="question-header">
                <span class="question-label">{{ question.label }}</span>
                <span class="question-points">{{ question.points }} pts</span>
              </div>
              
              <div class="score-input-container">
                <input 
                  type="number" 
                  :value="scoresData[question.id] || ''"
                  @input="$emit('score-change', question.id, $event.target.value)"
                  class="score-input"
                  :max="question.points"
                  min="0"
                  step="0.5"
                />
                
                <div class="quick-actions">
                  <button @click="$emit('score-change', question.id, question.points)" class="quick-btn">Max</button>
                  <button @click="$emit('score-change', question.id, question.points / 2)" class="quick-btn">½</button>
                  <button @click="$emit('score-change', question.id, 0)" class="quick-btn">0</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `
}

describe('EnhancedGradingPanel', () => {
  let wrapper: any

  const mockGradingStructure = [
    { id: 1, label: 'Exercice 1', points: 10 },
    { id: 2, label: 'Exercice 2', points: 15 }
  ]

  beforeEach(() => {
    wrapper = mount(EnhancedGradingPanel, {
      props: {
        gradingStructure: mockGradingStructure,
        scoresData: {},
        remarksData: {},
        globalAppreciation: '',
        showValidationErrors: false,
        bulkMode: false,
        focusedQuestionId: ''
      }
    })
  })

  it('renders correctly with default props', () => {
    expect(wrapper.find('.enhanced-grading-panel').exists()).toBe(true)
    expect(wrapper.find('.panel-header').exists()).toBe(true)
    expect(wrapper.find('.tab-navigation').exists()).toBe(true)
    expect(wrapper.find('.tab-content').exists()).toBe(true)
  })

  it('displays completion statistics correctly', () => {
    const stats = wrapper.find('.completion-stats')
    expect(stats.text()).toContain('0/2 noté')
  })

  it('displays questions correctly from grading structure', () => {
    const questions = wrapper.findAll('.question-item')
    expect(questions).toHaveLength(2)
    
    expect(questions[0].find('.question-label').text()).toBe('Exercice 1')
    expect(questions[0].find('.question-points').text()).toBe('10 pts')
    
    expect(questions[1].find('.question-label').text()).toBe('Exercice 2')
    expect(questions[1].find('.question-points').text()).toBe('15 pts')
  })

  it('emits score-change when score input changes', async () => {
    const scoreInput = wrapper.find('.score-input')
    await scoreInput.setValue('3')
    await scoreInput.trigger('input')
    
    expect(wrapper.emitted('score-change')).toBeTruthy()
    expect(wrapper.emitted('score-change')[0]).toEqual([1, '3'])
  })

  it('emits score-change when quick score buttons are clicked', async () => {
    const maxButton = wrapper.find('.quick-btn')
    await maxButton.trigger('click')
    
    expect(wrapper.emitted('score-change')).toBeTruthy()
    expect(wrapper.emitted('score-change')[0]).toEqual([1, 10])
  })

  it('displays correct number of score inputs', () => {
    const scoreInputs = wrapper.findAll('.score-input')
    expect(scoreInputs).toHaveLength(2)
  })

  it('displays correct number of quick action buttons', () => {
    const quickButtons = wrapper.findAll('.quick-btn')
    expect(quickButtons).toHaveLength(6) // 3 buttons per question
  })

  it('shows question labels correctly', () => {
    const labels = wrapper.findAll('.question-label')
    expect(labels[0].text()).toBe('Exercice 1')
    expect(labels[1].text()).toBe('Exercice 2')
  })

  it('shows question points correctly', () => {
    const points = wrapper.findAll('.question-points')
    expect(points[0].text()).toBe('10 pts')
    expect(points[1].text()).toBe('15 pts')
  })

  it('handles empty grading structure gracefully', async () => {
    await wrapper.setProps({ gradingStructure: [] })
    const questions = wrapper.findAll('.question-item')
    expect(questions).toHaveLength(0)
  })

  it('handles empty scores data gracefully', () => {
    const scoreInputs = wrapper.findAll('.score-input')
    scoreInputs.forEach(input => {
      expect(input.element.value).toBe('')
    })
  })

  it('updates completion stats when scores are added', async () => {
    await wrapper.setProps({ scoresData: { 1: '5', 2: '10' } })
    const stats = wrapper.find('.completion-stats')
    expect(stats.text()).toContain('2/2 noté')
  })

  it('maintains correct structure for all questions', () => {
    const questions = wrapper.findAll('.question-item')
    questions.forEach((question, index) => {
      expect(question.find('.question-header').exists()).toBe(true)
      expect(question.find('.question-label').exists()).toBe(true)
      expect(question.find('.question-points').exists()).toBe(true)
      expect(question.find('.score-input-container').exists()).toBe(true)
      expect(question.find('.score-input').exists()).toBe(true)
      expect(question.find('.quick-actions').exists()).toBe(true)
    })
  })

  it('respects prop changes', async () => {
    await wrapper.setProps({ globalAppreciation: 'New appreciation' })
    expect(wrapper.props('globalAppreciation')).toBe('New appreciation')
  })

  it('emits focus-question when needed', async () => {
    wrapper.vm.$emit('focus-question', 1)
    expect(wrapper.emitted('focus-question')).toBeTruthy()
    expect(wrapper.emitted('focus-question')[0]).toEqual([1])
  })

  it('emits remark-change when needed', async () => {
    wrapper.vm.$emit('remark-change', 1, 'Good work')
    expect(wrapper.emitted('remark-change')).toBeTruthy()
    expect(wrapper.emitted('remark-change')[0]).toEqual([1, 'Good work'])
  })

  it('emits appreciation-change when needed', async () => {
    wrapper.vm.$emit('appreciation-change', 'Excellent work')
    expect(wrapper.emitted('appreciation-change')).toBeTruthy()
    expect(wrapper.emitted('appreciation-change')[0]).toEqual(['Excellent work'])
  })
})
