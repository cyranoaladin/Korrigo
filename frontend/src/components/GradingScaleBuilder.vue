<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Array,
    required: true,
    default: () => []
  },
  level: {
    type: Number,
    default: 0
  }
})

const emit = defineEmits(['update:modelValue'])

const addNode = () => {
  const newNode = {
    id: Date.now().toString() + Math.random().toString().slice(2, 5), // Simple unique ID
    label: props.level === 0 ? `Exercice ${props.modelValue.length + 1}` : 'Question',
    points: 0,
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
  newList[index] = { ...newList[index], [key]: value }
  emit('update:modelValue', newList)
}

const updateChildren = (index, newChildren) => {
  const newList = [...props.modelValue]
  newList[index] = { ...newList[index], children: newChildren }
  emit('update:modelValue', newList)
}

// Ensure points are number
const onPointsChange = (index, event) => {
  const val = parseFloat(event.target.value)
  updateNode(index, 'points', isNaN(val) ? 0 : val)
}

const getTotalPoints = (nodes) => {
  return nodes.reduce((sum, node) => {
    let nodePoints = node.points || 0
    if (node.children && node.children.length > 0) {
      // If has children, points might be sum of children or defined on node (usually sum)
      // SPEC implies structure tree. Let's assume points are on leaf nodes or explicitly set.
      // If we want auto-sum, we can ignore parent points or make it read-only.
      // For builder flexibility, we let user define points anywhere, but typically leaves.
      nodePoints += getTotalPoints(node.children)
    }
    return sum + nodePoints
  }, 0)
}

const totalPoints = computed(() => getTotalPoints(props.modelValue))

</script>

<template>
  <div class="scale-builder">
    <div v-if="level === 0" class="global-actions">
        <h3>Total Examen: {{ totalPoints }} pts</h3>
        <button @click="addNode" class="btn-add-main">+ Ajouter Exercice</button>
    </div>

    <!-- Recursive List -->
    <div v-for="(node, index) in modelValue" :key="node.id" class="node-wrapper" :style="{ marginLeft: level * 20 + 'px' }">
      <div class="node-row">
        <!-- Label Input -->
        <input 
          type="text" 
          :value="node.label" 
          @input="updateNode(index, 'label', $event.target.value)"
          placeholder="Titre (ex: Exercice 1)"
          class="input-label"
        />

        <!-- Points Input (Only if no children? Or always? Let's allow always for mixed models) -->
        <div class="points-wrapper">
             <input 
              type="number" 
              :value="node.points" 
              @input="onPointsChange(index, $event)"
              min="0"
              step="0.25"
              class="input-points"
            />
            <span>pts</span>
        </div>

        <!-- Actions -->
        <div class="actions">
             <!-- Add Child -->
             <button @click="updateChildren(index, [...(node.children || []), {
                id: Date.now().toString() + Math.random().toString().slice(2,5),
                label: 'Question', 
                points: 0, 
                children: []
             }])" class="btn-mini" title="Ajouter sous-question">
               +
             </button>
             
             <!-- Delete -->
             <button @click="removeNode(index)" class="btn-mini btn-danger" title="Supprimer">
               🗑️
             </button>
        </div>
      </div>

      <!-- Recursive Children -->
      <div class="children-block" v-if="node.children && node.children.length > 0">
         <GradingScaleBuilder 
            :model-value="node.children"
            :level="level + 1"
            @update:modelValue="updateChildren(index, $event)"
         />
      </div>
      <!-- If empty children but want to show drop area? Not needed for MVP -->
    </div>

    <div v-if="level > 0" class="sub-actions">
      <button @click="addNode" class="btn-add-sub">+ Ajouter Question</button>
    </div>
  </div>
</template>

<script>
export default {
  name: 'GradingScaleBuilder'
}
</script>

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
</style>
