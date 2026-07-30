/**
 * kaggleEngine.js — motore di inferenza OpenAI-compatible verso i notebook Kaggle
 * (modelli abliterated: 14B Qwen2.5-Coder / 30B Qwen3-Coder MoE) esposti via ngrok.
 * Usato come anello di failover in localOrchestrator (modelli grandi e uncensored).
 *
 * Non espone segreti: l'host viene da kaggleWaker.KAGGLE_HOST (ngrok fisso), e il
 * notebook Kaggle NON richiede API key (è il tuo notebook privato). Se il notebook
 * è spento, l'inferenza fallisce velocemente e il failover passa al motore successivo
 * (non accende il notebook: l'accensione on-demand resta solo per scelta esplicita kaggle::).
 */
const https = require("https");
const kaggle = require("./kaggleWaker");

// Modelli disponibili sui notebook (nome → tag nel notebook).
// ★ 2026-07-23 — FIX NOMI MODELLO: i notebook fanno `ollama pull` col nome COMPLETO
// di HuggingFace e NON creano alias, quindi Ollama li espone esattamente così. I nomi
// brevi di prima (qwen2.5-coder-…:latest) NON esistevano sul notebook → ogni inferenza
// sarebbe fallita con "model not found". Gli override da .env restano possibili.
const MODELS = {
  "14b": process.env.KAGGLE_MODEL_14B || "hf.co/bartowski/Qwen2.5-Coder-14B-Instruct-abliterated-GGUF:Q4_K_M",
  "30b": process.env.KAGGLE_MODEL_30B || "hf.co/mradermacher/Huihui-Qwen3-Coder-30B-A3B-Instruct-abliterated-i1-GGUF:Q4_K_M"
};

function _host() { return kaggle.KAGGLE_HOST; }

function _post(path, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req = https.request({
      host: _host(), path, method: "POST", timeout: 180000,
      headers: {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
        "Content-Length": Buffer.byteLength(data)
      }
    }, (res) => {
      let d = ""; res.on("data", c => d += c);
      res.on("end", () => {
        if (res.statusCode !== 200) return reject(new Error("Kaggle HTTP " + res.statusCode + ": " + d.slice(0, 200)));
        try { resolve(JSON.parse(d)); } catch (e) { reject(new Error("Kaggle risposta non JSON: " + d.slice(0, 200))); }
      });
    });
    req.on("error", reject);
    req.setTimeout(180000, () => req.destroy(new Error("Kaggle timeout inferenza")));
    req.end(data);
  });
}

function _normalize(messages, tools) {
  // OpenAI-compatible: messages + tools (function). Antigravity passa tool già in
  // formato OpenAI, ma se i tool arrivano come {function:{name,description,parameters}}
  // li lasciamo così (lo è).
  const toolsOAI = Array.isArray(tools) ? tools.map(t => ({
    type: "function",
    function: { name: t.function.name, description: t.function.description, parameters: t.function.parameters }
  })) : undefined;
  return { messages, tools: toolsOAI };
}

class KaggleEngine {
  constructor(opts = {}) { this.logger = opts.logger || console; this._name = "kaggle"; }

  configured() { return !!_host(); }

  /** chat con tool-calling (OpenAI-compatible). */
  async chatTools(model, messages, tools) {
    const tag = String(model || "").replace(/^kaggle::/i, "").toLowerCase() || "14b";
    const realModel = MODELS[tag] || MODELS["14b"];
    const { messages: msgs, tools: tls } = _normalize(messages, tools);
    const payload = { model: realModel, messages: msgs, stream: false, temperature: 0.4 };
    if (tls && tls.length) payload.tools = tls;
    const json = await _post("/v1/chat/completions", payload);
    const choice = (json.choices && json.choices[0]) || {};
    const msg = choice.message || {};
    return {
      content: msg.content || "",
      tool_calls: Array.isArray(msg.tool_calls) ? msg.tool_calls.map(tc => ({
        id: tc.id, function: { name: tc.function && tc.function.name, arguments: tc.function && tc.function.arguments }
      })) : undefined,
      model: "kaggle::" + tag,
      label: "Kaggle " + tag.toUpperCase() + " (abliterated)"
    };
  }

  /** chat semplice (senza tool). */
  async chat(model, messages, opts = {}) {
    const tag = String(model || "").replace(/^kaggle::/i, "").toLowerCase() || "14b";
    const realModel = MODELS[tag] || MODELS["14b"];
    const last = messages[messages.length - 1];
    const json = await _post("/v1/chat/completions", {
      model: realModel,
      messages: [{ role: "user", content: (last && last.content) || "" }],
      stream: false, temperature: opts.temperature || 0.5
    });
    return ((json.choices && json.choices[0] && json.choices[0].message && json.choices[0].message.content) || "").toString();
  }

  async isOnline() { try { return await kaggle.isUp(); } catch (_) { return false; } }
}

module.exports = { KaggleEngine, KAGGLE_MODELS: MODELS };
