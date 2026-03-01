/**
 * KORRIGO — Script de récupération EXHAUSTIVE V3
 * Basé sur la V3 Claude Opus + améliorations V2
 * Hébergé sur le serveur pour une exécution sans friction.
 */

// UI helpers
function setStatus(cls, html) {
  var el = document.getElementById("status");
  el.className = cls;
  document.getElementById("statusText").innerHTML = html;
}
function setProgress(pct, step) {
  document.getElementById("progressWrap").classList.remove("hidden");
  // Use CSS classes instead of inline style (CSP blocks inline styles)
  var fill = document.getElementById("progressFill");
  // Remove all w* classes
  fill.className = fill.className.replace(/\bw\d+\b/g, "").trim();
  // Round to nearest 5
  var rounded = Math.round(pct / 5) * 5;
  if (rounded > 100) rounded = 100;
  fill.classList.add("w" + rounded);
  document.getElementById("stepText").textContent = step;
}
function showResults(results) {
  var wrap = document.getElementById("resultsWrap");
  wrap.classList.remove("hidden");
  wrap.innerHTML = results.map(function(r) {
    var cls = r.highlight ? "highlight" : (r.warning ? "warning" : "");
    return '<div class="result-row"><span class="result-label">' + r.label +
           '</span><span class="result-value ' + cls + '">' + r.value + '</span></div>';
  }).join("");
}

