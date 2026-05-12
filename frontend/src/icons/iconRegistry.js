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
  ChevronLeft,
  Menu,
  X,
  Mail,
  Eye,
  EyeOff,
  Plus,
  PlusCircle,
  Search,
  ArrowRight,
  ArrowLeft,
  ArrowUpDown,
  ArrowUpRight,
  Send,
  RefreshCw,
  Clock,

  // Users & Roles
  GraduationCap,
  PenTool,
  PenLine,
  Settings,
  Users,
  ShieldCheck,
  UserPlus,
  UserCog,
  User,
  Key,
  Link,
  KeyRound,
  UserCheck,

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
  Upload,
  ScanSearch,
  Ruler,
  FileDown,
  Layers,
  Shuffle,
  FileCheck,
  Briefcase,

  // Data & Stats
  BarChart3,
  BarChart2,
  LayoutDashboard,
  Target,
  TrendingUp,
  TrendingDown,
  Award,

  // Communication
  MessageSquare,
  MessageSquareText,
  MessageCircle,

  // Alerts & Status
  AlertCircle,
  CircleSlash,
  CheckCircle,
  CheckCircle2,
  Info,
  AlertTriangle,
  XCircle,

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
  Building,
  Code,
  Server,

  // CorrectorDesk toolbar
  Highlighter,
  Star,
  Lock,
  Lightbulb,
  MoveHorizontal,
  Minus,
  Check,
  XIcon,
  Trash2,
  Scissors,
  Flag,
  Trophy,
  Sparkles,
  Brain,
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
  'user-plus':      UserPlus,

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
  'layers':         Layers,
  'mail':           Mail,

  // --- Visibility ---
  'eye':            Eye,
  'eye-off':        EyeOff,

  // --- Actions ---
  'add':            PlusCircle,
  'plus':           Plus,
  'view':           Eye,
  'download':       Download,
  'upload':         Upload,
  'copy':           Copy,
  'edit':           PenTool,
  'sparkles':       Sparkles,
  'brain':          Brain,

  // --- Content ---
  'document':       FileText,
  'book':           BookOpen,
  'book-check':     BookOpenCheck,
  'report':         BarChart3,
  'questionnaire':  ClipboardList,
  'clipboard':      ClipboardList,
  'message':        MessageSquareText,
  'message-square': MessageSquare,
  'message-circle': MessageCircle,

  // --- Admin & Dashboard ---
  'settings':       Settings,
  'dashboard':      LayoutDashboard,
  'stats':          BarChart3,
  'score':          BarChart2,
  'target':         Target,
  'trending-up':    TrendingUp,
  'trending-down':  TrendingDown,
  'trending':       TrendingUp,
  'bar-chart-3':    BarChart3,
  'clock':          Clock,

  // --- Status & Alerts ---
  'alert':          AlertCircle,
  'empty':          CircleSlash,
  'success':        CheckCircle,
  'refresh':        RefreshCw,
  'refresh-cw':     RefreshCw,
  'info':           Info,
  'check-circle-2': CheckCircle2,

  // --- Security ---
  'security':       ShieldCheck,
  'shield':         ShieldCheck,
  'compliance':     ShieldCheck,

  // --- Exam structure ---
  'exam':           FileText,
  'exam-folder':    Folder,
  'folder':         Folder,
  'folder-open':    FolderOpen,
  'plus':           Plus,
  'result':         Target,
  'award':          Award,
  'chart':          BarChart3,
  'building':       Building,
  'code':           Code,
  'server':         Server,
  'file-down':      FileDown,
  'arrow-up-down':  ArrowUpDown,

  // --- Quick actions (ExamOverview) ---
  'identification': ScanSearch,
  'correctors':     Users,
  'scale':          Ruler,
  'copies':         Copy,
  'calendar':       Calendar,
  'tag':            Tag,
  'user':           User,
  'key':            Key,
  'link':           Link,
  'reset':          Key,
  'check':          CheckCircle2,
  'back':           ChevronRight,
  'user-check':     UserCheck,
  'shuffle':        Shuffle,
  'file-check':     FileCheck,
  'briefcase':      Briefcase,
  'key-round':      KeyRound,

  // --- CorrectorDesk toolbar ---
  'comment':        MessageCircle,
  'highlight':      Highlighter,
  'error-mark':     XCircle,
  'star':           Star,
  'lock':           Lock,
  'warning':        AlertTriangle,
  'arrow-left':     ArrowLeft,
  'arrow-up-right': ArrowUpRight,
  'send':           Send,
  'chevron-left':   ChevronLeft,
  'lightbulb':      Lightbulb,
  'fit-width':      MoveHorizontal,
  'zoom-in':        Plus,
  'zoom-out':       Minus,
  'check-mark':     Check,
  'x-mark':         XIcon,
  'delete':         Trash2,
  'trash':          Trash2,
  'cut':            Scissors,
  'flag':           Flag,
  'medal':          Trophy,
  'trophy':         Trophy,
  'pen-tool':       PenTool,

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
