/**
 * KORRIGO — Script de récupération TOTALE des données navigateur (V2)
 * 
 * Ce script capture TOUT le contenu du localStorage et sessionStorage
 * sans aucun filtre, pour ne perdre aucune donnée même si les UUIDs
 * des copies ou des utilisateurs ont changé après la reconstitution.
 * 
 * INSTRUCTIONS :
 * 1. Ouvrir le navigateur (Chrome/Edge/Firefox) sur l'ORDINATEUR
 *    où vous avez corrigé les copies (même machine, même navigateur).
 * 2. Aller sur https://korrigo.labomaths.tn
 *    (Le localStorage est lié au domaine, il FAUT être sur le site.)
 *    NB : L'app ne supprime pas automatiquement les données au chargement,
 *    c'est sans risque.
 * 3. Appuyer sur F12 (ou clic droit -> Inspecter).
 * 4. Aller dans l'onglet "Console".
 * 5. COLLER ce script en entier et appuyer sur Entrée.
 * 6. Un fichier JSON se téléchargera automatiquement avec TOUT ce qui
 *    est stocké dans le navigateur pour ce domaine.
 * 7. Envoyer ce fichier à Alaeddine immédiatement.
 * 
 * Le script capture TOUT : anciens UUIDs, nouveaux UUIDs, tous les
 * user IDs, tous les scores, tous les brouillons, sans aucun filtre.
 */

