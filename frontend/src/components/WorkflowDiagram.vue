<template>
  <div class="w-full overflow-x-auto">
    <svg
      viewBox="0 0 880 340"
      class="w-full max-w-4xl mx-auto"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Workflow complet de correction Korrigo PMF"
    >
      <defs>
        <marker id="arrowWF" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <path d="M0,0 L8,3 L0,6" fill="#64748b" />
        </marker>
        <filter id="shadowWF" x="-4%" y="-4%" width="108%" height="116%">
          <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.08" />
        </filter>
      </defs>

      <!-- Background -->
      <rect width="880" height="340" fill="#f8fafc" rx="16" />

      <!-- Title -->
      <text x="440" y="28" text-anchor="middle" font-size="14" font-weight="700" fill="#1e293b">Workflow Complet — Du Scan Papier à la Consultation Élève</text>

      <!-- ===== ROW 1: ADMIN PHASE ===== -->
      <text x="40" y="60" font-size="9" font-weight="600" fill="#dc2626" letter-spacing="0.5">PHASE ADMIN</text>

      <!-- Step 1: Upload Scan -->
      <g transform="translate(40, 68)">
        <rect width="120" height="70" rx="10" fill="#fff" stroke="#3b82f6" stroke-width="1.5" filter="url(#shadowWF)" />
        <rect width="120" height="4" rx="2" fill="#3b82f6" />
        <text x="60" y="30" text-anchor="middle" font-size="18">📄</text>
        <text x="60" y="46" text-anchor="middle" font-size="9" font-weight="700" fill="#1e3a5f">1. Upload Scans</text>
        <text x="60" y="58" text-anchor="middle" font-size="7" fill="#64748b">PDF batch A3/A4</text>
        <text x="60" y="67" text-anchor="middle" font-size="7" fill="#64748b">106 + 103 copies</text>
      </g>

      <!-- Arrow -->
      <line x1="160" y1="103" x2="185" y2="103" stroke="#64748b" stroke-width="1.5" marker-end="url(#arrowWF)" />

      <!-- Step 2: Split & Rasterize -->
      <g transform="translate(187, 68)">
        <rect width="120" height="70" rx="10" fill="#fff" stroke="#8b5cf6" stroke-width="1.5" filter="url(#shadowWF)" />
        <rect width="120" height="4" rx="2" fill="#8b5cf6" />
        <text x="60" y="30" text-anchor="middle" font-size="18">✂️</text>
        <text x="60" y="46" text-anchor="middle" font-size="9" font-weight="700" fill="#4c1d95">2. Split & Rasterize</text>
        <text x="60" y="58" text-anchor="middle" font-size="7" fill="#64748b">A3→2×A4 auto</text>
        <text x="60" y="67" text-anchor="middle" font-size="7" fill="#64748b">Booklets + PNG</text>
      </g>

      <!-- Arrow -->
      <line x1="307" y1="103" x2="332" y2="103" stroke="#64748b" stroke-width="1.5" marker-end="url(#arrowWF)" />

      <!-- Step 3: Barème -->
      <g transform="translate(334, 68)">
        <rect width="120" height="70" rx="10" fill="#fff" stroke="#f59e0b" stroke-width="1.5" filter="url(#shadowWF)" />
        <rect width="120" height="4" rx="2" fill="#f59e0b" />
        <text x="60" y="30" text-anchor="middle" font-size="18">📊</text>
        <text x="60" y="46" text-anchor="middle" font-size="9" font-weight="700" fill="#92400e">3. Barème</text>
        <text x="60" y="58" text-anchor="middle" font-size="7" fill="#64748b">Exercice→Question</text>
        <text x="60" y="67" text-anchor="middle" font-size="7" fill="#64748b">Structure hiérarchique</text>
      </g>

      <!-- Arrow -->
      <line x1="454" y1="103" x2="479" y2="103" stroke="#64748b" stroke-width="1.5" marker-end="url(#arrowWF)" />

      <!-- Step 4: Dispatch -->
      <g transform="translate(481, 68)">
        <rect width="120" height="70" rx="10" fill="#fff" stroke="#ef4444" stroke-width="1.5" filter="url(#shadowWF)" />
        <rect width="120" height="4" rx="2" fill="#ef4444" />
        <text x="60" y="30" text-anchor="middle" font-size="18">👥</text>
        <text x="60" y="46" text-anchor="middle" font-size="9" font-weight="700" fill="#991b1b">4. Dispatch</text>
        <text x="60" y="58" text-anchor="middle" font-size="7" fill="#64748b">Round-robin équitable</text>
        <text x="60" y="67" text-anchor="middle" font-size="7" fill="#64748b">8 correcteurs, 2 jurys</text>
      </g>

      <!-- ===== ROW 2: IDENTIFICATION + CORRECTION ===== -->
      <!-- Arrow down from Dispatch -->
      <line x1="541" y1="138" x2="541" y2="168" stroke="#64748b" stroke-width="1.5" marker-end="url(#arrowWF)" />

      <text x="40" y="178" font-size="9" font-weight="600" fill="#ea580c" letter-spacing="0.5">PHASE SECRÉTARIAT + CORRECTION</text>

      <!-- Step 5: OCR Identification -->
      <g transform="translate(40, 186)">
        <rect width="150" height="70" rx="10" fill="#fff" stroke="#f97316" stroke-width="1.5" filter="url(#shadowWF)" />
        <rect width="150" height="4" rx="2" fill="#f97316" />
        <text x="75" y="30" text-anchor="middle" font-size="18">🤖</text>
        <text x="75" y="46" text-anchor="middle" font-size="9" font-weight="700" fill="#9a3412">5. OCR GPT-4o-mini</text>
        <text x="75" y="58" text-anchor="middle" font-size="7" fill="#64748b">Lecture noms manuscrits</text>
        <text x="75" y="67" text-anchor="middle" font-size="7" fill="#64748b">Fuzzy matching élèves CSV</text>
      </g>

      <!-- Arrow -->
      <line x1="190" y1="221" x2="215" y2="221" stroke="#64748b" stroke-width="1.5" marker-end="url(#arrowWF)" />

      <!-- Step 6: Anonymisation -->
      <g transform="translate(217, 186)">
        <rect width="140" height="70" rx="10" fill="#fff" stroke="#a855f7" stroke-width="1.5" filter="url(#shadowWF)" />
        <rect width="140" height="4" rx="2" fill="#a855f7" />
        <text x="70" y="30" text-anchor="middle" font-size="18">🕶️</text>
        <text x="70" y="46" text-anchor="middle" font-size="9" font-weight="700" fill="#6b21a8">6. Anonymisation</text>
        <text x="70" y="58" text-anchor="middle" font-size="7" fill="#64748b">Masquage en-tête</text>
        <text x="70" y="67" text-anchor="middle" font-size="7" fill="#64748b">N° anonymat unique</text>
      </g>

      <!-- Arrow -->
      <line x1="357" y1="221" x2="382" y2="221" stroke="#64748b" stroke-width="1.5" marker-end="url(#arrowWF)" />

      <!-- Step 7: Correction -->
      <g transform="translate(384, 186)">
        <rect width="160" height="70" rx="10" fill="#fff" stroke="#0ea5e9" stroke-width="1.5" filter="url(#shadowWF)" />
        <rect width="160" height="4" rx="2" fill="#0ea5e9" />
        <text x="80" y="30" text-anchor="middle" font-size="18">✍️</text>
        <text x="80" y="46" text-anchor="middle" font-size="9" font-weight="700" fill="#0c4a6e">7. Correction Numérique</text>
        <text x="80" y="58" text-anchor="middle" font-size="7" fill="#64748b">Annotations PDF + barème</text>
        <text x="80" y="67" text-anchor="middle" font-size="7" fill="#64748b">Verrouillage + Autosave</text>
      </g>

      <!-- Arrow -->
      <line x1="544" y1="221" x2="569" y2="221" stroke="#64748b" stroke-width="1.5" marker-end="url(#arrowWF)" />

      <!-- Step 8: Bilan IA -->
      <g transform="translate(571, 186)">
        <rect width="130" height="70" rx="10" fill="#fff" stroke="#22c55e" stroke-width="1.5" filter="url(#shadowWF)" />
        <rect width="130" height="4" rx="2" fill="#22c55e" />
        <text x="65" y="30" text-anchor="middle" font-size="18">✨</text>
        <text x="65" y="46" text-anchor="middle" font-size="9" font-weight="700" fill="#14532d">8. Bilan IA</text>
        <text x="65" y="58" text-anchor="middle" font-size="7" fill="#64748b">Ollama qwen2.5:32b</text>
        <text x="65" y="67" text-anchor="middle" font-size="7" fill="#64748b">Résumé personnalisé</text>
      </g>

      <!-- Arrow -->
      <line x1="701" y1="221" x2="726" y2="221" stroke="#64748b" stroke-width="1.5" marker-end="url(#arrowWF)" />

      <!-- Step 9: Restitution -->
      <g transform="translate(728, 186)">
        <rect width="120" height="70" rx="10" fill="#fff" stroke="#22c55e" stroke-width="2" filter="url(#shadowWF)" />
        <rect width="120" height="4" rx="2" fill="#22c55e" />
        <text x="60" y="30" text-anchor="middle" font-size="18">🎓</text>
        <text x="60" y="46" text-anchor="middle" font-size="9" font-weight="700" fill="#14532d">9. Restitution</text>
        <text x="60" y="58" text-anchor="middle" font-size="7" fill="#64748b">Portail Élève</text>
        <text x="60" y="67" text-anchor="middle" font-size="7" fill="#64748b">Export CSV Pronote</text>
      </g>

      <!-- ===== BOTTOM: KEY METRICS ===== -->
      <g transform="translate(40, 278)">
        <rect width="800" height="42" rx="10" fill="#fff" stroke="#e2e8f0" stroke-width="1" />
        <text x="20" y="18" font-size="9" font-weight="700" fill="#475569">EN PRODUCTION :</text>
        <text x="140" y="18" font-size="8" fill="#64748b">209 copies · 2 examens (BB_J1 + BB_J2) · 8 correcteurs · 209 élèves terminale maths</text>
        <text x="20" y="33" font-size="9" font-weight="700" fill="#475569">GARANTIES :</text>
        <text x="140" y="33" font-size="8" fill="#64748b">100% anonymisé · Correction humaine uniquement · Aucune IA dans la notation · Traçabilité complète (GradingEvent)</text>
      </g>
    </svg>
  </div>
</template>

<script setup>
</script>
