<template>
  <div class="w-full overflow-x-auto">
    <svg
      viewBox="0 0 700 260"
      class="w-full max-w-3xl mx-auto"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Cycle de vie d'une copie dans Korrigo PMF"
    >
      <defs>
        <marker
          id="arrowLC"
          markerWidth="8"
          markerHeight="6"
          refX="8"
          refY="3"
          orient="auto"
        >
          <path
            d="M0,0 L8,3 L0,6"
            fill="#64748b"
          />
        </marker>
        <filter
          id="shadowLC"
          x="-4%"
          y="-4%"
          width="108%"
          height="116%"
        >
          <feDropShadow
            dx="0"
            dy="2"
            stdDeviation="3"
            flood-opacity="0.1"
          />
        </filter>
      </defs>

      <!-- Background -->
      <rect
        width="700"
        height="260"
        fill="#f8fafc"
        rx="16"
      />

      <!-- Title -->
      <text
        x="350"
        y="30"
        text-anchor="middle"
        font-size="15"
        font-weight="700"
        fill="#1e293b"
      >Cycle de Vie d'une Copie — Machine d'États</text>

      <!-- ===== STATE 1: READY ===== -->
      <g transform="translate(50, 60)">
        <rect
          width="150"
          height="110"
          rx="14"
          fill="#dbeafe"
          stroke="#3b82f6"
          stroke-width="2"
          filter="url(#shadowLC)"
        />
        <circle
          cx="75"
          cy="30"
          r="16"
          fill="#60a5fa"
          opacity="0.3"
        />
        <text
          x="75"
          y="35"
          text-anchor="middle"
          font-size="16"
        >✅</text>
        <text
          x="75"
          y="62"
          text-anchor="middle"
          font-size="11"
          font-weight="700"
          fill="#1e40af"
        >READY</text>
        <text
          x="75"
          y="76"
          text-anchor="middle"
          font-size="8"
          fill="#2563eb"
        >Prête à corriger</text>
        <text
          x="75"
          y="88"
          text-anchor="middle"
          font-size="8"
          fill="#2563eb"
        >Anonymisée</text>
        <text
          x="75"
          y="100"
          text-anchor="middle"
          font-size="7"
          fill="#3b82f6"
        >Secrétariat</text>
      </g>

      <!-- Arrow 1→2 -->
      <line
        x1="200"
        y1="115"
        x2="255"
        y2="115"
        stroke="#64748b"
        stroke-width="2"
        marker-end="url(#arrowLC)"
      />
      <text
        x="227"
        y="107"
        text-anchor="middle"
        font-size="7"
        fill="#64748b"
      >Lock</text>

      <!-- ===== STATE 2: IN_PROGRESS ===== -->
      <g transform="translate(257, 60)">
        <rect
          width="150"
          height="110"
          rx="14"
          fill="#FEF3C7"
          stroke="#F59E0B"
          stroke-width="2"
          filter="url(#shadowLC)"
        />
        <circle
          cx="75"
          cy="30"
          r="16"
          fill="#fbbf24"
          opacity="0.3"
        />
        <text
          x="75"
          y="35"
          text-anchor="middle"
          font-size="16"
        >✏️</text>
        <text
          x="75"
          y="62"
          text-anchor="middle"
          font-size="11"
          font-weight="700"
          fill="#92400e"
        >IN_PROGRESS</text>
        <text
          x="75"
          y="76"
          text-anchor="middle"
          font-size="8"
          fill="#b45309"
        >Correction en cours</text>
        <text
          x="75"
          y="88"
          text-anchor="middle"
          font-size="8"
          fill="#b45309"
        >Heartbeat 30s</text>
        <text
          x="75"
          y="100"
          text-anchor="middle"
          font-size="7"
          fill="#F59E0B"
        >Enseignant</text>
      </g>

      <!-- Arrow 2→3 -->
      <line
        x1="407"
        y1="115"
        x2="462"
        y2="115"
        stroke="#64748b"
        stroke-width="2"
        marker-end="url(#arrowLC)"
      />
      <text
        x="434"
        y="107"
        text-anchor="middle"
        font-size="7"
        fill="#64748b"
      >Finaliser</text>

      <!-- ===== STATE 3: FINALIZED ===== -->
      <g transform="translate(464, 60)">
        <rect
          width="150"
          height="110"
          rx="14"
          fill="#D1FAE5"
          stroke="#10B981"
          stroke-width="2"
          filter="url(#shadowLC)"
        />
        <circle
          cx="75"
          cy="30"
          r="16"
          fill="#4ade80"
          opacity="0.3"
        />
        <text
          x="75"
          y="35"
          text-anchor="middle"
          font-size="16"
        >🎓</text>
        <text
          x="75"
          y="62"
          text-anchor="middle"
          font-size="11"
          font-weight="700"
          fill="#065f46"
        >FINALIZED</text>
        <text
          x="75"
          y="76"
          text-anchor="middle"
          font-size="8"
          fill="#047857"
        >Note finale</text>
        <text
          x="75"
          y="88"
          text-anchor="middle"
          font-size="8"
          fill="#047857"
        >PDF + Bilan IA</text>
        <text
          x="75"
          y="100"
          text-anchor="middle"
          font-size="7"
          fill="#10B981"
        >Élève consulte</text>
      </g>

      <!-- Return arrow: IN_PROGRESS → READY (unlock) -->
      <path
        d="M332,170 L332,205 L125,205 L125,170"
        fill="none"
        stroke="#94a3b8"
        stroke-width="1.5"
        stroke-dasharray="5,3"
        marker-end="url(#arrowLC)"
      />
      <text
        x="228"
        y="220"
        text-anchor="middle"
        font-size="8"
        fill="#94a3b8"
      >Déverrouillage (timeout 10 min ou manuel)</text>

      <!-- ===== LEGEND ===== -->
      <g transform="translate(40, 240)">
        <rect
          width="620"
          height="14"
          rx="6"
          fill="none"
        />
        <rect
          x="0"
          y="0"
          width="12"
          height="12"
          rx="3"
          fill="#dbeafe"
          stroke="#3b82f6"
          stroke-width="1"
        />
        <text
          x="18"
          y="10"
          font-size="8"
          fill="#64748b"
        >Prête</text>

        <rect
          x="70"
          y="0"
          width="12"
          height="12"
          rx="3"
          fill="#FEF3C7"
          stroke="#F59E0B"
          stroke-width="1"
        />
        <text
          x="88"
          y="10"
          font-size="8"
          fill="#64748b"
        >En cours</text>

        <rect
          x="160"
          y="0"
          width="12"
          height="12"
          rx="3"
          fill="#D1FAE5"
          stroke="#10B981"
          stroke-width="1"
        />
        <text
          x="178"
          y="10"
          font-size="8"
          fill="#64748b"
        >Finalisée</text>

        <line
          x1="250"
          y1="6"
          x2="280"
          y2="6"
          stroke="#94a3b8"
          stroke-width="1.5"
          stroke-dasharray="5,3"
        />
        <text
          x="288"
          y="10"
          font-size="8"
          fill="#64748b"
        >Retour possible</text>

        <line
          x1="390"
          y1="6"
          x2="420"
          y2="6"
          stroke="#64748b"
          stroke-width="2"
          marker-end="url(#arrowLC)"
        />
        <text
          x="428"
          y="10"
          font-size="8"
          fill="#64748b"
        >Transition</text>

        <text
          x="0"
          y="28"
          font-size="7"
          fill="#94a3b8"
        >3 statuts · Verrouillage pessimiste avec heartbeat · Autosave dual-layer · Anonymisation dès READY</text>
      </g>
    </svg>
  </div>
</template>

<script setup>
</script>
