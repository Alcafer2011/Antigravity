#!/usr/bin/env node
"use strict";

/**
 * Server MCP di Antigravity — espone gli strumenti dell'estensione (generazione
 * immagini via ComfyUI, analisi binari RE) ad HERMES, così il cervello di Hermes
 * li usa nel suo loop come fossero suoi. Integrazione profonda: un solo cervello
 * (Hermes) con due cassette degli attrezzi fuse (le sue + le nostre).
 *
 * Protocollo: MCP su stdio, JSON-RPC 2.0, un messaggio per riga.
 * Registrazione:  hermes mcp add antigravity -- node <percorso>/mcpServer.js
 */

const readline = require("readline");
const { ComfyClient } = require("./comfyClient");
const { analyzeBinary } = require("./reTools");
const { HermesClient } = require("./hermesClient");

const comfy = new ComfyClient({});
const hermes = new HermesClient({});

const TOOLS = [
    {
        name: "generate_image",
        description: "Genera un'immagine da una descrizione testuale (ComfyUI in locale). Il prompt va in inglese, dettagliato. Ritorna il percorso del file PNG prodotto.",
        inputSchema: {
            type: "object",
            properties: {
                prompt: { type: "string", description: "descrizione dell'immagine, in inglese" },
                width: { type: "number", description: "larghezza px (default 768)" },
                height: { type: "number", description: "altezza px (default 768)" }
            },
            required: ["prompt"]
        }
    },
    {
        name: "analyze_binary",
        description: "Analizza un file binario/eseguibile (.exe/.dll/.sys): tipo, packer, compilatore (Detect-It-Easy), header PE, import/export, sezioni e stringhe rilevanti.",
        inputSchema: {
            type: "object",
            properties: { path: { type: "string", description: "percorso del binario" } },
            required: ["path"]
        }
    },
    {
        name: "delegate_to_hermes",
        description: "Delega un compito complesso e autonomo all'agente Hermes locale (loop completo con skills, memoria e sotto-agenti, modelli uncensored). Utile per analisi profonde o catene di azioni. Ritorna il risultato testuale di Hermes.",
        inputSchema: {
            type: "object",
            properties: { task: { type: "string", description: "il compito da delegare a Hermes, descritto in modo chiaro e completo" } },
            required: ["task"]
        }
    }
];

function send(msg) { process.stdout.write(JSON.stringify(msg) + "\n"); }
function reply(id, result) { send({ jsonrpc: "2.0", id, result }); }
function fail(id, code, message) { send({ jsonrpc: "2.0", id, error: { code, message } }); }

async function callTool(name, args) {
    if (name === "generate_image") {
        const r = await comfy.generate({ prompt: args.prompt, width: args.width, height: args.height });
        return "Immagine generata con successo: " + r.file;
    }
    if (name === "analyze_binary") {
        return analyzeBinary(String(args.path || ""));
    }
    if (name === "delegate_to_hermes") {
        if (!hermes.available()) return "Hermes non è installato su questa macchina.";
        return await hermes.delegate(String(args.task || ""), {});
    }
    throw new Error("strumento sconosciuto: " + name);
}

const rl = readline.createInterface({ input: process.stdin });
rl.on("line", async (line) => {
    line = line.trim();
    if (!line) return;
    let msg;
    try { msg = JSON.parse(line); } catch (_) { return; }
    const { id, method, params } = msg;
    try {
        if (method === "initialize") {
            reply(id, { protocolVersion: "2024-11-05", capabilities: { tools: {} }, serverInfo: { name: "antigravity", version: "1.0.37" } });
        } else if (method === "notifications/initialized") {
            /* notifica: nessuna risposta */
        } else if (method === "tools/list") {
            reply(id, { tools: TOOLS });
        } else if (method === "tools/call") {
            // Gli errori di uno strumento tornano come contenuto (isError), non come
            // errore JSON-RPC: così il modello legge il messaggio e prosegue.
            try {
                const text = await callTool(params.name, params.arguments || {});
                reply(id, { content: [{ type: "text", text: String(text) }] });
            } catch (e) {
                reply(id, { content: [{ type: "text", text: "ERRORE: " + e.message }], isError: true });
            }
        } else if (method === "ping") {
            reply(id, {});
        } else if (id !== undefined) {
            fail(id, -32601, "metodo non supportato: " + method);
        }
    } catch (e) {
        if (id !== undefined) fail(id, -32603, e.message);
    }
});
