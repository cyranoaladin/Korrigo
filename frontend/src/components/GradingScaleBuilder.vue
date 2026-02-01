<script setup>
import { computed } from 'vue'

defineOptions({
  name: 'GradingScaleBuilder'
})

const props = defineProps({
  modelValue: {
    type: Array,
    required: true
  },
  level: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['update:modelValue'])

const generateId = () => {
    try {
        return crypto.randomUUID()
    } catch {
        return Date.now().toString() + Math.random().toString().slice(2, 8)
    }
}

const addNode = () => {
  const newNode = {
    id: generateId(),
    label: props.level === 0 ? `Exercice ${props.modelValue.length + 1}` : 'Question',
    points: 0,
    points_backup: 0,
    children: []
  }
  const newList = [...props.modelValue, newNode]
  emit('update:modelValue', newList)
}

const removeNode = (index) => {
  if (confirm('Voulez-vous vraiment supprimer cet élément ?')) {
    const newList = [...props.modelValue]
    newList.splice(index, 1)
    emit('update:modelValue', newList)
  }
}

const updateNode = (index, key, value) => {
  const newList = [...props.modelValue]
  const updatedNode = { ...newList[index], [key]: value }
  // If we manually change points, update the backup
  if (key === 'points') {
      updatedNode.points_backup = value
  }
  newList[index] = updatedNode
  emit('update:modelValue', newList)
}

const updateChildren = (index, newChildren) => {
  const newList = [...props.modelValue]
  const hasChildren = newChildren && newChildren.length > 0
  const currentNode = { ...newList[index] }

  // Logic senior: capture points before nulling them for the first child
  // If points_backup is missing or 0, and current points > 0, we backup them.
  if (hasChildren && (!currentNode.points_backup || currentNode.points_backup === 0) && currentNode.points > 0) {
    currentNode.points_backup = currentNode.points
  }

  newList[index] = { 
    ...currentNode, 
    children: newChildren,
    // If children exist, points must be 0 (sum logic takes over)
    // If children become empty, restore from points_backup
    points: hasChildren ? 0 : (currentNode.points_backup || 0)
  }
  emit('update:modelValue', newList)
}

const getNodePoints = (node) => {
  if (node.children && node.children.length > 0) {
    return getTotalPoints(node.children)
  }
  return node.points || 0
}

const getTotalPoints = (nodes) => {
  return nodes.reduce((sum, node) => sum + getNodePoints(node), 0)
}

const addChild = (index) => {
    const currentNode = props.modelValue[index]
    const isFirstChild = !currentNode.children || currentNode.children.length === 0
    
    // If it's the first child, inherit the parent's points to preserve total
    // Otherwise 0
    const initialPoints = isFirstChild ? currentNode.points : 0
    
    const newChild = {
        id: generateId(),
        label: 'Question',
        points: initialPoints,
        points_backup: 0,
        children: []
    }
    
    const newChildren = [...(currentNode.children || []), newChild]
    updateChildren(index, newChildren)
}

const totalPoints = computed(() => getTotalPoints(props.modelValue))

</script>

<template>
  <div class="scale-builder">
    <div
      v-if="level === 0"
      class="global-actions"
    >
      <h3>Total Examen: {{ totalPoints }} pts</h3>
      <button
        class="btn-add-main"
        @click="addNode"
      >
        + Ajouter Exercice
      </button>
    </div>

    <!-- Recursive List -->
    <div
      v-for="(node, nodeIdx) in modelValue"
      :key="node.id"
      class="node-wrapper"
      :style="{ marginLeft: level * 20 + 'px' }"
    >
      <div class="node-row">
        <!-- Label Input -->
        <input 
          type="text" 
          :value="node.label" 
          placeholder="Titre (ex: Exercice 1)"
          class="input-label"
          @input="updateNode(nodeIdx, 'label', $event.target.value)"
        >

        <!-- Points Input -->
        <div class="node-controls">
          <div class="points-input">
            <input 
              type="number" 
              step="0.25"
              :value="getNodePoints(node)"
              :disabled="node.children && node.children.length > 0"
              @input="e => updateNode(nodeIdx, 'points', parseFloat(e.target.value))"
            >
            <span 
              v-if="node.children && node.children.length > 0" 
              class="sum-indicator" 
              title="Calculé à partir des enfants"
            >
              (Σ)
            </span>
          </div>
          
          <button 
            v-if="level < 2" 
            class="btn-icon add-child"
            title="Ajouter une sous-question"
            @click="addChild(nodeIdx)"
          >
            +
          </button>
          <button 
            class="btn-icon delete" 
            title="Supprimer"
            @click="removeNode(nodeIdx)"
          >
            &times;
          </button>
        </div>
      </div>
      
      <div 
        v-if="node.children && node.children.length > 0" 
        class="children-warning"
      >
        Remarque : Les points de cet élément sont calculés automatiquement.
      </div>

      <!-- Recursive Children -->
      <div
        v-if="node.children && node.children.length > 0"
        class="children-block"
      >
        <GradingScaleBuilder 
          :model-value="node.children"
          :level="level + 1"
          @update:model-value="updateChildren(nodeIdx, $event)"
        />
      </div>
      <!-- If empty children but want to show drop area? Not needed for MVP -->
    </div>

    <div
      v-if="level > 0"
      class="sub-actions"
    >
      <button
        class="btn-add-sub"
        @click="addNode"
      >
        + Ajouter Question
      </button>
    </div>
  </div>
</template>



<style scoped>
.scale-builder {
  font-family: 'Inter', sans-serif;
  color: #333;
}
.global-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 8px;
}
.node-wrapper {
  border-left: 2px solid #ddd;
  padding-left: 10px;
  margin-bottom: 10px;
}
.node-row {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #fff;
  padding: 8px;
  border: 1px solid #eee;
  border-radius: 4px;
}
.input-label {
  flex: 1;
  padding: 5px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.input-points {
  width: 60px;
  padding: 5px;
  border: 1px solid #ccc;
  border-radius: 4px;
  text-align: right;
}
.points-wrapper {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.9em;
  color: #666;
}
.children-warning {
  font-size: 0.75rem;
  color: #6366f1;
  margin-top: -0.5rem;
  margin-bottom: 0.75rem;
  margin-left: 1rem;
  font-style: italic;
}

.sum-indicator { font-size: 0.8rem; font-weight: bold; color: #6366f1; cursor: help; }
.btn-add-main {
  background: #28a745;
  color: white;
  border: none;
  padding: 8px 15px;
  border-radius: 4px;
  cursor: pointer;
}
.btn-add-sub {
  background: transparent;
  color: #007bff;
  border: 1px dashed #007bff;
  padding: 5px 10px;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 5px;
  font-size: 0.9em;
}
.btn-mini {
  background: #e9ecef;
  border: none;
  padding: 5px 10px;
  border-radius: 4px;
  cursor: pointer;
}
.btn-danger {
  color: #dc3545;
  background: #fde8e8;
}
.sub-actions {
  margin-left: 20px;
}

/* Missing classes added */
.node-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.points-input input {
  width: 60px;
  padding: 6px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  text-align: right;
  font-weight: 500;
}

.btn-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: bold;
}

.add-child {
  background: #e0e7ff;
  color: #4f46e5;
}
.add-child:hover {
  background: #c7d2fe;
}

.delete {
  background: #fee2e2;
  color: #ef4444;
}
.delete:hover {
  background: #fecaca;
}
</style>
