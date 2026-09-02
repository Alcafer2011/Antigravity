"use strict";
/**
 * ultrahd8k — SEZIONE DEDICATA all'apparecchio TV di casa: «8K Ultra HD».
 *
 * ★ 2026-09-02 — Prima di oggi Antigravity non sapeva NULLA di quell'apparecchio:
 * ogni volta bisognava ridirgli l'indirizzo, ritrovare adb, ricapire dov'erano
 * le cartelle di Kodi. Qui quella conoscenza diventa PERMANENTE e diventa uno
 * strumento, esattamente come `ghidra` per il reverse engineering.
 *
 * COS'È L'APPARECCHIO (censito dal vivo il 02/09/2026)
 *   Transpeed 8K618-T — SoC Allwinner, scheda "apollo-p17"
 *   Android 12, ABI **armeabi-v7a a 32 bit** (NIENTE arm64: gli APK a 64 bit
 *     NON si installano — è l'errore in cui si cade per primo)
 *   ADB su TCP: 192.168.1.114:5555 (per rete, niente cavo)
 *   ROOTATO: /system/xbin/su dà uid=0. Serve DAVVERO, perché da Android 11
 *     /sdcard/Android/data/ è chiusa allo shell adb: senza root la cartella
 *     di Kodi non si legge e non si scrive.
 *   Kodi 21.2 "Omega", pacchetto org.xbmc.kodi
 *   Attaccato via HDMI a una TV Hisense; CEC attivo lato box.
 *
 * DUE VIE PER COMANDARLO, e servono entrambe:
 *   1) ADB — il muscolo. Installa APK, scrive file, preme tasti, fa screenshot.
 *      Funziona sempre, anche a Kodi spento.
 *   2) JSON-RPC di Kodi (HTTP su 8080) — la precisione. Legge e scrive le
 *      IMPOSTAZIONI per id, elenca e abilita add-on, fa partire i video, manda
 *      notifiche a schermo. Di fabbrica è SPENTO: si accende con
 *      op="api_accendi", che patcha guisettings.xml via root (a Kodi FERMO,
 *      altrimenti Kodi lo riscrive sopra quando esce) e riavvia.
 *
 * FILOSOFIA DEL TOOL — vedi GHIDRA_TOOL in nativeAgent: un solo strumento con
 * `op`, non venti strumenti quasi identici. I modelli piccoli e quelli
 * uncensored (tool-calling spesso debole) affogano nelle liste lunghe.
 */

const fs = require("fs");
const path = require("path");
const os = require("os");
const http = require("http");
const https = require("https");
const zlib = require("zlib");
const { spawn, spawnSync } = require("child_process");

const CONFIG = path.join(__dirname, ".8k-ultra-hd.json");

/** Valori di partenza: quelli censiti dal vivo. Il file di config li può cambiare. */
const DEFAULT = {
    indirizzo: "192.168.1.114:5555",
    adb: "C:\\rpi_backup\\platform-tools\\adb.exe",
    pacchettoKodi: "org.xbmc.kodi",
    kodiHome: "/sdcard/Android/data/org.xbmc.kodi/files/.kodi",
    apiPorta: 8080,
    apiUtente: "kodi",
    apiPassword: "",
    ramoRepo: "omega",
    modello: "Transpeed 8K618-T (Allwinner apollo-p17)",
    abi: "armeabi-v7a",
    note: "Android 12, rootato (/system/xbin/su). Kodi 21.2. TV Hisense via HDMI-CEC."
};

const MIRROR = "https://mirrors.kodi.tv/addons";

function leggiConfig() {
    try {
        const j = JSON.parse(fs.readFileSync(CONFIG, "utf8"));
        return Object.assign({}, DEFAULT, j);
    } catch (_) { return Object.assign({}, DEFAULT); }
}
function scriviConfig(c) {
    try { fs.writeFileSync(CONFIG, JSON.stringify(c, null, 2), "utf8"); return true; }
    catch (_) { return false; }
}

