"use strict";
/**
 * imageAgent — sotto-agente immagini che ESEGUE la generazione via ComfyUI
 * (comfyClient già cablato). Input: prompt + parametri. Output: percorso PNG.
 */
const path = require("path");

async function generate(prompt, opts = {}) {
  try {
    const comfy = require("../comfyClient");
    // comfyClient espone tipicamente txt2img(prompt, opts)
    if (typeof comfy.txt2img === "function") {
      const r = await comfy.txt2img(prompt, opts);
      return { ok: true, output: r };
    }
    return { ok: false, error: "comfyClient.txt2img non disponibile" };
  } catch (e) { return { ok: false, error: e.message }; }
}

module.exports = { generate, kind: "immagini" };
