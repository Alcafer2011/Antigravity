"use strict";

/**
 * modelMirror — il deposito dei TUOI modelli, per l'avvio veloce.
 *
 * ★ 2026-07-30 — Il collo di bottiglia dell'accensione non è la GPU: è lo
 * scaricamento dei GGUF (minuti, ogni volta, e dipende dal fatto che la repo di
 * bartowski resti su e pubblica). Con un mirror su un TUO repo HuggingFace
 * privato: scarichi una volta, poi tutte le piattaforme tirano da lì.
 *
 * Serve un HF_TOKEN con permesso di SCRITTURA (quello che hai adesso potrebbe
 * essere in sola lettura: il controllo qui sotto lo dice invece di fallire a
 * metà upload). Repo privato: i modelli abliterated restano cosa tua.
 *
 * Il mirror NON è obbligatorio: senza, si scarica dalla repo originale come
 * adesso. Quando c'è, notebookTemplate lo usa da solo (campo `mirror`).
 */

const https = require("https");
const b = require("./platforms/base");

const API = "huggingface.co";

function _api(percorso, o = {}) {
    return new Promise((resolve) => {
        const tok = b.env("HF_TOKEN");
        const req = https.request({
            host: API, path: percorso, method: o.method || "GET", timeout: o.timeoutMs || 20000,
            headers: Object.assign({
                "User-Agent": "Antigravity",
                "Accept": "application/json"
            }, tok ? { Authorization: "Bearer " + tok } : {}, o.headers || {})
        }, (res) => {
            let d = "";
            res.on("data", c => { if (d.length < 500000) d += c; });
            res.on("end", () => {
                let j = null; try { j = JSON.parse(d); } catch (_) {}
                resolve({ status: res.statusCode, json: j, testo: d.slice(0, 2000) });
            });
        });
        req.on("timeout", () => { req.destroy(); resolve({ status: 0, errore: "timeout" }); });
        req.on("error", (e) => resolve({ status: 0, errore: e.message }));
        if (o.corpo) req.write(typeof o.corpo === "string" ? o.corpo : JSON.stringify(o.corpo));
        req.end();
    });
}

/**
 * Il token che hai può scrivere? Domanda decisiva: un token in sola lettura
 * fallisce solo a upload iniziato, dopo aver scaricato decine di GB.
 */
async function statoToken() {
    const tok = b.env("HF_TOKEN");
    if (!tok) return { ok: false, presente: false, messaggio: "Manca HF_TOKEN nel .env. Serve un token con permesso di scrittura: https://huggingface.co/settings/tokens" };
    const r = await _api("/api/whoami-v2");
    if (r.status !== 200) return { ok: false, presente: true, valido: false, messaggio: "HF_TOKEN rifiutato da HuggingFace (" + r.status + "). Rigeneralo su https://huggingface.co/settings/tokens" };
    const auth = (r.json && r.json.auth) || {};
    const acc = auth.accessToken || {};
    const scrive = /write/i.test(acc.role || "") || (Array.isArray(acc.fineGrained && acc.fineGrained.scoped)
        && acc.fineGrained.scoped.some(s => (s.permissions || []).some(p => /write/i.test(p))));
    return {
        ok: !!scrive, presente: true, valido: true, scrive: !!scrive,
        utente: (r.json && r.json.name) || null, ruolo: acc.role || "(fine-grained)",
        messaggio: scrive
            ? "HF_TOKEN valido e con permesso di scrittura: posso creare il mirror."
            : "HF_TOKEN valido ma in SOLA LETTURA: il mirror non si può creare. Genera un token 'write' su https://huggingface.co/settings/tokens e sostituiscilo nel .env (l'upload fallirebbe comunque, ma dopo aver scaricato decine di GB)."
    };
}

/** Crea (se manca) il repo privato che farà da deposito. */
async function creaRepo(nome) {
    const t = await statoToken();
    if (!t.ok) return { ok: false, messaggio: t.messaggio };
    const repo = nome || (t.utente + "/antigravity-modelli");
    const [utente, nomeRepo] = repo.split("/");
    if (!utente || !nomeRepo) return { ok: false, messaggio: "Nome repo non valido (serve utente/nome): " + repo };

    const esiste = await _api("/api/models/" + repo);
    if (esiste.status === 200) {
        b.setEnv("HF_MIRROR_REPO", repo);
        return { ok: true, repo, gia: true, messaggio: "Il deposito esiste già: " + repo };
    }
    const r = await _api("/api/repos/create", {
        method: "POST", headers: { "Content-Type": "application/json" },
        corpo: { name: nomeRepo, organization: utente === t.utente ? null : utente, type: "model", private: true }
    });
    if (r.status !== 200 && r.status !== 201) {
        return { ok: false, messaggio: "Creazione repo fallita (" + r.status + "): " + r.testo };
    }
    b.setEnv("HF_MIRROR_REPO", repo);
    return { ok: true, repo, messaggio: "Deposito privato creato: " + repo + " (salvato in HF_MIRROR_REPO)" };
}

/**
 * Copia un GGUF dalla repo originale al tuo deposito. La copia la fa la
 * piattaforma GPU (che ha banda vera), non il tuo PC: qui si genera il comando
 * da eseguire nel notebook/container.
 *
 * Questo è deliberato: scaricare 20 GB sul PC di casa per ricaricarli su HF
 * sarebbe la strada lenta. Sulla GPU ci mette pochi minuti.
 */
function comandoCopia(repoSorgente, quant, repoDeposito) {
    const dep = repoDeposito || b.env("HF_MIRROR_REPO");
    if (!dep) return { ok: false, messaggio: "Nessun deposito configurato: crea prima il mirror (HF_MIRROR_REPO)." };
    const righe = [
        "pip install -q huggingface_hub",
        "python - <<'PY'",
        "import os, glob",
        "from huggingface_hub import snapshot_download, HfApi",
        "src = " + JSON.stringify(repoSorgente),
        "dst = " + JSON.stringify(dep),
        "quant = " + JSON.stringify(quant),
        "p = snapshot_download(src, allow_patterns=[f'*{quant}*.gguf'])",
        "api = HfApi(token=os.environ['HF_TOKEN'])",
        "for f in glob.glob(p + '/**/*.gguf', recursive=True):",
        "    print('carico', f)",
        "    api.upload_file(path_or_fileobj=f, path_in_repo=os.path.basename(f), repo_id=dst, repo_type='model')",
        "print('mirror pronto:', dst)",
        "PY"
    ].join("\n");
    return { ok: true, deposito: dep, comando: righe,
        nota: "Da eseguire UNA volta sulla piattaforma GPU (ha la banda). Serve HF_TOKEN con scrittura nell'ambiente." };
}

/** Stato compatto per il pannello. */
async function stato() {
    const t = await statoToken();
    const repo = b.env("HF_MIRROR_REPO");
    let presente = null;
    if (repo) { const r = await _api("/api/models/" + repo); presente = r.status === 200; }
    return {
        token: t, deposito: repo || null, depositoEsiste: presente,
        attivo: !!(repo && presente && t.ok),
        effetto: repo && presente
            ? "I notebook generati scaricano da " + repo + ": avvio in decine di secondi invece di minuti."
            : "Nessun deposito: i modelli si scaricano dalla repo originale a ogni avvio (minuti)."
    };
}

module.exports = { statoToken, creaRepo, comandoCopia, stato };