// Main extraction
async function startExtraction() {
  var btn = document.getElementById("startBtn");
  btn.disabled = true;
  btn.textContent = "Extraction en cours...";
  setStatus("running", "Extraction en cours, veuillez patienter...");
  setProgress(0, "Initialisation...");

  var T0 = Date.now();

  var result = {
    _version: "3.0",
    _date: new Date().toISOString(),
    _browser: navigator.userAgent,
    _url: window.location.href,
    _origin: window.location.origin,
    localStorage: {},
    sessionStorage: {},
    cookies: "",
    cacheStorage: {},
    indexedDB: {},
    serviceWorkers: [],
    performanceEntries: [],
    opfs: null,
    analyse: {
      scores_trouves: [],
      drafts_trouves: [],
      reponses_api_cachees: [],
      cles_uuid: [],
      cles_korrigo: []
    }
  };

  // ═══════════════════════════════════════════════════
  // 1. LOCAL STORAGE — dump complet
  // ═══════════════════════════════════════════════════
  setProgress(5, "1/7 — Lecture du localStorage...");
  try {
    for (var i = 0; i < localStorage.length; i++) {
      var k = localStorage.key(i);
      var v = localStorage.getItem(k);
      var parsed;
      try { parsed = JSON.parse(v); } catch(e) { parsed = v; }
      result.localStorage[k] = parsed;
      classifyEntry(k, parsed, result.analyse);
    }
  } catch(e) { result.localStorage._error = e.message; }

  // ═══════════════════════════════════════════════════
  // 2. SESSION STORAGE — dump complet
  // ═══════════════════════════════════════════════════
  setProgress(15, "2/7 — Lecture du sessionStorage...");
  try {
    for (var i = 0; i < sessionStorage.length; i++) {
      var k = sessionStorage.key(i);
      var v = sessionStorage.getItem(k);
      var parsed;
      try { parsed = JSON.parse(v); } catch(e) { parsed = v; }
      result.sessionStorage[k] = parsed;
      classifyEntry(k, parsed, result.analyse);
    }
  } catch(e) { result.sessionStorage._error = e.message; }

  // ═══════════════════════════════════════════════════
  // 3. COOKIES
  // ═══════════════════════════════════════════════════
  setProgress(20, "3/7 — Lecture des cookies...");
  try { result.cookies = document.cookie || "(aucun)"; } catch(e) {}

  // ═══════════════════════════════════════════════════
  // 4. CACHE STORAGE — lecture du contenu des réponses
  // ═══════════════════════════════════════════════════
  setProgress(25, "4/7 — Scan du Cache Storage (réponses HTTP)...");
  try {
    if (typeof caches !== "undefined") {
      var cacheNames = await caches.keys();
      for (var ci = 0; ci < cacheNames.length; ci++) {
        var name = cacheNames[ci];
        var cache = await caches.open(name);
        var requests = await cache.keys();
        var entries = [];

        for (var ri = 0; ri < requests.length; ri++) {
          var req = requests[ri];
          var entry = { url: req.url, method: req.method };
          try {
            var resp = await cache.match(req);
            if (resp) {
              entry.status = resp.status;
              entry.contentType = resp.headers.get("content-type") || "";
              entry.date = resp.headers.get("date") || "";

              var ct = entry.contentType.toLowerCase();
              if (ct.includes("json") || ct.includes("text")) {
                try {
                  var text = await resp.text();
                  if (text.length < 500000) {
                    var bodyParsed;
                    try { bodyParsed = JSON.parse(text); } catch(e) { bodyParsed = text; }
                    entry.body = bodyParsed;
                    entry.bodySize = text.length;
                    analyzeApiResponse(req.url, bodyParsed, result.analyse);
                  } else {
                    entry.body = "(tronque: " + text.length + " car.)";
                    entry.bodySize = text.length;
                  }
                } catch(e) { entry.bodyError = e.message; }
              } else {
                try {
                  var buf = await resp.clone().arrayBuffer();
                  entry.bodySize = buf.byteLength;
                  entry.body = "(binaire: " + buf.byteLength + " octets)";
                } catch(e) {}
              }
            }
          } catch(e) { entry.error = e.message; }
          entries.push(entry);
        }
        result.cacheStorage[name] = { count: entries.length, entries: entries };
      }
    }
  } catch(e) { result.cacheStorage._error = e.message; }

  // ═══════════════════════════════════════════════════
  // 5. INDEXED DB — extraction complète
  // ═══════════════════════════════════════════════════
  setProgress(50, "5/7 — Extraction IndexedDB...");
  try {
    if (indexedDB && indexedDB.databases) {
      var dbs = await indexedDB.databases();
      for (var di = 0; di < dbs.length; di++) {
        var dbInfo = dbs[di];
        try {
          var data = await extractFullIndexedDB(dbInfo.name);
          result.indexedDB[dbInfo.name] = { version: dbInfo.version, stores: data };
          // Analyse du contenu
          for (var storeName in data) {
            var store = data[storeName];
            if (store.data) {
              for (var si = 0; si < store.data.length; si++) {
                var record = store.data[si];
                if (record && typeof record === "object") {
                  var str = JSON.stringify(record).toLowerCase();
                  if (str.includes("score") || str.includes("annotation") || str.includes("korrigo") ||
                      str.includes("grading") || str.includes("copy") || str.includes("draft")) {
                    result.analyse.cles_korrigo.push({
                      source: "IndexedDB/" + dbInfo.name + "/" + storeName,
                      preview: JSON.stringify(record).substring(0, 500)
                    });
                  }
                }
              }
            }
          }
        } catch(e) {
          result.indexedDB[dbInfo.name] = { error: e.message };
        }
      }
    } else {
      // Firefox fallback
      var fallbackNames = ["korrigo", "korrigo-db", "workbox-expiration", "keyval-store"];
      for (var fi = 0; fi < fallbackNames.length; fi++) {
        try {
          var data = await extractFullIndexedDB(fallbackNames[fi]);
          if (data && Object.keys(data).length > 0) {
            result.indexedDB[fallbackNames[fi]] = { stores: data };
          }
        } catch(e) {}
      }
    }
  } catch(e) { result.indexedDB._error = e.message; }

  // ═══════════════════════════════════════════════════
  // 6. SERVICE WORKERS
  // ═══════════════════════════════════════════════════
  setProgress(75, "6/7 — Vérification Service Workers...");
  try {
    if (navigator.serviceWorker) {
      var regs = await navigator.serviceWorker.getRegistrations();
      for (var swi = 0; swi < regs.length; swi++) {
        var reg = regs[swi];
        result.serviceWorkers.push({
          scope: reg.scope,
          active: reg.active ? { scriptURL: reg.active.scriptURL, state: reg.active.state } : null,
          waiting: reg.waiting ? { scriptURL: reg.waiting.scriptURL } : null
        });
      }
    }
  } catch(e) {}

  // ═══════════════════════════════════════════════════
  // 7. PERFORMANCE API — URLs d'API visitées
  // ═══════════════════════════════════════════════════
  setProgress(85, "7/7 — Analyse des URLs API visitées...");
  try {
    var perfEntries = performance.getEntriesByType("resource");
    var apiEntries = perfEntries.filter(function(e) {
      var u = e.name.toLowerCase();
      return u.includes("/api/") || u.includes("korrigo") || u.includes("score") ||
             u.includes("annotation") || u.includes("grading") || u.includes("copies");
    });
    result.performanceEntries = apiEntries.map(function(e) {
      return { url: e.name, type: e.initiatorType, duration: Math.round(e.duration), size: e.transferSize || 0 };
    });
  } catch(e) {}

  // ═══════════════════════════════════════════════════
  // OPFS (Origin Private File System)
  // ═══════════════════════════════════════════════════
  setProgress(90, "Scan du File System...");
  try {
    if (navigator.storage && navigator.storage.getDirectory) {
      var root = await navigator.storage.getDirectory();
      var files = [];
      for await (var entry of root.values()) {
        if (entry.kind === "file") {
          var file = await entry.getFile();
          var fInfo = { name: entry.name, size: file.size, lastModified: file.lastModified };
          if (file.size < 100000) {
            try {
              var txt = await file.text();
              var fp; try { fp = JSON.parse(txt); } catch(e) { fp = txt; }
              fInfo.content = fp;
            } catch(e) {}
          }
          files.push(fInfo);
        } else {
          files.push({ name: entry.name, kind: "directory" });
        }
      }
      if (files.length > 0) result.opfs = files;
    }
  } catch(e) {}

  // ═══════════════════════════════════════════════════
  // RÉSUMÉ & TÉLÉCHARGEMENT
  // ═══════════════════════════════════════════════════
  setProgress(95, "Préparation du fichier...");

  var a = result.analyse;
  var nbScores = a.scores_trouves.length;
  var nbDrafts = a.drafts_trouves.length;
  var nbApi = a.reponses_api_cachees.length;
  var nbUuid = a.cles_uuid.length;
  var nbKorrigo = a.cles_korrigo.length;
  var nbLS = Object.keys(result.localStorage).length - (result.localStorage._error ? 1 : 0);
  var nbSS = Object.keys(result.sessionStorage).length - (result.sessionStorage._error ? 1 : 0);
  var nbCache = Object.keys(result.cacheStorage).length - (result.cacheStorage._error ? 1 : 0);
  var nbIDB = Object.keys(result.indexedDB).length - (result.indexedDB._error ? 1 : 0);
  var elapsed = ((Date.now() - T0) / 1000).toFixed(1);

  // Téléchargement
  var json = JSON.stringify(result, null, 2);
  var blob = new Blob([json], { type: "application/json" });
  var url = URL.createObjectURL(blob);
  var link = document.createElement("a");
  link.href = url;
  link.download = "korrigo_recovery_V3_" + new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19) + ".json";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);

  setProgress(100, "Terminé en " + elapsed + "s");

  // Afficher le résumé
  var totalData = nbScores + nbDrafts + nbApi;
  var resultsData = [
    { label: "Clés localStorage", value: nbLS },
    { label: "Clés sessionStorage", value: nbSS },
    { label: "Caches HTTP", value: nbCache },
    { label: "Bases IndexedDB", value: nbIDB },
    { label: "Service Workers", value: result.serviceWorkers.length },
    { label: "URLs API détectées", value: result.performanceEntries.length },
    { label: "Scores trouvés", value: nbScores, highlight: nbScores > 0 },
    { label: "Brouillons trouvés", value: nbDrafts, highlight: nbDrafts > 0 },
    { label: "Réponses API cachées", value: nbApi, highlight: nbApi > 0 },
    { label: "Clés avec UUID", value: nbUuid, warning: nbUuid > 0 },
    { label: "Clés liées à Korrigo", value: nbKorrigo, warning: nbKorrigo > 0 }
  ];
  showResults(resultsData);

  if (totalData > 0) {
    setStatus("success",
      "<strong>Données trouvées !</strong> " + nbScores + " score(s), " +
      nbDrafts + " brouillon(s), " + nbApi + " réponse(s) API cachée(s).<br><br>" +
      "Le fichier <strong>" + link.download + "</strong> a été téléchargé.<br>" +
      "<strong>Envoyez-le à Alaeddine sur WhatsApp maintenant.</strong>"
    );
  } else if (nbUuid > 0 || nbKorrigo > 0) {
    setStatus("empty",
      "<strong>Traces indirectes trouvées</strong> (" + nbUuid + " UUID, " +
      nbKorrigo + " clé(s) liées).<br><br>" +
      "Le fichier a été téléchargé. <strong>Envoyez-le quand même à Alaeddine</strong>, " +
      "il peut contenir des indices utiles."
    );
  } else {
    setStatus("empty",
      "<strong>Aucune donnée de correction trouvée</strong> sur ce navigateur.<br><br>" +
      "Vérifiez que c'est bien <strong>le même ordinateur</strong> et <strong>le même navigateur</strong> " +
      "(et profil) que celui utilisé pour corriger.<br><br>" +
      "Le fichier a quand même été téléchargé — <strong>envoyez-le à Alaeddine</strong> pour confirmation."
    );
  }

  btn.disabled = false;
  btn.textContent = "Relancer l'extraction";
}

