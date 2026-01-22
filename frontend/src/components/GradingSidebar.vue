<script setup>
import { computed } from 'vue'

const props = defineProps({
  structure: {
    type: Array, // Expected: [ { id: 'ex1', label: 'Ex 1', max: 5, children: [...] }, ... ]
    required: true
  },
  scores: {
    type: Object, // { 'ex1': 2, 'ex1q1': 1... }
    required: true
  }
})

const emit = defineEmits(['update-score'])

// Helper to calculate total for a node recursively
const calculateNodeTotal = (node) => {
  if (node.children && node.children.length > 0) {
    return node.children.reduce((sum, child) => sum + calculateNodeTotal(child), 0)
  }
  // Leaf node: return score from props.scores or 0
  return props.scores[node.id] || 0
}

// Helper to calculate max for a node
const calculateNodeMax = (node) => {
  if (node.points !== undefined) return node.points
  if (node.children) {
    return node.children.reduce((sum, child) => sum + calculateNodeMax(child), 0)
  }
  return 0
}

const updateScore = (id, value) => {
  emit('update-score', { id, value })
}
</script>

<template>
  <div class="grading-sidebar-content">
    <div
      v-for="node in structure"
      :key="node.id"
      class="node-container"
    >
      <!-- HEADER NODE (Exercise or Question with children) -->
      <div
        v-if="node.children && node.children.length > 0"
        class="node-header"
      >
        <span class="label">{{ node.label }}</span>
        <span class="sub-total">
          {{ calculateNodeTotal(node) }} / {{ calculateNodeMax(node) }}
        </span>
      </div>

      <!-- LEAF NODE (Input field) -->
      <div
        v-else
        class="node-leaf"
      >
        <label :for="node.id">{{ node.label }}</label>
        <div class="input-wrapper">
          <input 
            :id="node.id"
            type="number" 
            :value="scores[node.id] || 0"
            min="0"
            :max="node.points"
            step="0.25"
            @input="updateScore(node.id, parseFloat($event.target.value))"
          >
          <span class="max-points">/ {{ node.points }}</span>
        </div>
      </div>

      <!-- RECURSION -->
      <div
        v-if="node.children"
        class="children-container"
      >
        <!-- Self-reference for recursion: -->
        <!-- Since we are in the same file, we can't easily self-import in script setup without naming the component.
             In Vue 3, <script setup> components are closed.
             Standard pattern for recursion in SFC:
             Use a separate component OR use <component :is="..."> if defined.
             However, simplified approach: We iterate `GradingSidebar` inside itself? 
             No, that causes infinite loop if not careful.
             Better approach: 
             If we want true recursion in one file, we need to define a recursive SubComponent in the same file 
             or just handle 2-3 levels deep manually if constrained.
             BUT "Task 3... Recursive Rendering". 
             
             SOLUTION: We will define a `GradingNode.vue` functionality inside this file 
             by extracting the recursive logic into a transparent wrapper or assuming `GradingSidebar` is used recursively.
             
             Let's implement a `GradingNode` component SEPARATELY if needed, 
             OR use the `name` export to allow self-reference.
         -->
        <GradingSidebar 
          :structure="node.children" 
          :scores="scores" 
          @update-score="$emit('update-score', $event)" 
        />
      </div>
    </div>
  </div>
</template>

<script>
// We need a normal script block to define the 'name' for recursion
export default {
  name: 'GradingSidebar'
}
</script>

<style scoped>
.grading-sidebar-content {
  font-family: 'Inter', sans-serif;
  padding-left: 10px;
}
.node-container {
  margin-bottom: 5px;
}
.node-header {
  font-weight: bold;
  background: #eef;
  padding: 5px;
  display: flex;
  justify-content: space-between;
  border-radius: 4px;
}
.node-leaf {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 5px 0;
  border-bottom: 1px dotted #ccc;
}
.children-container {
  margin-left: 15px; /* Indent children */
  border-left: 2px solid #ddd;
}
.input-wrapper input {
  width: 50px;
  text-align: center;
  margin-right: 5px;
}
.sub-total {
    color: #666;
    font-size: 0.9em;
}
</style>
