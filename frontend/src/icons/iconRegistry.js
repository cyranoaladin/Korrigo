/**
 * Icon Registry — Korrigo Design System
 *
 * Single source of truth for all icon mappings.
 * Business-semantic names → Lucide Vue components.
 *
 * RULES:
 * - No component should import from 'lucide-vue-next' directly.
 * - All icon usage goes through AppIcon.vue or resolveIcon().
 * - Backend string ↔ icon mapping for ExamTypeIcon lives here.
 */

import {
  // Navigation & UI
  LogIn,
  LogOut,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Menu,
  X,
  Eye,
  EyeOff,
  Plus,
  PlusCircle,
  Search,
  ArrowRight,

  // Users & Roles
  GraduationCap,
  PenTool,
  PenLine,
  Settings,
  Users,
  UserCog,
  User,
  ShieldCheck,

  // Content & Documents
  FileText,
  BookOpen,
  BookOpenCheck,
  Book,
  Folder,
  FolderOpen,
  ClipboardList,
  Copy,
  Download,
  ScanSearch,
  Ruler,

  // Data & Stats
  BarChart3,
  BarChart2,
  LayoutDashboard,
  Target,
  TrendingUp,

  // Communication
  MessageSquare,
  MessageSquareText,

  // Alerts & Status
  AlertCircle,
  CircleSlash,
  CheckCircle,
  CheckCircle2,
  Info,

  // Time
  Calendar,
  Tag,

  // Exam-type specific (backend compatibility)
  School,
  Calculator,
  FlaskConical,
  Atom,
  Microscope,
  Globe,
  Music,
  Languages,
  History,
  Compass,
  Cpu,
  Paintbrush,
  Dumbbell,
} from 'lucide-vue-next'

// ─── Business-semantic icon registry ────────────────────────────────
const ICON_REGISTRY = {
  // --- Users & Roles ---
  'student':        GraduationCap,
  'graduation':     GraduationCap,
  'teacher':        PenTool,
  'teacher-pen':    PenTool,
  'admin':          UserCog,
  'users':          Users,

  // --- Auth & Navigation ---
  'login':          LogIn,
  'logout':         LogOut,
  'chevron-down':   ChevronDown,
  'chevron-right':  ChevronRight,
  'chevron-up':     ChevronUp,
  'menu':           Menu,
  'close':          X,
  'search':         Search,
  'arrow-right':    ArrowRight,

  // --- Visibility ---
  'eye':            Eye,
  'eye-off':        EyeOff,

  // --- Actions ---
  'add':            PlusCircle,
  'plus':           Plus,
  'view':           Eye,
  'download':       Download,
  'copy':           Copy,

  // --- Content ---
  'document':       FileText,
  'book':           BookOpen,
  'book-check':     BookOpenCheck,
  'report':         BarChart3,
  'questionnaire':  ClipboardList,
  'message':        MessageSquareText,

  // --- Admin & Dashboard ---
  'settings':       Settings,
  'dashboard':      LayoutDashboard,
  'stats':          BarChart3,
  'score':          BarChart2,
  'target':         Target,
  'trending':       TrendingUp,

  // --- Status & Alerts ---
  'alert':          AlertCircle,
  'empty':          CircleSlash,
  'success':        CheckCircle,
  'info':           Info,

  // --- Security ---
  'security':       ShieldCheck,
  'shield':         ShieldCheck,
  'compliance':     ShieldCheck,

  // --- Exam structure ---
  'exam':           FileText,
  'exam-folder':    Folder,
  'folder':         Folder,
  'folder-open':    FolderOpen,
  'result':         Target,

  // --- Quick actions (ExamOverview) ---
  'identification': ScanSearch,
  'correctors':     Users,
  'scale':          Ruler,
  'copies':         Copy,
  'calendar':       Calendar,
  'tag':            Tag,
  'user':           User,
  'check':          CheckCircle2,
  'back':           ChevronRight,

  // ─── Backend ExamType compatibility aliases ───────────────────────
  'graduation-cap': GraduationCap,
  'graduation_cap': GraduationCap,
  'school':         School,
  'book-open':      BookOpen,
  'book_open':      BookOpen,
  'book-open-check': BookOpenCheck,
  'file-text':      FileText,
  'file_text':      FileText,
  'calculator':     Calculator,
  'flask':          FlaskConical,
  'flask-conical':  FlaskConical,
  'beaker':         FlaskConical,
  'atom':           Atom,
  'microscope':     Microscope,
  'pen':            PenLine,
  'pen-line':       PenLine,
  'globe':          Globe,
  'music':          Music,
  'languages':      Languages,
  'language':       Languages,
  'history':        History,
  'compass':        Compass,
  'bar-chart':      BarChart2,
  'cpu':            Cpu,
  'paintbrush':     Paintbrush,
  'dumbbell':       Dumbbell,
}

/**
 * Resolve an icon name to its Lucide Vue component.
 * Falls back to FileText if the name is unknown.
 *
 * @param {string} name - Semantic icon name or backend icon string
 * @returns {import('vue').Component} Lucide Vue component
 */
export function resolveIcon(name) {
  if (!name) return FileText
  const key = name.toLowerCase().trim()
  return ICON_REGISTRY[key] || ICON_REGISTRY[name] || FileText
}

/**
 * Check if an icon name exists in the registry.
 * @param {string} name
 * @returns {boolean}
 */
export function hasIcon(name) {
  if (!name) return false
  const key = name.toLowerCase().trim()
  return key in ICON_REGISTRY || name in ICON_REGISTRY
}

export default ICON_REGISTRY