// ═══════════════════════════════════════════════════
// FONCTIONS UTILITAIRES
// ═══════════════════════════════════════════════════

function classifyEntry(key, value, analyse) {
  var kl = key.toLowerCase();
  var uuidRe = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

  // Scores Korrigo
  if (key.startsWith("korrigo_scores_")) {
    var uuid = key.replace("korrigo_scores_", "");
    var total = 0, nb = 0;
    if (value && typeof value === "object") {
      var vals = Object.values(value);
      for (var i = 0; i < vals.length; i++) {
        var n = parseFloat(vals[i]);
        if (!isNaN(n)) { total += n; nb++; }
      }
    }
    analyse.scores_trouves.push({
      source: "localStorage/" + key,
      copy_uuid: uuid,
      nb_questions: nb,
      total: Math.round(total * 100) / 100,
      data: value
    });
  }
  // Brouillons d'annotation
  else if (key.startsWith("draft_")) {
    var info = { source: "localStorage/" + key, key: key };
    if (value && typeof value === "object") {
      info.content_preview = (value.content || (value.data && value.data.content) || "").substring(0, 200);
      info.page_index = value.page_index !== undefined ? value.page_index : (value.data ? value.data.page_index : undefined);
      info.saved_at = value.saved_at || value.timestamp;
      var match = key.match(uuidRe);
      if (match) info.copy_uuid = match[0];
      // Format TTL wrapper
      if (value.data && value.timestamp) {
        info.wrapped_format = true;
        info.timestamp = value.timestamp;
        info.ttl = value.ttl;
        info.inner_data = value.data;
      }
    }
    analyse.drafts_trouves.push(info);
  }
  // Clé contenant un UUID
  else if (uuidRe.test(key)) {
    analyse.cles_uuid.push({
      source: "localStorage/" + key,
      key: key,
      preview: JSON.stringify(value).substring(0, 300)
    });
  }

  // Mots-clés Korrigo
  var mots = ["korrigo", "grading", "annotation", "score", "remark", "exam", "corrector", "copy", "copie", "draft"];
  var isRelated = mots.some(function(m) { return kl.includes(m); });
  if (!isRelated && value && typeof value === "object") {
    var vs = JSON.stringify(value).toLowerCase();
    isRelated = mots.some(function(m) { return vs.includes(m); });
  }
  if (isRelated && !key.startsWith("korrigo_scores_") && !key.startsWith("draft_")) {
    analyse.cles_korrigo.push({
      source: "localStorage/" + key,
      preview: JSON.stringify(value).substring(0, 300)
    });
  }
}

