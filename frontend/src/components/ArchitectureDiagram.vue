<template>
  <div class="w-full overflow-x-auto">
    <svg
      viewBox="0 0 900 420"
      class="w-full max-w-4xl mx-auto"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Architecture technique Korrigo PMF"
    >
      <defs>
        <marker id="arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <path d="M0,0 L8,3 L0,6" fill="#94a3b8" />
        </marker>
        <linearGradient id="gradBlue" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#dbeafe" />
          <stop offset="100%" stop-color="#bfdbfe" />
        </linearGradient>
        <linearGradient id="gradGreen" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#dcfce7" />
          <stop offset="100%" stop-color="#bbf7d0" />
        </linearGradient>
        <linearGradient id="gradPurple" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#f3e8ff" />
          <stop offset="100%" stop-color="#e9d5ff" />
        </linearGradient>
        <linearGradient id="gradOrange" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#fff7ed" />
          <stop offset="100%" stop-color="#fed7aa" />
        </linearGradient>
        <linearGradient id="gradRed" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#fef2f2" />
          <stop offset="100%" stop-color="#fecaca" />
        </linearGradient>
        <filter id="shadow" x="-4%" y="-4%" width="108%" height="112%">
          <feDropShadow dx="0" dy="2" stdDeviation="3" flood-opacity="0.08" />
        </filter>
      </defs>

      <!-- Background -->
      <rect width="900" height="420" fill="#f8fafc" rx="16" />

      <!-- Title -->
      <text x="450" y="32" text-anchor="middle" font-size="15" font-weight="700" fill="#1e293b">Architecture Technique — Korrigo PMF</text>

      <!-- ===== CLIENT LAYER ===== -->
      <rect x="30" y="52" width="840" height="80" rx="12" fill="url(#gradBlue)" stroke="#93c5fd" stroke-width="1" filter="url(#shadow)" />
      <text x="50" y="74" font-size="10" font-weight="600" fill="#1d4ed8" text-transform="uppercase" letter-spacing="1">CLIENT (NAVIGATEUR)</text>

      <!-- Vue.js -->
      <rect x="50" y="84" width="130" height="36" rx="8" fill="#fff" stroke="#93c5fd" stroke-width="1" />
      <text x="115" y="106" text-anchor="middle" font-size="11" font-weight="600" fill="#1e40af">Vue.js 3</text>
      <text x="115" y="117" text-anchor="middle" font-size="8" fill="#64748b">Composition API</text>

      <!-- Pinia -->
      <rect x="200" y="84" width="110" height="36" rx="8" fill="#fff" stroke="#93c5fd" stroke-width="1" />
      <text x="255" y="106" text-anchor="middle" font-size="11" font-weight="600" fill="#1e40af">Pinia</text>
      <text x="255" y="117" text-anchor="middle" font-size="8" fill="#64748b">State Management</text>

      <!-- Tailwind -->
      <rect x="330" y="84" width="110" height="36" rx="8" fill="#fff" stroke="#93c5fd" stroke-width="1" />
      <text x="385" y="106" text-anchor="middle" font-size="11" font-weight="600" fill="#1e40af">TailwindCSS 4</text>
      <text x="385" y="117" text-anchor="middle" font-size="8" fill="#64748b">Styling</text>

      <!-- Axios -->
      <rect x="460" y="84" width="110" height="36" rx="8" fill="#fff" stroke="#93c5fd" stroke-width="1" />
      <text x="515" y="106" text-anchor="middle" font-size="11" font-weight="600" fill="#1e40af">Axios</text>
      <text x="515" y="117" text-anchor="middle" font-size="8" fill="#64748b">API + CSRF</text>

      <!-- Canvas PDF -->
      <rect x="590" y="84" width="130" height="36" rx="8" fill="#fff" stroke="#93c5fd" stroke-width="1" />
      <text x="655" y="106" text-anchor="middle" font-size="11" font-weight="600" fill="#1e40af">Canvas Layer</text>
      <text x="655" y="117" text-anchor="middle" font-size="8" fill="#64748b">Annotations PDF</text>

      <!-- Vite -->
      <rect x="740" y="84" width="110" height="36" rx="8" fill="#fff" stroke="#93c5fd" stroke-width="1" />
      <text x="795" y="106" text-anchor="middle" font-size="11" font-weight="600" fill="#1e40af">Vite 5</text>
      <text x="795" y="117" text-anchor="middle" font-size="8" fill="#64748b">Build Tool</text>

      <!-- Arrow down -->
      <line x1="450" y1="132" x2="450" y2="158" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#arrow)" />
      <text x="465" y="150" font-size="8" fill="#94a3b8">HTTPS / REST API</text>

      <!-- ===== NGINX ===== -->
      <rect x="320" y="158" width="260" height="32" rx="8" fill="#fff" stroke="#cbd5e1" stroke-width="1" filter="url(#shadow)" />
      <text x="450" y="179" text-anchor="middle" font-size="11" font-weight="600" fill="#475569">Nginx — Reverse Proxy + TLS</text>

      <!-- Arrow down -->
      <line x1="450" y1="190" x2="450" y2="216" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#arrow)" />

      <!-- ===== BACKEND LAYER ===== -->
      <rect x="30" y="216" width="540" height="90" rx="12" fill="url(#gradGreen)" stroke="#86efac" stroke-width="1" filter="url(#shadow)" />
      <text x="50" y="238" font-size="10" font-weight="600" fill="#15803d" text-transform="uppercase" letter-spacing="1">BACKEND (PYTHON 3.11)</text>

      <!-- Django -->
      <rect x="50" y="248" width="130" height="46" rx="8" fill="#fff" stroke="#86efac" stroke-width="1" />
      <text x="115" y="268" text-anchor="middle" font-size="11" font-weight="600" fill="#166534">Django 4.2</text>
      <text x="115" y="280" text-anchor="middle" font-size="8" fill="#64748b">DRF + Sessions</text>
      <text x="115" y="290" text-anchor="middle" font-size="8" fill="#64748b">Rate Limiting</text>

      <!-- Celery -->
      <rect x="200" y="248" width="110" height="46" rx="8" fill="#fff" stroke="#86efac" stroke-width="1" />
      <text x="255" y="268" text-anchor="middle" font-size="11" font-weight="600" fill="#166534">Celery</text>
      <text x="255" y="280" text-anchor="middle" font-size="8" fill="#64748b">Tasks async</text>
      <text x="255" y="290" text-anchor="middle" font-size="8" fill="#64748b">PDF, OCR, LLM</text>

      <!-- Grading Service -->
      <rect x="330" y="248" width="120" height="46" rx="8" fill="#fff" stroke="#86efac" stroke-width="1" />
      <text x="390" y="268" text-anchor="middle" font-size="11" font-weight="600" fill="#166534">GradingService</text>
      <text x="390" y="280" text-anchor="middle" font-size="8" fill="#64748b">Barème, Scores</text>
      <text x="390" y="290" text-anchor="middle" font-size="8" fill="#64748b">Lock, Finalize</text>

      <!-- PDF Flattener -->
      <rect x="470" y="248" width="85" height="46" rx="8" fill="#fff" stroke="#86efac" stroke-width="1" />
      <text x="512" y="268" text-anchor="middle" font-size="10" font-weight="600" fill="#166534">PDF</text>
      <text x="512" y="280" text-anchor="middle" font-size="8" fill="#64748b">Flattener</text>
      <text x="512" y="290" text-anchor="middle" font-size="8" fill="#64748b">+ Bilan</text>

      <!-- ===== IA LAYER ===== -->
      <rect x="600" y="216" width="270" height="90" rx="12" fill="url(#gradPurple)" stroke="#c084fc" stroke-width="1" filter="url(#shadow)" />
      <text x="620" y="238" font-size="10" font-weight="600" fill="#7e22ce" text-transform="uppercase" letter-spacing="1">INTELLIGENCE ARTIFICIELLE</text>

      <!-- GPT-4o-mini -->
      <rect x="620" y="248" width="110" height="46" rx="8" fill="#fff" stroke="#c084fc" stroke-width="1" />
      <text x="675" y="268" text-anchor="middle" font-size="10" font-weight="600" fill="#7e22ce">GPT-4o-mini</text>
      <text x="675" y="280" text-anchor="middle" font-size="8" fill="#64748b">OCR Vision</text>
      <text x="675" y="290" text-anchor="middle" font-size="8" fill="#64748b">Identification</text>

      <!-- Ollama -->
      <rect x="745" y="248" width="110" height="46" rx="8" fill="#fff" stroke="#c084fc" stroke-width="1" />
      <text x="800" y="268" text-anchor="middle" font-size="10" font-weight="600" fill="#7e22ce">Ollama (Local)</text>
      <text x="800" y="280" text-anchor="middle" font-size="8" fill="#64748b">Bilans LLM</text>
      <text x="800" y="290" text-anchor="middle" font-size="8" fill="#64748b">qwen2.5:32b</text>

      <!-- Arrow Backend → IA -->
      <line x1="570" y1="275" x2="598" y2="275" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#arrow)" />

      <!-- Arrows down from backend -->
      <line x1="200" y1="306" x2="200" y2="340" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#arrow)" />
      <line x1="400" y1="306" x2="400" y2="340" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#arrow)" />
      <line x1="680" y1="306" x2="680" y2="340" stroke="#94a3b8" stroke-width="1.5" marker-end="url(#arrow)" />

      <!-- ===== DATA LAYER ===== -->
      <!-- PostgreSQL -->
      <rect x="100" y="340" width="180" height="56" rx="12" fill="url(#gradOrange)" stroke="#fdba74" stroke-width="1" filter="url(#shadow)" />
      <text x="190" y="364" text-anchor="middle" font-size="12" font-weight="700" fill="#c2410c">PostgreSQL 15</text>
      <text x="190" y="380" text-anchor="middle" font-size="9" fill="#9a3412">~20 modèles · 5 apps</text>
      <text x="190" y="392" text-anchor="middle" font-size="8" fill="#9a3412">Copies, Scores, AuditLog</text>

      <!-- Redis -->
      <rect x="320" y="340" width="160" height="56" rx="12" fill="url(#gradRed)" stroke="#fca5a5" stroke-width="1" filter="url(#shadow)" />
      <text x="400" y="364" text-anchor="middle" font-size="12" font-weight="700" fill="#dc2626">Redis</text>
      <text x="400" y="380" text-anchor="middle" font-size="9" fill="#b91c1c">Cache · Broker Celery</text>
      <text x="400" y="392" text-anchor="middle" font-size="8" fill="#b91c1c">Sessions · Rate Limit</text>

      <!-- Media storage -->
      <rect x="560" y="340" width="230" height="56" rx="12" fill="#f1f5f9" stroke="#cbd5e1" stroke-width="1" filter="url(#shadow)" />
      <text x="675" y="364" text-anchor="middle" font-size="12" font-weight="700" fill="#475569">Stockage Media</text>
      <text x="675" y="380" text-anchor="middle" font-size="9" fill="#64748b">PDFs source · Pages PNG</text>
      <text x="675" y="392" text-anchor="middle" font-size="8" fill="#64748b">PDFs finaux · Fascicules</text>

      <!-- Docker badge -->
      <rect x="750" y="404" width="120" height="14" rx="4" fill="#e0f2fe" />
      <text x="810" y="414" text-anchor="middle" font-size="8" font-weight="600" fill="#0369a1">Docker Compose Prod</text>
    </svg>
  </div>
</template>

<script setup>
</script>
