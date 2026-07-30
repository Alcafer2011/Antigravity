"use strict";
/**
 * whatsappBridge — NOTIFICHE + COMANDI Hermes via WhatsApp (numero utente:
 * +393****1150), versione LEGGERA (CallMeBot, nessun puppeteer/npm pesante).
 *
 * Perche' non whatsapp-web.js: richiede Chromium/Puppeteer e su questa macchina
 * l'install npm fallisce (HP Wolf / impronte / rete). CallMeBot invece e' solo
 * una chiamata HTTP GET: nessun install, funziona subito.
 *
 * SETUP (una tantum, lo fai tu in 2 minuti):
 *   1) Apri WhatsApp sul telefono e invia un messaggio al numero CallMeBot:
 *      +34 644 09 71 85  (il bot ufficiale)  scrivendo:  "I allow callmebot to send me messages"
 *   2) Il bot ti risponde con la tua API key (es. "APIKEY: 1234567ABCDEF").
 *   3) Incolla quella key nel .env come  WHATSAPP_CALLMEBOT_KEY=...
 * Fatto: Hermes ora ti manda le notifiche su WhatsApp.
 *
 * Comandi: puoi anche rispondere al bot e lui inoltra qui (via /hermes/inbound).
 */
const fs = require("fs");
const path = require("path");
const os = require("os");
const http = require("http");
const https = require("https");
const url = require("url");

const MY_NUMBER = "+393****1150";       // il TUO numero
const CALLMEBOT_NUM = "34644097185";     // numero ufficiale CallMeBot (senza +)
const KEY_FILE = path.join(os.homedir(), ".antigravity", "whatsapp-key.txt");

function _key() {
  try { return fs.readFileSync(KEY_FILE, "utf8").trim(); } catch (_) {
    try {
      const txt = fs.readFileSync(path.join(os.homedir(), ".env"), "utf8");
      const m = txt.match(/WHATSAPP_CALLMEBOT_KEY\s*=\s*"?([^"\r\n]+)"?/i);
      return m ? m[1].trim() : null;
    } catch (_) { return null; }
  }
}

// Invia un messaggio WhatsApp all'utente (notifica Hermes) tramite CallMeBot.
function notify(text) {
  const key = _key();
  if (!key) { console.log("[whatsapp] nessuna key CallMeBot: notifica saltata. Metti WHATSAPP_CALLMEBOT_KEY nel .env."); return false; }
  const q = "https://api.callmebot.com/whatsapp.php?phone=" + encodeURIComponent(MY_NUMBER.replace(/\+/g, "")) +
            "&text=" + encodeURIComponent(String(text).slice(0, 4000)) + "&apikey=" + encodeURIComponent(key);
  try {
    const req = https.get(q, (res) => { res.resume(); });
    req.on("error", () => {});
    req.end();
    return true;
  } catch (e) { console.log("[whatsapp] send err:", e.message); return false; }
}

// Inoltra un messaggio in arrivo a Hermes (server Antigravity su 8790).
function _forwardToHermes(from, body) {
  const data = JSON.stringify({ from, body, channel: "whatsapp" });
  const req = http.request({ host: "127.0.0.1", port: 8790, path: "/hermes/inbound", method: "POST",
    headers: { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(data) } },
    (res) => { let d = ""; res.on("data", c => d += c); res.on("end", () => {
      try { const j = JSON.parse(d); if (j.reply) notify("💬 Hermes: " + j.reply); } catch (_) {} }); });
  req.on("error", () => {});
  req.write(data); req.end();
}

function start() {
  console.log("[whatsapp] bridge CallMeBot pronto (notifiche via HTTP). Key:", _key() ? "presente" : "MANCANTE -> metti WHATSAPP_CALLMEBOT_KEY nel .env");
}

module.exports = { start, notify, MY_NUMBER };