function analyzeApiResponse(url, body, analyse) {
  var ul = url.toLowerCase();
  var isApi = ul.includes("/api/") || ul.includes("korrigo");
  if (!isApi) return;

  var type = "autre";
  if (ul.includes("score")) type = "scores";
  else if (ul.includes("annotation")) type = "annotations";
  else if (ul.includes("remark")) type = "remarques";
  else if (ul.includes("copies") || ul.includes("copy")) type = "copies";
  else if (ul.includes("exam")) type = "examens";
  else if (ul.includes("grading")) type = "correction";

  var entry = { url: url, type: type };

  if (Array.isArray(body)) {
    entry.count = body.length;
    entry.preview = JSON.stringify(body.slice(0, 2)).substring(0, 500);
  } else if (body && typeof body === "object") {
    entry.keys = Object.keys(body).slice(0, 20);
    if (body.scores_data || body.score || body.total) type = "scores";
    if (body.results && Array.isArray(body.results)) {
      entry.count = body.results.length;
      entry.preview = JSON.stringify(body.results.slice(0, 2)).substring(0, 500);
    }
  }

  // Extraire les scores des réponses API
  if (type === "scores" && body) {
    var scoreData = body.scores_data || body;
    if (typeof scoreData === "object" && !Array.isArray(scoreData)) {
      var total = 0, nb = 0;
      var vals = Object.values(scoreData);
      for (var i = 0; i < vals.length; i++) {
        var n = parseFloat(vals[i]);
        if (!isNaN(n)) { total += n; nb++; }
      }
      if (nb > 0) {
        var uuidMatch = url.match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i);
        analyse.scores_trouves.push({
          source: "CacheStorage/" + url,
          copy_uuid: uuidMatch ? uuidMatch[0] : null,
          nb_questions: nb,
          total: Math.round(total * 100) / 100,
          data: scoreData
        });
      }
    }
  }

  analyse.reponses_api_cachees.push(entry);
}

