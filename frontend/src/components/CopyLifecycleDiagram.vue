<template>
  <div class="w-full overflow-x-auto">
    <svg
      viewBox="0 0 880 300"
      class="w-full max-w-4xl mx-auto"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Cycle de vie d'une copie dans Korrigo PMF"
    >
      <defs>
        <marker id="arrowLC" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <path d="M0,0 L8,3 L0,6" fill="#64748b" />
        </marker>
        <filter id="shadowLC" x="-4%" y="-4%" width="108%" height="116%">
          <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.1" />
        </filter>
      </defs>

      <!-- Background -->
      <rect width="880" height="300" fill="#f8fafc" rx="16" />

      <!-- Title -->
      <text x="440" y="30" text-anchor="middle" font-size="15" font-weight="700" fill="#1e293b">Cycle de Vie d'une Copie — Machine d'États</text>

      <!-- ===== STATE 1: STAGING ===== -->
      <g transform="translate(40, 60)">
        <rect width="130" height="100" rx="14" fill="#fef3c7" stroke="#f59e0b" stroke-width="2" filter="url(#shadowLC)" />
        <circle cx="65" cy="28" r="16" fill="#fbbf24" opacity="0.3" />
        <text x="65" y="33" text-anchor="middle" font-size="16">📥</text>
        <text x="65" y="58" text-anchor="middle" font-size="11" font-weight="700" fill="#92400e">STAGING</text>
        <text x="65" y="72" text-anchor="middle" font-size="8" fill="#a16207">Import PDF</text>
        <text x="65" y="83" text-anchor="middle" font-size="8" fill="#a16207">Split + Rasterize</text>
        <text x="65" y="94" text-anchor="middle" font-size="7" fill="#ca8a04">Admin</text>
      </g>

      <!-- Arrow 1→2 -->
      <line x1="170" y1="110" x2="210" y2="110" stroke="#64748b" stroke-width="2" marker-end="url(#arrowLC)" />
      <text x="190" y="102" text-anchor="middle" font-size="7" fill="#64748b">OCR</text>

      <!-- ===== STATE 2: PENDING_IDENTIFICATION ===== -->
      <g transform="translate(212, 60)">
        <rect width="130" height="100" rx="14" fill="#fed7aa" stroke="#f97316" stroke-width="2" filter="url(#shadowLC)" />
        <circle cx="65" cy="28" r="16" fill="#fb923c" opacity="0.3" />
        <text x="65" y="33" text-anchor="middle" font-size="16">🔍</text>
        <text x="65" y="55" text-anchor="middle" font-size="10" font-weight="700" fill="#9a3412">PENDING</text>
        <text x="65" y="66" text-anchor="middle" font-size="10" font-weight="700" fill="#9a3412">IDENTIFICATION</text>
        <text x="65" y="80" text-anchor="middle" font-size="8" fill="#c2410c">OCR GPT-4o-mini</text>
        <text x="65" y="91" text-anchor="middle" font-size="8" fill="#c2410c">Liaison Copie↔Élève</text>
      </g>

      <!-- Arrow 2→3 -->
      <line x1="342" y1="110" x2="382" y2="110" stroke="#64748b" stroke-width="2" marker-end="url(#arrowLC)" />
      <text x="362" y="102" text-anchor="middle" font-size="7" fill="#64748b">Validé</text>

      <!-- ===== STATE 3: READY ===== -->
      <g transform="translate(384, 60)">
        <rect width="130" height="100" rx="14" fill="#dbeafe" stroke="#3b82f6" stroke-width="2" filter="url(#shadowLC)" />
        <circle cx="65" cy="28" r="16" fill="#60a5fa" opacity="0.3" />
        <text x="65" y="33" text-anchor="middle" font-size="16">✅</text>
        <text x="65" y="58" text-anchor="middle" font-size="11" font-weight="700" fill="#1e40af">READY</text>
        <text x="65" y="72" text-anchor="middle" font-size="8" fill="#2563eb">Anonymisée</text>
        <text x="65" y="83" text-anchor="middle" font-size="8" fill="#2563eb">Prête à corriger</text>
        <text x="65" y="94" text-anchor="middle" font-size="7" fill="#3b82f6">Secrétariat</text>
      </g>

      <!-- Arrow 3→4 -->
      <line x1="514" y1="110" x2="554" y2="110" stroke="#64748b" stroke-width="2" marker-end="url(#arrowLC)" />
      <text x="534" y="102" text-anchor="middle" font-size="7" fill="#64748b">Lock</text>

      <!-- ===== STATE 4: LOCKED ===== -->
      <g transform="translate(556, 60)">
        <rect width="130" height="100" rx="14" fill="#e9d5ff" stroke="#a855f7" stroke-width="2" filter="url(#shadowLC)" />
        <circle cx="65" cy="28" r="16" fill="#a78bfa" opacity="0.3" />
        <text x="65" y="33" text-anchor="middle" font-size="16">🔒</text>
        <text x="65" y="58" text-anchor="middle" font-size="11" font-weight="700" fill="#6b21a8">LOCKED</text>
        <text x="65" y="72" text-anchor="middle" font-size="8" fill="#7e22ce">Correction en cours</text>
        <text x="65" y="83" text-anchor="middle" font-size="8" fill="#7e22ce">Heartbeat 30s</text>
        <text x="65" y="94" text-anchor="middle" font-size="7" fill="#a855f7">Enseignant</text>
      </g>

      <!-- Arrow 4→5 -->
      <line x1="686" y1="110" x2="726" y2="110" stroke="#64748b" stroke-width="2" marker-end="url(#arrowLC)" />
      <text x="706" y="102" text-anchor="middle" font-size="7" fill="#64748b">Finalize</text>

      <!-- ===== STATE 5: GRADED ===== -->
      <g transform="translate(728, 60)">
        <rect width="120" height="100" rx="14" fill="#dcfce7" stroke="#22c55e" stroke-width="2" filter="url(#shadowLC)" />
        <circle cx="60" cy="28" r="16" fill="#4ade80" opacity="0.3" />
        <text x="60" y="33" text-anchor="middle" font-size="16">🎓</text>
        <text x="60" y="58" text-anchor="middle" font-size="11" font-weight="700" fill="#15803d">GRADED</text>
        <text x="60" y="72" text-anchor="middle" font-size="8" fill="#16a34a">Note finale</text>
        <text x="60" y="83" text-anchor="middle" font-size="8" fill="#16a34a">PDF + Bilan IA</text>
        <text x="60" y="94" text-anchor="middle" font-size="7" fill="#22c55e">Élève consulte</text>
      </g>

      <!-- Return arrow: LOCKED → READY (unlock) -->
      <path d="M621,160 L621,195 L449,195 L449,160" fill="none" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="5,3" marker-end="url(#arrowLC)" />
      <text x="535" y="210" text-anchor="middle" font-size="8" fill="#94a3b8">Déverrouillage (timeout 30 min ou manuel)</text>

      <!-- ===== LEGEND ===== -->
      <g transform="translate(40, 240)">
        <rect width="800" height="48" rx="10" fill="#fff" stroke="#e2e8f0" stroke-width="1" />
        <text x="20" y="22" font-size="9" font-weight="600" fill="#475569">LÉGENDE :</text>

        <rect x="100" y="10" width="12" height="12" rx="3" fill="#fef3c7" stroke="#f59e0b" stroke-width="1" />
        <text x="118" y="21" font-size="8" fill="#64748b">Import</text>

        <rect x="170" y="10" width="12" height="12" rx="3" fill="#fed7aa" stroke="#f97316" stroke-width="1" />
        <text x="188" y="21" font-size="8" fill="#64748b">Identification</text>

        <rect x="270" y="10" width="12" height="12" rx="3" fill="#dbeafe" stroke="#3b82f6" stroke-width="1" />
        <text x="288" y="21" font-size="8" fill="#64748b">Prête</text>

        <rect x="330" y="10" width="12" height="12" rx="3" fill="#e9d5ff" stroke="#a855f7" stroke-width="1" />
        <text x="348" y="21" font-size="8" fill="#64748b">Verrouillée</text>

        <rect x="420" y="10" width="12" height="12" rx="3" fill="#dcfce7" stroke="#22c55e" stroke-width="1" />
        <text x="438" y="21" font-size="8" fill="#64748b">Corrigée</text>

        <line x1="500" y1="16" x2="530" y2="16" stroke="#94a3b8" stroke-width="1.5" stroke-dasharray="5,3" />
        <text x="538" y="21" font-size="8" fill="#64748b">Retour possible</text>

        <line x1="620" y1="16" x2="650" y2="16" stroke="#64748b" stroke-width="2" marker-end="url(#arrowLC)" />
        <text x="658" y="21" font-size="8" fill="#64748b">Transition</text>

        <text x="20" y="40" font-size="8" fill="#94a3b8">5 statuts · Verrouillage pessimiste avec heartbeat · Autosave dual-layer (localStorage + serveur) · Anonymisation dès READY</text>
      </g>
    </svg>
  </div>
</template>

<script setup>
</script>
