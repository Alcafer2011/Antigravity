"use strict";
// ---------------------------------------------------------------------------
// IL SALOTTO — Raspberry Pi 4 con LibreELEC, attaccato alla Hisense.
//
// E' il secondo apparecchio di casa, dopo il box 8K della camera. La differenza
// che conta per chi scrive codice: **qui NON c'e' adb**. Non e' Android: e'
// Linux. Quindi si comanda in due modi soltanto:
//
//   1) l'API di Kodi (JSON-RPC su HTTP)  -> tutto quello che riguarda i video
//   2) SSH                                -> il sistema (servizi, file, log)
//
// Chi cerca qui dentro `tasto`, `apk_installa` o `sveglia` non li trova, e non
// e' una dimenticanza: su questo apparecchio non hanno senso.
//
// Verificato il 05/09/2026: LibreELEC 11.0.6, Kodi 20.3, 4 GB di RAM.
// ---------------------------------------------------------------------------

const http = require("http");
const fs = require("fs");
const path = require("path");
const { spawnSync } = require("child_process");

const CONFIG = path.join(__dirname, ".salotto.json");

const DEFAULT = {
    indirizzo: "192.168.1.105",
    apiPorta: 8080,
    apiUtente: "kodi",
    apiPassword: "ag1kp0yx7w",
    sshUtente: "root",
    // La password SSH NON sta qui: si legge da .salotto-ssh (fuori dal codice,
    // fuori da git). Se manca, le operazioni di sistema si rifiutano.
    modello: "Raspberry Pi 4 (case Argon NEO) — LibreELEC 11.0.6, Kodi 20.3",
    note: "Attaccato alla Hisense 50A5LE del salotto via micro HDMI. " +
          "Il telecomando della TV lo comanda via HDMI-CEC.",
};

function leggiConfig() {
    try {
        return Object.assign({}, DEFAULT, JSON.parse(fs.readFileSync(CONFIG, "utf8")));
    } catch (_) {
        return Object.assign({}, DEFAULT);
    }
}

class Salotto {
    constructor(opts = {}) {
        this.cfg = Object.assign(leggiConfig(), opts);
    }

    /** Chiamata all'API di Kodi. E' la porta principale di questo apparecchio. */
    rpc(metodo, params = {}, { timeout = 20000 } = {}) {
        const corpo = JSON.stringify({ jsonrpc: "2.0", id: 1, method: metodo, params });
        const auth = Buffer.from(this.cfg.apiUtente + ":" + this.cfg.apiPassword).toString("base64");
        return new Promise((risolvi, rifiuta) => {
            const req = http.request({
                host: this.cfg.indirizzo, port: this.cfg.apiPorta, path: "/jsonrpc",
                method: "POST", timeout,
                headers: {
                    "Content-Type": "application/json",
                    "Content-Length": Buffer.byteLength(corpo),
                    "Authorization": "Basic " + auth,
                },
            }, (res) => {
                let d = "";
                res.on("data", (c) => { d += c; });
                res.on("end", () => {
                    if (res.statusCode === 401) {
                        return rifiuta(new Error(
                            "Kodi del salotto ha rifiutato la password. " +
                            "Sta in src/.salotto.json (campo apiPassword)."));
                    }
                    try { risolvi(JSON.parse(d)); }
                    catch (e) { rifiuta(new Error("risposta non capita: " + d.slice(0, 120))); }
                });
            });
            req.on("timeout", () => { req.destroy(); rifiuta(new Error(
                "Il salotto non risponde entro " + timeout + " ms. " +
                "Kodi e' avviato? La TV e' stata accesa almeno una volta?")); });
            req.on("error", (e) => rifiuta(new Error(
                "Non raggiungo il salotto (" + this.cfg.indirizzo + "): " + e.message)));
            req.write(corpo);
            req.end();
        });
    }

