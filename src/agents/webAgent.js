"use strict";
/**
 * webAgent — sotto-agente ricerca/Tor che ESEGUE davvero (webSearch / torBrowser
 * già cablati). Input: query. Output: risultati o pagina .onion.
 */
async function search(query, opts = {}) {
  try {
    const ws = require("../webSearch");
    if (typeof ws.search === "function") return { ok: true, output: await ws.search(query, opts) };
    return { ok: false, error: "webSearch.search non disponibile" };
  } catch (e) { return { ok: false, error: e.message }; }
}

async function onion(url) {
  try {
    const tor = require("../torBrowser");
    if (typeof tor.fetch === "function") return { ok: true, output: await tor.fetch(url) };
    return { ok: false, error: "torBrowser.fetch non disponibile" };
  } catch (e) { return { ok: false, error: e.message }; }
}

module.exports = { search, onion, kind: "web" };
