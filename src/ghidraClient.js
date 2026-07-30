"use strict";

const http = require("http");
const { URL } = require("url");

/**
 * GhidraClient — ponte HTTP verso il plugin GhidraMCP (LaurieWired) che gira
 * DENTRO Ghidra ed espone un server HTTP (default http://127.0.0.1:8080/).
 *
 * Permette all'agente di Antigravity — pilotato da QUALSIASI provider/modello
 * cloud (OpenRouter/Groq/HuggingFace/Gemini, modelli grossi uncensored/codex) —
 * di fare reverse engineering LIVE sul programma aperto in Ghidra: elencare e
 * decompilare funzioni, cercare, leggere stringhe/import/export, rinominare,
 * commentare, seguire le xref. È l'equivalente "nativo" di ciò che GhidraMCP
 * offre via MCP a Claude, ma qui usabile dai tuoi altri modelli.
 *
 * Nessuna dipendenza esterna: solo il modulo http di Node.
 *
 * Config: GHIDRA_SERVER nel .env (default http://127.0.0.1:8080/).
 */
class GhidraClient {
    constructor(opts = {}) {
        const raw = opts.server || process.env.GHIDRA_SERVER || "http://127.0.0.1:8080/";
        this.base = raw.endsWith("/") ? raw : raw + "/";
        this.timeout = opts.timeout || 15000;
    }

    _request(method, endpoint, { query, body, contentType } = {}) {
        return new Promise((resolve, reject) => {
            let u;
            try { u = new URL(endpoint.replace(/^\//, ""), this.base); } catch (e) { return reject(e); }
            if (query) for (const [k, v] of Object.entries(query)) {
                if (v !== undefined && v !== null) u.searchParams.set(k, String(v));
            }
            const data = body != null ? Buffer.from(body, "utf8") : null;
            const req = http.request({
                hostname: u.hostname, port: u.port || 80, path: u.pathname + u.search,
                method,
                headers: Object.assign(
                    { "Accept": "text/plain" },
                    data ? { "Content-Type": contentType || "application/x-www-form-urlencoded", "Content-Length": data.length } : {}
                )
            }, (res) => {
                let chunks = "";
                res.setEncoding("utf8");
                res.on("data", (c) => { chunks += c; if (chunks.length > 200000) req.destroy(); });
                res.on("end", () => {
                    if (res.statusCode >= 200 && res.statusCode < 300) resolve(chunks.trim());
                    else resolve("ERRORE " + res.statusCode + ": " + chunks.trim());
                });
            });
            req.setTimeout(this.timeout, () => { req.destroy(new Error("timeout")); });
            req.on("error", (e) => {
                // Il caso tipico: Ghidra non aperto o server non avviato.
                if (/ECONNREFUSED|timeout|ECONNRESET/.test(e.message)) {
                    resolve("GHIDRA_OFFLINE: nessuna risposta dal server GhidraMCP su " + this.base +
                        ". Apri Ghidra, carica un programma nel CodeBrowser e assicurati che il plugin GhidraMCP sia attivo (menu Tool → GhidraMCP HTTP Server su porta 8080).");
                } else reject(e);
            });
            if (data) req.write(data);
            req.end();
        });
    }

    _get(endpoint, query) { return this._request("GET", endpoint, { query }); }
    _postForm(endpoint, obj) {
        const body = Object.entries(obj).map(([k, v]) => encodeURIComponent(k) + "=" + encodeURIComponent(v == null ? "" : v)).join("&");
        return this._request("POST", endpoint, { body });
    }
    _postRaw(endpoint, text) { return this._request("POST", endpoint, { body: String(text), contentType: "text/plain" }); }

    // ---- Lettura (sicure, non mutano il programma) ------------------------
    async ping() {
        const r = await this._get("get_current_program").catch(() => null);
        // get_current_program potrebbe non esistere in tutte le build: proviamo methods.
        if (r && !/GHIDRA_OFFLINE|ERRORE 404/.test(r)) return r || "(programma aperto)";
        const m = await this._get("methods", { offset: 0, limit: 1 });
        if (/GHIDRA_OFFLINE/.test(m)) return m;
        return "Ghidra ONLINE. Server: " + this.base;
    }
    listFunctions(offset = 0, limit = 200) { return this._get("methods", { offset, limit }); }
    searchFunctions(query, offset = 0, limit = 100) { return this._get("searchFunctions", { query, offset, limit }); }
    decompileByName(name) { return this._postRaw("decompile", name); }
    decompileByAddress(address) { return this._get("decompile_function", { address }); }
    disassemble(address) { return this._get("disassemble_function", { address }); }
    listStrings(offset = 0, limit = 200, filter) { return this._get("strings", filter ? { offset, limit, filter } : { offset, limit }); }
    listImports(offset = 0, limit = 200) { return this._get("imports", { offset, limit }); }
    listExports(offset = 0, limit = 200) { return this._get("exports", { offset, limit }); }
    listClasses(offset = 0, limit = 200) { return this._get("classes", { offset, limit }); }
    listSegments(offset = 0, limit = 200) { return this._get("segments", { offset, limit }); }
    xrefsTo(address, offset = 0, limit = 100) { return this._get("xrefs_to", { address, offset, limit }); }
    xrefsFrom(address, offset = 0, limit = 100) { return this._get("xrefs_from", { address, offset, limit }); }
    functionXrefs(name, offset = 0, limit = 100) { return this._get("function_xrefs", { name, offset, limit }); }
    listNamespaces(offset = 0, limit = 200) { return this._get("namespaces", { offset, limit }); }
    listDataItems(offset = 0, limit = 200) { return this._get("data", { offset, limit }); }
    getFunctionByAddress(address) { return this._get("get_function_by_address", { address }); }
    getCurrentAddress() { return this._get("get_current_address"); }
    getCurrentFunction() { return this._get("get_current_function"); }

    // ---- Scrittura (mutano il programma: passano dal gate di approvazione) --
    renameFunction(oldName, newName) { return this._postForm("renameFunction", { oldName, newName }); }
    renameFunctionByAddress(function_address, new_name) { return this._postForm("rename_function_by_address", { function_address, new_name }); }
    renameData(address, newName) { return this._postForm("renameData", { address, newName }); }
    renameVariable(functionName, oldName, newName) { return this._postForm("renameVariable", { functionName, oldName, newName }); }
    setDecompilerComment(address, comment) { return this._postForm("set_decompiler_comment", { address, comment }); }
    setDisassemblyComment(address, comment) { return this._postForm("set_disassembly_comment", { address, comment }); }
    setFunctionPrototype(function_address, prototype) { return this._postForm("set_function_prototype", { function_address, prototype }); }
    setLocalVariableType(function_address, variable_name, new_type) { return this._postForm("set_local_variable_type", { function_address, variable_name, new_type }); }
}

module.exports = { GhidraClient };
