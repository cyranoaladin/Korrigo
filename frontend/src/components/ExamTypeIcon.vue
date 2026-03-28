<script setup>
import {
  GraduationCap, BookOpen, BookOpenCheck, Book, FileText,
  Folder, FolderOpen, Calculator, FlaskConical, Atom,
  PenLine, Globe, Music, Languages, School, Microscope,
  History, Compass, BarChart2, Cpu, Paintbrush, Dumbbell
} from 'lucide-vue-next'

const props = defineProps({
  icon: { type: String, default: '' },
  size: { type: Number, default: 24 },
})

const ICON_MAP = {
  'graduation-cap': GraduationCap,
  'graduation_cap': GraduationCap,
  'school': School,
  'book-open': BookOpen,
  'book_open': BookOpen,
  'book-open-check': BookOpenCheck,
  'book': Book,
  'file-text': FileText,
  'file_text': FileText,
  'folder': Folder,
  'folder-open': FolderOpen,
  'calculator': Calculator,
  'flask': FlaskConical,
  'flask-conical': FlaskConical,
  'beaker': FlaskConical,
  'atom': Atom,
  'microscope': Microscope,
  'pen': PenLine,
  'pen-line': PenLine,
  'globe': Globe,
  'music': Music,
  'languages': Languages,
  'language': Languages,
  'history': History,
  'compass': Compass,
  'bar-chart': BarChart2,
  'cpu': Cpu,
  'paintbrush': Paintbrush,
  'dumbbell': Dumbbell,
}

const resolvedIcon = (name) => {
  if (!name) return FileText
  return ICON_MAP[name.toLowerCase()] || ICON_MAP[name] || FileText
}
</script>

<template>
  <component :is="resolvedIcon(icon)" :size="size" />
</template>