// Attach click listener (no inline onclick — CSP compliant)
document.addEventListener("DOMContentLoaded", function() {
  var btn = document.getElementById("startBtn");
  if (btn) btn.addEventListener("click", startExtraction);
});

function extractFullIndexedDB(dbName) {
  return new Promise(function(resolve, reject) {
    try {
      var req = indexedDB.open(dbName);
      req.onerror = function() { reject(new Error("Impossible d'ouvrir " + dbName)); };
      req.onsuccess = function(e) {
        var db = e.target.result;
        var storeNames = Array.from(db.objectStoreNames);
        var stores = {};
        var pending = storeNames.length;
        if (pending === 0) { db.close(); resolve(stores); return; }

        storeNames.forEach(function(storeName) {
          try {
            var tx = db.transaction(storeName, "readonly");
            var store = tx.objectStore(storeName);
            var getAll = store.getAll();
            getAll.onsuccess = function() {
              stores[storeName] = { count: getAll.result.length, data: getAll.result };
              if (--pending === 0) { db.close(); resolve(stores); }
            };
            getAll.onerror = function() {
              stores[storeName] = { error: "lecture echouee" };
              if (--pending === 0) { db.close(); resolve(stores); }
            };
          } catch(ex) {
            stores[storeName] = { error: ex.message };
            if (--pending === 0) { db.close(); resolve(stores); }
          }
        });
      };
    } catch(e) { reject(e); }
  });
}