/** Le virgolette dentro un `su -c '…'`: fonte infinita di bug. */
function quotaShell(s) { return "'" + String(s).replace(/'/g, "'\\''") + "'"; }

class UltraHD8K {
    constructor(opts = {}) {
        this.cfg = leggiConfig();
        if (opts.indirizzo) this.cfg.indirizzo = opts.indirizzo;
        this._connesso = false;
        this.tmp = opts.tmp || path.join(os.tmpdir(), "ultrahd8k");
        try { fs.mkdirSync(this.tmp, { recursive: true }); } catch (_) {}
    }

    // ────────────────────────────────────────────────────────── ADB base ──

    /** Trova adb: config → PATH → posti soliti. Se lo trova altrove lo salva. */
    _adbPath() {
        const c = this.cfg.adb;
        if (c && fs.existsSync(c)) return c;
        try {
            const prova = spawnSync("where", ["adb"], { encoding: "utf8", shell: true });
            if (prova.status === 0) {
                const p = String(prova.stdout || "").split(/\r?\n/)[0].trim();
                if (p && fs.existsSync(p)) { this.cfg.adb = p; scriviConfig(this.cfg); return p; }
            }
        } catch (_) {}
        const cand = [
            "C:\\rpi_backup\\platform-tools\\adb.exe",
            path.join(os.homedir(), "AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe"),
            "C:\\platform-tools\\adb.exe"
        ];
        for (const p of cand) if (fs.existsSync(p)) { this.cfg.adb = p; scriviConfig(this.cfg); return p; }
        return null;
    }

    _adb(args, { timeout = 60000, binario = false } = {}) {
        return new Promise((risolvi) => {
            const exe = this._adbPath();
            if (!exe) return risolvi({ ok: false, out: "ADB_MANCANTE: non trovo adb.exe. Scarica le platform-tools Android e indica il percorso in " + CONFIG });
            const p = spawn(exe, args, { windowsHide: true });
            const pezzi = [];
            let chiuso = false;
            const t = setTimeout(() => { if (!chiuso) { try { p.kill(); } catch (_) {} } }, timeout);
            p.stdout.on("data", d => pezzi.push(d));
            p.stderr.on("data", d => pezzi.push(d));
            p.on("error", e => { chiuso = true; clearTimeout(t); risolvi({ ok: false, out: "ADB_ERRORE: " + e.message }); });
            p.on("close", code => {
                chiuso = true; clearTimeout(t);
                const buf = Buffer.concat(pezzi);
                risolvi({ ok: code === 0, code, out: binario ? buf : buf.toString("utf8").trim(), buf });
            });
        });
    }

    /** Si assicura che il box sia agganciato; ricollega da solo se è caduto. */
    async connetti(forza = false) {
        if (this._connesso && !forza) return { ok: true };
        const b = this.cfg.indirizzo;
        await this._adb(["connect", b], { timeout: 15000 });
        const d = await this._adb(["devices", "-l"], { timeout: 15000 });
        const riga = String(d.out || "").split(/\r?\n/).find(r => r.startsWith(b));
        if (!riga || !/\bdevice\b/.test(riga)) {
            this._connesso = false;
            return {
                ok: false,
                out: "BOX_IRRAGGIUNGIBILE su " + b + ".\nControlla: (1) apparecchio acceso e sulla stessa rete; "
                    + "(2) debug ADB via rete attivo (Android → Opzioni sviluppatore). "
                    + "Se è cambiato l'IP, correggilo con op='configura'.\nDettaglio adb: " + d.out
            };
        }
        this._connesso = true;
        return { ok: true, riga };
    }

    /** Comando shell sul box. root:true passa da `su`: indispensabile per la cartella Kodi. */
    async sh(cmd, { root = false, timeout = 60000 } = {}) {
        const c = await this.connetti();
        if (!c.ok) return c.out;
        const vero = root ? "su -c " + quotaShell(cmd) : cmd;
        const r = await this._adb(["-s", this.cfg.indirizzo, "shell", vero], { timeout });
        return r.out;
    }

    // ───────────────────────────────────────────────────────────── Stato ──

    async stato() {
        const c = await this.connetti(true);
        if (!c.ok) return c.out;
        const props = await this.sh("getprop ro.product.model; getprop ro.product.device; "
            + "getprop ro.build.version.release; getprop ro.product.cpu.abilist");
        const [modello, scheda, android, abi] = String(props).split(/\r?\n/).map(s => s.trim());
        const pid = await this.sh("pidof " + this.cfg.pacchettoKodi + " || echo -");
        const ver = await this.sh("dumpsys package " + this.cfg.pacchettoKodi + " | grep versionName | head -1");
        const root = await this.sh("id", { root: true });
        const haRoot = /uid=0/.test(root);
        let api = false;
        try { await this.rpc("JSONRPC.Version", {}, { timeout: 4000 }); api = true; } catch (_) {}
        const libero = await this.sh("df -h /data | tail -1");

        return [
            "APPARECCHIO 8K ULTRA HD — stato",
            "  indirizzo ADB : " + this.cfg.indirizzo + "  (collegato)",
            "  modello       : " + (modello || "?") + "   scheda: " + (scheda || "?"),
            "  Android       : " + (android || "?") + "   ABI: " + (abi || "?"),
            "  root (su)     : " + (haRoot ? "SÌ (uid=0) — accesso completo" : "NO — la cartella di Kodi resterà illeggibile"),
            "  Kodi          : " + (String(ver).replace(/.*versionName=/, "").trim() || "?")
                + "  —  " + (pid.trim() === "-" ? "SPENTO" : "in esecuzione (pid " + pid.trim() + ")"),
            "  API JSON-RPC  : " + (api ? "ATTIVA su porta " + this.cfg.apiPorta : "SPENTA — accendila con op='api_accendi'"),
            "  spazio /data  : " + String(libero).trim(),
            "",
            "Promemoria: ABI a 32 bit — gli APK arm64 NON si installano su questo box."
        ].join("\n");
    }

    async configura(campi) {
        Object.assign(this.cfg, campi || {});
        scriviConfig(this.cfg);
        this._connesso = false;
        return "Configurazione aggiornata in " + CONFIG + ":\n" + JSON.stringify(this.cfg, null, 2);
    }

    // ─────────────────────────────────────────────── Occhi e mani sul box ──

    /** Screenshot portato sul PC: il modello può GUARDARLO con read_image. */
    async schermo() {
        const c = await this.connetti();
        if (!c.ok) return c.out;
        const remoto = "/sdcard/.ag_screen.png";
        await this.sh("screencap -p " + remoto);
        const locale = path.join(this.tmp, "schermo-" + Date.now() + ".png");
        const r = await this._adb(["-s", this.cfg.indirizzo, "pull", remoto, locale], { timeout: 60000 });
        await this.sh("rm -f " + remoto);
        if (!fs.existsSync(locale)) return "SCREENSHOT_FALLITO: " + r.out;
        const kb = Math.round(fs.statSync(locale).size / 1024);
        return "Schermata catturata (" + kb + " KB): " + locale
            + "\nAprila con lo strumento read_image per vedere cosa c'è sulla TV in questo momento.";
    }

    /**
     * Tasti del telecomando. Nomi comodi o codici Android.
     * Più tasti separati da spazio: "giu giu ok" naviga davvero un menu.
     */
    async tasto(sequenza, ripeti = 1) {
        const MAPPA = {
            su: 19, giu: 20, sinistra: 21, destra: 22, ok: 23, invio: 66,
            up: 19, down: 20, left: 21, right: 22, enter: 23, select: 23,
            indietro: 4, back: 4, home: 3, menu: 82, info: 165,
            play: 85, pausa: 85, stop: 86, avanti: 87, precedente: 88,
            volume_su: 24, volume_giu: 25, muto: 164, accendi: 26, power: 26,
            cancella: 67, ricerca: 84
        };
        const nomi = String(sequenza || "").trim().split(/\s+/).filter(Boolean);
        if (!nomi.length) return "Indica almeno un tasto. Disponibili: " + Object.keys(MAPPA).join(", ");
        const codici = [];
        for (const n of nomi) {
            const k = MAPPA[n.toLowerCase()] !== undefined ? MAPPA[n.toLowerCase()] : (/^\d+$/.test(n) ? Number(n) : null);
            if (k === null) return "Tasto sconosciuto: «" + n + "». Disponibili: " + Object.keys(MAPPA).join(", ");
            codici.push(k);
        }
        const giri = Math.max(1, Math.min(50, Number(ripeti) || 1));
        // Un solo `input keyevent` con più codici: molto più veloce di N chiamate adb.
        for (let i = 0; i < giri; i++) await this.sh("input keyevent " + codici.join(" "));
        return "Inviati: " + nomi.join(" → ") + (giri > 1 ? "  (×" + giri + ")" : "");
    }

    async testo(t) {
        // `input text` non digerisce gli spazi: vanno come %s.
        const s = String(t || "").replace(/ /g, "%s").replace(/'/g, "");
        await this.sh("input text " + quotaShell(s));
        return "Digitato: " + t;
    }

    // ──────────────────────────────────────────────────── Kodi: ciclo vita ──

    async kodiFerma() {
        await this.sh("am force-stop " + this.cfg.pacchettoKodi);
        // force-stop torna subito ma il processo muore un attimo dopo.
        for (let i = 0; i < 10; i++) {
            const p = await this.sh("pidof " + this.cfg.pacchettoKodi + " || echo -");
            if (p.trim() === "-") return "Kodi fermato.";
            await new Promise(r => setTimeout(r, 500));
        }
        return "Kodi non si è fermato del tutto (potrebbe riavviarsi da solo).";
    }

    async kodiAvvia({ attendi = true } = {}) {
        await this.sh("monkey -p " + this.cfg.pacchettoKodi + " -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1");
        if (!attendi) return "Kodi avviato.";
        // Su questo box Kodi ci mette una decina di secondi a essere pronto.
        for (let i = 0; i < 40; i++) {
            await new Promise(r => setTimeout(r, 1000));
            try { await this.rpc("JSONRPC.Version", {}, { timeout: 2000 }); return "Kodi avviato e API pronta."; }
            catch (_) { /* ancora in avvio */ }
        }
        const p = await this.sh("pidof " + this.cfg.pacchettoKodi + " || echo -");
        return p.trim() === "-" ? "Kodi NON è partito."
            : "Kodi è partito (pid " + p.trim() + ") ma l'API non risponde: accendila con op='api_accendi'.";
    }

    async kodiRiavvia() {
        await this.kodiFerma();
        return await this.kodiAvvia();
    }

    // ────────────────────────────────────────── Kodi: accendere l'API ──

    /** Legge un file dal box passando da root (unico modo per Android/data). */
    async _leggiRemoto(remoto) {
        const ponte = "/data/local/tmp/.ag_r_" + Date.now();
        const esito = await this.sh("cp " + quotaShell(remoto) + " " + ponte + " && chmod 666 " + ponte + " && echo OK", { root: true });
        if (!/OK/.test(esito)) return { ok: false, out: "Non riesco a leggere " + remoto + ": " + esito };
        const locale = path.join(this.tmp, path.basename(remoto) + "." + Date.now());
        await this._adb(["-s", this.cfg.indirizzo, "pull", ponte, locale], { timeout: 60000 });
        await this.sh("rm -f " + ponte, { root: true });
        if (!fs.existsSync(locale)) return { ok: false, out: "Pull fallito da " + remoto };
        return { ok: true, locale, testo: fs.readFileSync(locale, "utf8") };
    }

    /** Scrive un file sul box via root, RIMETTENDO proprietario e permessi giusti. */
    async _scriviRemoto(remoto, contenuto) {
        const locale = path.join(this.tmp, "up-" + Date.now());
        fs.writeFileSync(locale, contenuto, "utf8");
        const ponte = "/data/local/tmp/.ag_w_" + Date.now();
        const p = await this._adb(["-s", this.cfg.indirizzo, "push", locale, ponte], { timeout: 120000 });
        if (!p.ok) return { ok: false, out: "Push fallito: " + p.out };
        // ★ Il proprietario CONTA: se il file resta di shell, Kodi (u0_a1xx) non
        // lo può riscrivere e le impostazioni tornano indietro al riavvio.
        const prop = await this.sh("stat -c '%U:%G' " + quotaShell(remoto) + " 2>/dev/null || echo ''", { root: true });
        const owner = String(prop).trim();
        let cmd = "cp " + ponte + " " + quotaShell(remoto);
        if (owner && owner !== ":") cmd += " && chown " + owner + " " + quotaShell(remoto);
        cmd += " && chmod 660 " + quotaShell(remoto) + " && rm -f " + ponte + " && echo OK";
        const esito = await this.sh(cmd, { root: true });
        try { fs.unlinkSync(locale); } catch (_) {}
        return /OK/.test(esito) ? { ok: true } : { ok: false, out: "Copia sul box fallita: " + esito };
    }

    /**
     * Accende il web server di Kodi (JSON-RPC su HTTP). È il passaggio che
     * trasforma "premere tasti alla cieca" in "comandare Kodi con precisione".
     *
     * Va fatto A KODI FERMO: Kodi tiene le impostazioni in memoria e riscrive
     * guisettings.xml quando esce — patcharlo da acceso non serve a niente.
     */
    async apiAccendi({ porta, utente, password } = {}) {
        const c = await this.connetti();
        if (!c.ok) return c.out;

        const p = Number(porta) || this.cfg.apiPorta || 8080;
        const u = utente || this.cfg.apiUtente || "kodi";
        // Kodi 19+ NON accetta il web server senza password.
        const pw = password || this.cfg.apiPassword || ("ag" + Math.random().toString(36).slice(2, 10));

        await this.kodiFerma();

        const file = this.cfg.kodiHome + "/userdata/guisettings.xml";
        const letto = await this._leggiRemoto(file);
        if (!letto.ok) return letto.out;
        let xml = letto.testo;

        const voci = {
            "services.webserver": "true",
            "services.webserverport": String(p),
            "services.webserverusername": u,
            "services.webserverpassword": pw,
            "services.webserverauthentication": "true",
            "services.esenabled": "true",
            "services.esallinterfaces": "true",
            "services.zeroconf": "true"
        };
        for (const [id, val] of Object.entries(voci)) {
            const rx = new RegExp("<setting\\s+id=\"" + id.replace(/\./g, "\\.") + "\"[^>]*>[\\s\\S]*?</setting>");
            const nuovo = '<setting id="' + id + '">' + val + "</setting>";
            if (rx.test(xml)) xml = xml.replace(rx, nuovo);
            else xml = xml.replace(/<\/settings>\s*$/, "    " + nuovo + "\n</settings>\n");
        }

        const scritto = await this._scriviRemoto(file, xml);
        if (!scritto.ok) return scritto.out;

        this.cfg.apiPorta = p; this.cfg.apiUtente = u; this.cfg.apiPassword = pw;
        scriviConfig(this.cfg);

        const avvio = await this.kodiAvvia();
        try {
            const v = await this.rpc("JSONRPC.Version", {});
            return "API JSON-RPC ACCESA e verificata.\n"
                + "  http://" + this.cfg.indirizzo.split(":")[0] + ":" + p + "/jsonrpc\n"
                + "  utente: " + u + "   password: " + pw + "   (salvate in " + CONFIG + ")\n"
                + "  versione API: " + JSON.stringify(v.version || v) + "\n"
                + "Da adesso op='rpc', 'impostazione_*' e 'addon_*' funzionano.";
        } catch (e) {
            return "Ho scritto le impostazioni e riavviato Kodi, ma l'API non risponde ancora.\n"
                + avvio + "\nErrore: " + e.message
                + "\nRiprova op='stato' fra qualche secondo; se resta muta, guarda op='log'.";
        }
    }

    // ───────────────────────────────────────────────────── Kodi: JSON-RPC ──

    rpc(metodo, params = {}, { timeout = 20000 } = {}) {
        return new Promise((risolvi, rifiuta) => {
            const host = this.cfg.indirizzo.split(":")[0];
            const corpo = JSON.stringify({ jsonrpc: "2.0", id: 1, method: metodo, params: params || {} });
            const auth = Buffer.from((this.cfg.apiUtente || "kodi") + ":" + (this.cfg.apiPassword || "")).toString("base64");
            const req = http.request({
                host, port: this.cfg.apiPorta || 8080, path: "/jsonrpc", method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Content-Length": Buffer.byteLength(corpo),
                    "Authorization": "Basic " + auth
                }, timeout
            }, res => {
                const pezzi = [];
                res.on("data", d => pezzi.push(d));
                res.on("end", () => {
                    const testo = Buffer.concat(pezzi).toString("utf8");
                    if (res.statusCode === 401) return rifiuta(new Error("API_NON_AUTORIZZATA: utente/password sbagliati. Rifai op='api_accendi'."));
                    let j; try { j = JSON.parse(testo); } catch (_) { return rifiuta(new Error("Risposta non-JSON da Kodi: " + testo.slice(0, 300))); }
                    if (j.error) return rifiuta(new Error("Kodi: " + (j.error.message || "") + " " + JSON.stringify(j.error.data || {})));
                    risolvi(j.result);
                });
            });
            req.on("timeout", () => { req.destroy(); rifiuta(new Error("API_MUTA: Kodi non risponde entro " + timeout + "ms (spento? API non accesa?)")); });
            req.on("error", e => rifiuta(new Error("API_IRRAGGIUNGIBILE: " + e.message + " — Kodi è acceso? L'API è stata accesa con op='api_accendi'?")));
            req.write(corpo); req.end();
        });
    }

    // ────────────────────────────────── Impostazioni di Kodi, per id ──

    /** Cerca le impostazioni per parola: serve a TROVARE l'id giusto prima di scriverlo. */
    async impostazioneCerca(q) {
        const r = await this.rpc("Settings.GetSettings", { level: "expert" });
        const cerca = String(q || "").toLowerCase();
        const trovate = (r.settings || []).filter(s =>
            !cerca || String(s.id).toLowerCase().includes(cerca)
            || String(s.label || "").toLowerCase().includes(cerca)
            || String(s.help || "").toLowerCase().includes(cerca));
        if (!trovate.length) return "Nessuna impostazione contiene «" + q + "».";
        return "Impostazioni che contengono «" + q + "» (" + trovate.length + "):\n"
            + trovate.slice(0, 60).map(s =>
                "  " + s.id + "\n      valore attuale: " + JSON.stringify(s.value)
                + (s.options ? "\n      scelte: " + s.options.map(o => JSON.stringify(o.value) + "=" + o.label).join(", ").slice(0, 400) : "")
                + (s.label ? "\n      etichetta: " + s.label : "")).join("\n")
            + (trovate.length > 60 ? "\n  … e altre " + (trovate.length - 60) + ", restringi la ricerca." : "");
    }

    async impostazioneLeggi(id) {
        const v = await this.rpc("Settings.GetSettingValue", { setting: id });
        return id + " = " + JSON.stringify(v.value);
    }

    async impostazioneScrivi(id, valore) {
        // Kodi è tipizzato: "true" come stringa su un bool viene rifiutato.
        let v = valore;
        if (v === "true") v = true; else if (v === "false") v = false;
        else if (typeof v === "string" && /^-?\d+$/.test(v)) v = Number(v);
        const r = await this.rpc("Settings.SetSettingValue", { setting: id, value: v });
        if (r !== true) return "Kodi ha RIFIUTATO " + id + " = " + JSON.stringify(v)
            + " (tipo sbagliato? valore fuori dalle scelte ammesse? usa op='impostazione_cerca' per vedere le scelte)";
        const ora = await this.rpc("Settings.GetSettingValue", { setting: id });
        return "Impostato e verificato: " + id + " = " + JSON.stringify(ora.value);
    }

    // ──────────────────────────────────────────────────────────── Add-on ──

    async addonLista({ abilitati = null, tipo = null } = {}) {
        const p = { properties: ["name", "version", "enabled", "broken", "summary"] };
        if (abilitati !== null) p.enabled = !!abilitati;
        if (tipo) p.type = tipo;
        const r = await this.rpc("Addons.GetAddons", p);
        const a = r.addons || [];
        if (!a.length) return "Nessun add-on trovato con questo filtro.";
        return "Add-on installati (" + a.length + "):\n" + a.map(x =>
            "  " + (x.enabled ? "[on] " : "[off]") + " " + x.addonid + "  v" + (x.version || "?")
            + (x.broken ? "  ⚠ ROTTO" : "") + "\n      " + (x.name || "")).join("\n");
    }

    async addonDettagli(id) {
        const r = await this.rpc("Addons.GetAddonDetails", {
            addonid: id,
            properties: ["name", "version", "summary", "description", "author", "enabled", "broken", "dependencies", "path"]
        });
        const a = r.addon || {};
        return [
            "Add-on: " + a.addonid,
            "  nome     : " + (a.name || "?") + "   v" + (a.version || "?"),
            "  stato    : " + (a.enabled ? "ABILITATO" : "disabilitato") + (a.broken ? "   ⚠ segnalato ROTTO: " + a.broken : ""),
            "  autore   : " + (a.author || "?"),
            "  riassunto: " + (a.summary || ""),
            "  dipende  : " + ((a.dependencies || []).map(d => d.addonid + (d.optional ? "?" : "")).join(", ") || "niente"),
            "  percorso : " + (a.path || "")
        ].join("\n");
    }

    async addonAbilita(id, acceso = true) {
        await this.rpc("Addons.SetAddonEnabled", { addonid: id, enabled: !!acceso });
        return await this.addonDettagli(id);
    }

    async addonEsegui(id, params) {
        await this.rpc("Addons.ExecuteAddon", params ? { addonid: id, params } : { addonid: id });
        return "Lanciato l'add-on " + id + ". Guarda com'è andata con op='schermo'.";
    }

    // ── Catalogo del repository UFFICIALE Kodi (per cercare e installare) ──

    _scarica(url, { redirect = 5 } = {}) {
        return new Promise((risolvi, rifiuta) => {
            const mod = url.startsWith("https") ? https : http;
            const req = mod.get(url, { timeout: 60000, headers: { "User-Agent": "Antigravity/8k" } }, res => {
                if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
                    if (redirect <= 0) return rifiuta(new Error("troppi redirect"));
                    res.resume();
                    return risolvi(this._scarica(new URL(res.headers.location, url).toString(), { redirect: redirect - 1 }));
                }
                if (res.statusCode !== 200) { res.resume(); return rifiuta(new Error("HTTP " + res.statusCode + " su " + url)); }
                const pezzi = [];
                res.on("data", d => pezzi.push(d));
                res.on("end", () => risolvi(Buffer.concat(pezzi)));
            });
            req.on("error", rifiuta);
            req.on("timeout", () => { req.destroy(); rifiuta(new Error("timeout su " + url)); });
        });
    }

    /** addons.xml del ramo giusto (omega per Kodi 21), in cache mezza giornata. */
    async _catalogo() {
        const cache = path.join(this.tmp, "addons-" + this.cfg.ramoRepo + ".xml");
        try {
            const st = fs.statSync(cache);
            if (Date.now() - st.mtimeMs < 12 * 3600 * 1000) return fs.readFileSync(cache, "utf8");
        } catch (_) {}
        const gz = await this._scarica(MIRROR + "/" + this.cfg.ramoRepo + "/addons.xml.gz");
        const xml = zlib.gunzipSync(gz).toString("utf8");
        fs.writeFileSync(cache, xml, "utf8");
        return xml;
    }

    /** Spezza addons.xml in schede. Regex e non un parser XML: nessuna dipendenza in più. */
    async _schede() {
        const xml = await this._catalogo();
        const out = [];
        const rx = /<addon\s+([^>]*?)>([\s\S]*?)<\/addon>/g;
        let m;
        while ((m = rx.exec(xml))) {
            const attr = m[1], corpo = m[2];
            const g = (k) => { const r = new RegExp(k + '="([^"]*)"').exec(attr); return r ? r[1] : ""; };
            const sum = /<summary[^>]*>([\s\S]*?)<\/summary>/.exec(corpo);
            const des = /<description[^>]*>([\s\S]*?)<\/description>/.exec(corpo);
            const req = [];
            const rr = /<import\s+addon="([^"]+)"(?:\s+version="([^"]*)")?(?:\s+optional="([^"]*)")?/g;
            let r2; while ((r2 = rr.exec(corpo))) req.push({ id: r2[1], ver: r2[2] || "", opz: r2[3] === "true" });
            out.push({
                id: g("id"), nome: g("name"), versione: g("version"), autore: g("provider-name"),
                punto: g("point"), riassunto: (sum ? sum[1] : "").trim(), descrizione: (des ? des[1] : "").trim(),
                richiede: req
            });
        }
        return out;
    }

    /** Cerca un add-on nel repo ufficiale per id, nome o descrizione. */
    async addonCerca(q, limite = 25) {
        const schede = await this._schede();
        const t = String(q || "").toLowerCase().trim();
        if (!t) return "Indica cosa cercare (es. 'sottotitoli', 'youtube', 'meteo', 'iptv').";
        const punteggio = (s) => {
            let p = 0;
            if (s.id.toLowerCase() === t) p += 100;
            if (s.id.toLowerCase().includes(t)) p += 40;
            if ((s.nome || "").toLowerCase().includes(t)) p += 30;
            if ((s.riassunto || "").toLowerCase().includes(t)) p += 10;
            if ((s.descrizione || "").toLowerCase().includes(t)) p += 5;
            return p;
        };
        const trovati = schede.map(s => ({ s, p: punteggio(s) })).filter(x => x.p > 0)
            .sort((a, b) => b.p - a.p).slice(0, limite);
        if (!trovati.length) return "Nessun add-on nel repository ufficiale Kodi (" + this.cfg.ramoRepo + ") corrisponde a «" + q + "».";
        return "Trovati nel repository UFFICIALE Kodi — ramo " + this.cfg.ramoRepo + " (" + trovati.length + " su " + schede.length + " add-on):\n"
            + trovati.map(({ s }) =>
                "  " + s.id + "   v" + s.versione + "   [" + (s.punto || "?") + "]"
                + "\n      " + (s.nome || "") + (s.autore ? " — di " + s.autore : "")
                + (s.riassunto ? "\n      " + s.riassunto.slice(0, 200) : "")).join("\n")
            + "\n\nPer installarne uno: op='addon_installa', addon='<id>'.";
    }

    /** Estrae uno zip con PowerShell: niente librerie in più, siamo su Windows. */
    _scompatta(zip, dove) {
        const r = spawnSync("powershell", ["-NoProfile", "-Command",
            "Expand-Archive -LiteralPath " + JSON.stringify(zip) + " -DestinationPath " + JSON.stringify(dove) + " -Force"],
            { encoding: "utf8", windowsHide: true, timeout: 180000 });
        return r.status === 0 ? { ok: true } : { ok: false, out: (r.stderr || r.stdout || "").trim() };
    }

    /**
     * Installa un add-on dal repository ufficiale: risolve le dipendenze,
     * scarica, scompatta, copia sul box, riavvia Kodi e VERIFICA che sia
     * davvero abilitato. È il "verifica che funziona" della richiesta.
     */
    async addonInstalla(id, { profondita = 0, giaFatti = null, saltaRiavvio = false } = {}) {
        const fatti = giaFatti || new Set();
        if (fatti.has(id)) return null;
        fatti.add(id);
        const passi = [];

        // Già presente? Non lo riscarico.
        const presenti = await this.sh("ls " + quotaShell(this.cfg.kodiHome + "/addons") + " 2>/dev/null", { root: true });
        const elenco = new Set(String(presenti).split(/\r?\n/).map(s => s.trim()).filter(Boolean));
        if (elenco.has(id)) {
            passi.push("  = " + id + " — già presente, salto");
        } else {
            const schede = await this._schede();
            const s = schede.find(x => x.id === id);
            if (!s) {
                // Le dipendenze di sistema (xbmc.python ecc.) non sono add-on scaricabili.
                if (/^xbmc\./.test(id)) { passi.push("  = " + id + " — dipendenza di sistema, la fornisce Kodi"); return passi.join("\n"); }
                return "  ✗ " + id + " — NON esiste nel repository ufficiale (ramo " + this.cfg.ramoRepo + ").";
            }

            // Prima le dipendenze, ricorsivamente.
            if (profondita < 6) {
                for (const d of s.richiede) {
                    if (d.opz || /^xbmc\./.test(d.id)) continue;
                    const sub = await this.addonInstalla(d.id, { profondita: profondita + 1, giaFatti: fatti, saltaRiavvio: true });
                    if (sub) passi.push(sub);
                }
            }

            const url = MIRROR + "/" + this.cfg.ramoRepo + "/" + s.id + "/" + s.id + "-" + s.versione + ".zip";
            let zipBuf;
            try { zipBuf = await this._scarica(url); }
            catch (e) { return passi.concat("  ✗ " + id + " — scaricamento fallito: " + e.message).join("\n"); }

            const zip = path.join(this.tmp, s.id + "-" + s.versione + ".zip");
            fs.writeFileSync(zip, zipBuf);
            const dest = path.join(this.tmp, "estratto-" + s.id + "-" + Date.now());
            const est = this._scompatta(zip, dest);
            if (!est.ok) return passi.concat("  ✗ " + id + " — zip non estraibile: " + est.out).join("\n");

            const cartella = path.join(dest, s.id);
            if (!fs.existsSync(cartella)) return passi.concat("  ✗ " + id + " — lo zip non contiene la cartella attesa " + s.id).join("\n");

            // Ponte in /data/local/tmp (scrivibile da shell), poi copia da root.
            const ponte = "/data/local/tmp/.ag_addon_" + s.id;
            await this.sh("rm -rf " + ponte, { root: true });
            const push = await this._adb(["-s", this.cfg.indirizzo, "push", cartella, ponte], { timeout: 300000 });
            if (!push.ok) return passi.concat("  ✗ " + id + " — push fallito: " + push.out).join("\n");

            const proprietario = await this.sh("stat -c '%U:%G' " + quotaShell(this.cfg.kodiHome + "/addons") + " 2>/dev/null || echo ''", { root: true });
            const own = String(proprietario).trim();
            const destBox = this.cfg.kodiHome + "/addons/" + s.id;
            let cmd = "rm -rf " + quotaShell(destBox) + " && cp -r " + ponte + " " + quotaShell(destBox);
            if (own && own !== ":") cmd += " && chown -R " + own + " " + quotaShell(destBox);
            cmd += " && chmod -R 770 " + quotaShell(destBox) + " && rm -rf " + ponte + " && echo OK";
            const esito = await this.sh(cmd, { root: true });
            if (!/OK/.test(esito)) return passi.concat("  ✗ " + id + " — copia sul box fallita: " + esito).join("\n");

            try { fs.unlinkSync(zip); fs.rmSync(dest, { recursive: true, force: true }); } catch (_) {}
            passi.push("  ✓ " + s.id + " v" + s.versione + " copiato" + (s.nome ? " (" + s.nome + ")" : ""));
        }

        if (saltaRiavvio) return passi.join("\n");

        // Kodi legge la cartella addons SOLO all'avvio: senza riavvio non esiste.
        passi.push("  … riavvio Kodi perché rilegga la cartella add-on");
        await this.kodiRiavvia();

        // VERIFICA vera: Kodi lo vede? È abilitato? È rotto?
        try {
            const d = await this.rpc("Addons.GetAddonDetails", { addonid: id, properties: ["name", "version", "enabled", "broken"] });
            const a = d.addon || {};
            if (a.broken) passi.push("  ⚠ Kodi lo segnala ROTTO: " + a.broken);
            if (!a.enabled) {
                await this.rpc("Addons.SetAddonEnabled", { addonid: id, enabled: true });
                passi.push("  ✓ abilitato");
            }
            passi.push("  ✓ VERIFICATO: Kodi vede " + a.addonid + " v" + a.version + " — " + (a.name || "") + " — abilitato.");
        } catch (e) {
            passi.push("  ⚠ NON verificato: Kodi non lo riconosce (" + e.message + ").");
            passi.push("    Guarda op='log' per l'errore preciso: di solito è una dipendenza mancante o la versione di Python sbagliata.");
        }
        return "Installazione di «" + id + "»:\n" + passi.join("\n");
    }

    async addonRimuovi(id) {
        const dest = this.cfg.kodiHome + "/addons/" + id;
        const c = await this.sh("ls -d " + quotaShell(dest) + " 2>/dev/null || echo ASSENTE", { root: true });
        if (/ASSENTE/.test(c)) return "L'add-on «" + id + "» non è installato.";
        await this.sh("rm -rf " + quotaShell(dest), { root: true });
        await this.kodiRiavvia();
        return "Rimosso l'add-on «" + id + "» e riavviato Kodi.";
    }

    // ─────────────────────────────────────────────────────────────── APK ──

    async apkLista(filtro) {
        const out = await this.sh("pm list packages -3" + (filtro ? " | grep -i " + quotaShell(filtro) : ""));
        const righe = String(out).split(/\r?\n/).map(s => s.replace(/^package:/, "").trim()).filter(Boolean);
        return "App installate dall'utente (" + righe.length + "):\n" + righe.map(r => "  " + r).join("\n");
    }

    /** Installa un APK da percorso locale o da URL. Attenzione all'ABI: qui è 32 bit. */
    async apkInstalla(origine) {
        let apk = origine;
        if (/^https?:\/\//i.test(origine)) {
            const buf = await this._scarica(origine);
            apk = path.join(this.tmp, "app-" + Date.now() + ".apk");
            fs.writeFileSync(apk, buf);
        }
        if (!fs.existsSync(apk)) return "APK non trovato: " + apk;
        const mb = (fs.statSync(apk).size / 1048576).toFixed(1);
        const r = await this._adb(["-s", this.cfg.indirizzo, "install", "-r", "-g", apk], { timeout: 600000 });
        const out = String(r.out || "");
        if (/Success/i.test(out)) return "APK installato (" + mb + " MB): " + path.basename(apk) + "\n" + out;
        if (/INSTALL_FAILED_NO_MATCHING_ABIS/i.test(out))
            return "FALLITO — ABI SBAGLIATA. Questo box è armeabi-v7a a 32 bit: l'APK che hai preso è per arm64. "
                + "Cerca la variante armeabi-v7a (o 'universal') dello stesso programma.\n" + out;
        if (/INSTALL_FAILED_OLDER_SDK/i.test(out))
            return "FALLITO — l'APK richiede un Android più recente del 12 che c'è sul box.\n" + out;
        return "Installazione FALLITA:\n" + out;
    }

    async apkDisinstalla(pacchetto) {
        const r = await this._adb(["-s", this.cfg.indirizzo, "uninstall", pacchetto], { timeout: 120000 });
        return "Disinstallazione di " + pacchetto + ": " + r.out;
    }

    async apri(pacchetto) {
        await this.sh("monkey -p " + pacchetto + " -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1");
        return "Aperto " + pacchetto + ". Verifica con op='schermo'.";
    }

    // ──────────────────────────────────────────────────────── Diagnostica ──

    /** Il kodi.log: l'unico posto dove si legge PERCHÉ un add-on non parte. */
    async log(righe = 120, filtro = "") {
        const file = this.cfg.kodiHome + "/temp/kodi.log";
        let cmd = "tail -n " + Math.min(2000, Math.max(10, Number(righe) || 120)) + " " + quotaShell(file);
        if (filtro) cmd += " | grep -i " + quotaShell(filtro);
        const out = await this.sh(cmd, { root: true, timeout: 90000 });
        if (!String(out).trim()) return "kodi.log vuoto o non leggibile (Kodi non è mai partito?).";
        return "kodi.log (ultime " + righe + " righe" + (filtro ? ", filtro «" + filtro + "»" : "") + "):\n" + out;
    }

    async notifica(titolo, messaggio, secondi = 5000) {
        await this.rpc("GUI.ShowNotification", {
            title: String(titolo || "Antigravity"),
            message: String(messaggio || ""),
            displaytime: Number(secondi) || 5000
        });
        return "Notifica mostrata sulla TV.";
    }

    async riproduci(percorso) {
        await this.rpc("Player.Open", { item: { file: String(percorso) } });
        return "Riproduzione avviata: " + percorso;
    }
}

module.exports = { UltraHD8K, CONFIG_8K: CONFIG, DEFAULT_8K: DEFAULT };