(async function() {
    console.log("=== KORRIGO RECOVERY V2 — Extraction totale ===");
    console.log("Debut:", new Date().toISOString());

    const result = {
        version: "2.0",
        extraction_date: new Date().toISOString(),
        browser: navigator.userAgent,
        current_url: window.location.href,
        localstorage_dump: [],
        sessionstorage_dump: [],
        cookies: "",
        indexeddb_databases: [],
        cache_storage_keys: [],
        analysis: {
            drafts: [],
            scores: [],
            uuid_keys: [],
            korrigo_related: []
        }
    };

    // =====================================================
    // 1. DUMP COMPLET DU LOCALSTORAGE (toutes les clés)
    // =====================================================
    console.log("\n[1/5] Extraction localStorage...");
    try {
        for (let i = 0; i < localStorage.length; i++) {
            const key = localStorage.key(i);
            const raw = localStorage.getItem(key);
            let parsed = null;
            let parseOk = false;
            try {
                parsed = JSON.parse(raw);
                parseOk = true;
            } catch(e) {
                parsed = null;
            }

            const entry = {
                key: key,
                value: parseOk ? parsed : raw,
                is_json: parseOk,
                size_bytes: raw ? raw.length : 0
            };
            result.localstorage_dump.push(entry);

            // Analyse automatique : classifier la clé
            classifyEntry(key, parseOk ? parsed : raw, parseOk, result.analysis);
        }
        console.log("  localStorage: " + localStorage.length + " cle(s) trouvee(s)");
    } catch(e) {
        console.warn("  localStorage inaccessible:", e.message);
    }

    // =====================================================
    // 2. DUMP COMPLET DU SESSIONSTORAGE
    // =====================================================
    console.log("\n[2/5] Extraction sessionStorage...");
    try {
        for (let i = 0; i < sessionStorage.length; i++) {
            const key = sessionStorage.key(i);
            const raw = sessionStorage.getItem(key);
            let parsed = null;
            let parseOk = false;
            try {
                parsed = JSON.parse(raw);
                parseOk = true;
            } catch(e) {
                parsed = null;
            }
            result.sessionstorage_dump.push({
                key: key,
                value: parseOk ? parsed : raw,
                is_json: parseOk,
                size_bytes: raw ? raw.length : 0
            });
        }
        console.log("  sessionStorage: " + sessionStorage.length + " cle(s)");
    } catch(e) {
        console.warn("  sessionStorage inaccessible:", e.message);
    }

    // =====================================================
    // 3. COOKIES
    // =====================================================
    console.log("\n[3/5] Extraction cookies...");
    try {
        result.cookies = document.cookie || "(aucun cookie)";
        console.log("  Cookies: " + (document.cookie ? document.cookie.length + " caracteres" : "aucun"));
    } catch(e) {
        result.cookies = "inaccessible: " + e.message;
    }

    // =====================================================
    // 4. INDEXEDDB — lister les bases disponibles
    // =====================================================
    console.log("\n[4/5] Scan IndexedDB...");
    try {
        if (indexedDB && indexedDB.databases) {
            const dbs = await indexedDB.databases();
            result.indexeddb_databases = dbs.map(function(db) {
                return { name: db.name, version: db.version };
            });
            console.log("  IndexedDB: " + dbs.length + " base(s)");
            // Dump each database content
            for (const dbInfo of dbs) {
                try {
                    const dbData = await extractIndexedDB(dbInfo.name);
                    result.indexeddb_databases.push({
                        name: dbInfo.name,
                        version: dbInfo.version,
                        stores: dbData
                    });
                } catch(e) {
                    console.warn("  Impossible de lire IDB " + dbInfo.name + ":", e.message);
                }
            }
        } else {
            console.log("  IndexedDB.databases() non supporte, tentative manuelle...");
        }
    } catch(e) {
        console.warn("  IndexedDB scan echoue:", e.message);
    }

    // =====================================================
    // 5. CACHE STORAGE — lister les caches
    // =====================================================
    console.log("\n[5/5] Scan CacheStorage...");
    try {
        if (caches) {
            const keys = await caches.keys();
            result.cache_storage_keys = keys;
            console.log("  Caches: " + keys.length + " cache(s)");
        }
    } catch(e) {
        console.warn("  CacheStorage inaccessible:", e.message);
    }

    // =====================================================
    // RAPPORT CONSOLE
    // =====================================================
    const a = result.analysis;
    console.log("\n========== RAPPORT ==========");
    console.log("Total localStorage: " + result.localstorage_dump.length + " cles");
    console.log("Total sessionStorage: " + result.sessionstorage_dump.length + " cles");
    console.log("Drafts (brouillons annotation): " + a.drafts.length);
    console.log("Scores (notes par question): " + a.scores.length);
    console.log("Cles contenant un UUID: " + a.uuid_keys.length);
    console.log("Cles liees a Korrigo: " + a.korrigo_related.length);

    if (a.drafts.length > 0) {
        console.log("\n--- DRAFTS TROUVES ---");
        a.drafts.forEach(function(d) {
            var info = d.key;
            if (d.content_preview) info += " | " + d.content_preview;
            console.log("  " + info);
        });
    }

    if (a.scores.length > 0) {
        console.log("\n--- SCORES TROUVES ---");
        a.scores.forEach(function(s) {
            var nbQ = s.nb_questions || 0;
            var total = s.total_points || "?";
            console.log("  " + s.key + " | " + nbQ + " questions | total=" + total);
        });
    }

    if (a.drafts.length === 0 && a.scores.length === 0 && a.uuid_keys.length === 0) {
        console.log("\n*** AUCUNE DONNEE KORRIGO TROUVEE SUR CE DOMAINE ***");
        console.log("Verifiez que vous etes bien sur le meme ordinateur");
        console.log("et le meme navigateur que celui utilise pour corriger.");
    }

    // =====================================================
    // TELECHARGEMENT AUTOMATIQUE
    // =====================================================
    var jsonStr = JSON.stringify(result, null, 2);
    var blob = new Blob([jsonStr], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = "korrigo_recovery_TOTAL_" + new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19) + ".json";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    console.log("\n>>> Fichier telecharge: " + link.download);
    console.log(">>> ENVOYEZ CE FICHIER A ALAEDDINE <<<");
    console.log("=== FIN ===");

    // =====================================================
    // FONCTIONS UTILITAIRES
    // =====================================================

    /**
     * Classifie automatiquement une clé localStorage
     */
    function classifyEntry(key, value, isJson, analysis) {
        var keyLower = key.toLowerCase();

        // Pattern UUID : 8-4-4-4-12 hex
        var uuidPattern = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

        // 1. Drafts : clé commence par "draft_"
        if (key.startsWith("draft_")) {
            var draftInfo = { key: key };
            if (isJson && value) {
                draftInfo.type = value.type || null;
                draftInfo.content_preview = (value.content || "").substring(0, 100);
                draftInfo.page_index = value.page_index;
                draftInfo.saved_at = value.saved_at;
                draftInfo.rect = value.rect || null;
                // Extraire le copy UUID de la clé
                var parts = key.split("_");
                if (parts.length >= 2) {
                    var possibleUuid = parts.slice(1, -1).join("_");
                    if (uuidPattern.test(possibleUuid)) {
                        draftInfo.copy_uuid = possibleUuid;
                    }
                }
                // Extraire user ID de la clé
                var lastPart = parts[parts.length - 1];
                if (/^\d+$/.test(lastPart)) {
                    draftInfo.user_id = parseInt(lastPart);
                }
            }
            // Aussi vérifier le format TTL de storage.js : { data: ..., timestamp: ..., ttl: ... }
            if (isJson && value && value.data && value.timestamp) {
                draftInfo.wrapped_format = true;
                draftInfo.timestamp = value.timestamp;
                draftInfo.ttl = value.ttl;
                draftInfo.inner_data = value.data;
                if (value.data.content) {
                    draftInfo.content_preview = (value.data.content || "").substring(0, 100);
                }
            }
            analysis.drafts.push(draftInfo);
        }
        // 2. Scores : clé commence par "korrigo_scores_"
        else if (key.startsWith("korrigo_scores_")) {
            var scoreInfo = { key: key };
            var copyUuid = key.replace("korrigo_scores_", "");
            scoreInfo.copy_uuid = copyUuid;
            if (isJson && value && typeof value === "object") {
                var keys = Object.keys(value);
                scoreInfo.nb_questions = keys.length;
                var total = 0;
                keys.forEach(function(k) {
                    var v = parseFloat(value[k]);
                    if (!isNaN(v)) total += v;
                });
                scoreInfo.total_points = Math.round(total * 100) / 100;
                scoreInfo.questions = value;
            }
            analysis.scores.push(scoreInfo);
        }
        // 3. Toute clé contenant un UUID (potentiellement lié à une copie)
        else if (uuidPattern.test(key)) {
            analysis.uuid_keys.push({
                key: key,
                value_preview: isJson ? JSON.stringify(value).substring(0, 200) : String(value).substring(0, 200)
            });
        }

        // 4. Clés liées à Korrigo (mots-clés dans la clé ou la valeur)
        var korrigoKeywords = ["korrigo", "grading", "annotation", "copy", "copie",
                               "score", "remark", "draft", "exam", "corrector", "barème"];
        var isRelated = korrigoKeywords.some(function(kw) { return keyLower.includes(kw); });
        if (!isRelated && isJson && value) {
            // Chercher aussi dans la valeur
            var valStr = JSON.stringify(value).toLowerCase();
            isRelated = korrigoKeywords.some(function(kw) { return valStr.includes(kw); });
        }
        if (isRelated && !key.startsWith("draft_") && !key.startsWith("korrigo_scores_")) {
            analysis.korrigo_related.push({
                key: key,
                value_preview: isJson ? JSON.stringify(value).substring(0, 300) : String(value).substring(0, 300)
            });
        }
    }

    /**
     * Extrait le contenu complet d'une base IndexedDB
     */
    function extractIndexedDB(dbName) {
        return new Promise(function(resolve, reject) {
            try {
                var request = indexedDB.open(dbName);
                request.onerror = function() { reject(new Error("Cannot open " + dbName)); };
                request.onsuccess = function(event) {
                    var db = event.target.result;
                    var storeNames = Array.from(db.objectStoreNames);
                    var stores = {};
                    var pending = storeNames.length;
                    if (pending === 0) { db.close(); resolve(stores); return; }

                    storeNames.forEach(function(storeName) {
                        try {
                            var tx = db.transaction(storeName, "readonly");
                            var store = tx.objectStore(storeName);
                            var getAllReq = store.getAll();
                            getAllReq.onsuccess = function() {
                                stores[storeName] = {
                                    count: getAllReq.result.length,
                                    data: getAllReq.result.slice(0, 100) // max 100 entries per store
                                };
                                pending--;
                                if (pending === 0) { db.close(); resolve(stores); }
                            };
                            getAllReq.onerror = function() {
                                stores[storeName] = { error: "read failed" };
                                pending--;
                                if (pending === 0) { db.close(); resolve(stores); }
                            };
                        } catch(e) {
                            stores[storeName] = { error: e.message };
                            pending--;
                            if (pending === 0) { db.close(); resolve(stores); }
                        }
                    });
                };
            } catch(e) {
                reject(e);
            }
        });
    }

})();