    /** Comando di sistema via SSH. Serve solo per servizi, file e log. */
    sh(comando) {
        let pw = "";
        try { pw = fs.readFileSync(path.join(__dirname, ".salotto-ssh"), "utf8").trim(); }
        catch (_) {
            return Promise.resolve(
                "Non posso entrare via SSH: manca src/.salotto-ssh con la password. " +
                "Le operazioni sui VIDEO funzionano lo stesso (passano dall'API di Kodi).");
        }
        // La password NON si passa sulla riga di comando: contiene una '&', e
        // fra Windows, wsl.exe e la shell qualcuno se la mangia sempre.
        // Si scrive in un file dentro WSL e si usa sshpass -f. (Guasto vero.)
        spawnSync("wsl.exe", ["-d", "Ubuntu", "-u", "root", "--", "sh", "-c",
            "cat > /root/.salotto-pw && chmod 600 /root/.salotto-pw"],
            { input: pw, encoding: "utf8", timeout: 20000 });
        // Si passa da WSL perche' Windows non ha sshpass. E' gia' installato.
        const r = spawnSync("wsl.exe", ["-d", "Ubuntu", "-u", "root", "--",
            "sshpass", "-f", "/root/.salotto-pw", "ssh", "-o", "StrictHostKeyChecking=no",
            "-o", "UserKnownHostsFile=/dev/null", "-o", "ConnectTimeout=10",
            this.cfg.sshUtente + "@" + this.cfg.indirizzo, comando],
            { encoding: "utf8", timeout: 60000 });
        return Promise.resolve(((r.stdout || "") + (r.stderr || ""))
            .split("\n").filter((x) => !/^Warning: Permanently added|systemd user session/.test(x))
            .join("\n").trim());
    }

    async stato() {
        const righe = ["SALOTTO — " + this.cfg.modello];
        try {
            const v = await this.rpc("Application.GetProperties", { properties: ["version", "volume", "muted"] });
            const a = (v.result || {});
            righe.push("Kodi " + (a.version ? a.version.major + "." + a.version.minor : "?") +
                       " — volume " + a.volume + (a.muted ? " (muto)" : ""));
        } catch (e) {
            righe.push("Kodi NON risponde: " + e.message);
            return righe.join("\n");
        }
        try {
            const p = await this.rpc("Player.GetActivePlayers");
            const gi = (p.result || []);
            if (!gi.length) righe.push("Non sta riproducendo niente.");
            else {
                const d = await this.rpc("Player.GetItem", {
                    playerid: gi[0].playerid, properties: ["title", "showtitle", "season", "episode"] });
                const it = ((d.result || {}).item) || {};
                righe.push("In riproduzione: " + (it.showtitle ? it.showtitle + " — " : "") +
                           (it.label || it.title || "?"));
            }
        } catch (_) { /* poco importante */ }
        return righe.join("\n");
    }

    async riproduci(percorso) {
        await this.rpc("Player.Open", { item: { file: percorso } });
        return "Mandato in riproduzione nel salotto:\n  " + percorso;
    }

    async apriAddon(addonId) {
        await this.rpc("GUI.ActivateWindow", { window: "videos", parameters: ["plugin://" + addonId + "/"] });
        return "Aperto " + addonId + " sulla TV del salotto.";
    }

    async ferma() {
        const p = await this.rpc("Player.GetActivePlayers");
        for (const g of (p.result || [])) await this.rpc("Player.Stop", { playerid: g.playerid });
        return "Fermato.";
    }

    async pausa() {
        const p = await this.rpc("Player.GetActivePlayers");
        for (const g of (p.result || [])) await this.rpc("Player.PlayPause", { playerid: g.playerid });
        return "Pausa / riprendi.";
    }

    async volume(livello) {
        await this.rpc("Application.SetVolume", { volume: Math.max(0, Math.min(100, parseInt(livello, 10) || 0)) });
        return "Volume del salotto: " + livello;
    }

    async notifica(titolo, messaggio, secondi = 5) {
        await this.rpc("GUI.ShowNotification", { title: String(titolo), message: String(messaggio), displaytime: secondi * 1000 });
        return "Avviso mostrato sulla TV del salotto.";
    }

    async tracceAudio() {
        const p = await this.rpc("Player.GetActivePlayers");
        const gi = (p.result || []);
        if (!gi.length) return "Non sta riproducendo niente.";
        const d = await this.rpc("Player.GetProperties", {
            playerid: gi[0].playerid, properties: ["audiostreams", "currentaudiostream"] });
        const r = d.result || {};
        const ora = (r.currentaudiostream || {}).index;
        return (r.audiostreams || []).map((t) =>
            (t.index === ora ? "> " : "  ") + t.index + "  " + (t.language || "?") +
            "  " + (t.channels || "?") + " canali  (" + (t.codec || "?") + ")").join("\n")
            || "Una sola traccia.";
    }

    async log(righe = 40, filtro = "") {
        const cmd = filtro
            ? "grep -i " + JSON.stringify(filtro) + " /storage/.kodi/temp/kodi.log | tail -" + righe
            : "tail -" + righe + " /storage/.kodi/temp/kodi.log";
        return await this.sh(cmd);
    }
}

module.exports = { Salotto };
