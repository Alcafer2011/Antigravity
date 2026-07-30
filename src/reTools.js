"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");
const { execSync } = require("child_process");

// Strumenti RE conosciuti (percorsi reali sulla macchina). Condivisi tra
// l'agente nativo e il server MCP.
const RE_TOOLS = {
    diec: "C:\\RE-Tools\\die\\die\\diec.exe",
    ghidra: "C:\\ProgramData\\chocolatey\\lib\\ghidra\\tools\\ghidra_12.1.2_PUBLIC\\support\\analyzeHeadless.bat"
};

/** Analisi completa di un binario usando la toolchain RE installata. */
function analyzeBinary(fp) {
    const parts = [];
    const run = (cmd) => {
        try {
            return execSync(cmd, { encoding: "utf8", maxBuffer: 8 * 1024 * 1024, timeout: 60000, windowsHide: true });
        } catch (e) { return (e.stdout || "") + (e.stderr || e.message || ""); }
    };
    if (!fp || !fs.existsSync(fp)) return "ERRORE: il binario non esiste: " + fp;

    // 1) Detect-It-Easy: tipo/packer/compilatore.
    if (fs.existsSync(RE_TOOLS.diec)) {
        const die = run(`"${RE_TOOLS.diec}" "${fp}"`);
        parts.push("### Detect-It-Easy (tipo/packer/compilatore)\n" + (die || "(nessun output)").trim());
    }
    // 2) pefile: header PE, sezioni, import/export.
    const py = "import sys,pefile\n" +
        "pe=pefile.PE(sys.argv[1], fast_load=True)\n" +
        "pe.parse_data_directories()\n" +
        "print('Machine:', hex(pe.FILE_HEADER.Machine), '| 64-bit:', pe.FILE_HEADER.Machine==0x8664)\n" +
        "print('DLL:', bool(pe.FILE_HEADER.Characteristics & 0x2000), '| Subsystem:', pe.OPTIONAL_HEADER.Subsystem)\n" +
        "print('EntryPoint:', hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint), '| ImageBase:', hex(pe.OPTIONAL_HEADER.ImageBase))\n" +
        "print('Sezioni:'); [print(' ', s.Name.decode(errors='ignore').strip('\\x00'), 'vsize', hex(s.Misc_VirtualSize)) for s in pe.sections]\n" +
        "imps=getattr(pe,'DIRECTORY_ENTRY_IMPORT',[])\n" +
        "print('Import DLL:', ', '.join(e.dll.decode(errors='ignore') for e in imps) or '(nessuno)')\n" +
        "for e in imps[:8]:\n" +
        "  fns=[ (i.name.decode(errors='ignore') if i.name else 'ord%d'%i.ordinal) for i in e.imports[:15]]\n" +
        "  print('  '+e.dll.decode(errors='ignore')+':', ', '.join(fns))\n" +
        "exp=getattr(pe,'DIRECTORY_ENTRY_EXPORT',None)\n" +
        "print('Export:', ', '.join((s.name.decode(errors='ignore') if s.name else 'ord%d'%s.ordinal) for s in exp.symbols[:30]) if exp else '(nessuno)')\n";
    const pyFile = path.join(os.tmpdir(), "antigravity_pe.py");
    try {
        fs.writeFileSync(pyFile, py, "utf8");
        const peOut = run(`python "${pyFile}" "${fp}"`);
        if (peOut && !/No module named|not recognized|Errno/.test(peOut)) {
            parts.push("### PE header / import / export (pefile)\n" + peOut.trim());
        } else if (peOut) {
            parts.push("### pefile\n(pefile non disponibile o errore: " + peOut.trim().slice(0, 200) + ")");
        }
    } catch (_) {}
    // 3) Stringhe stampabili rilevanti (fallback nativo).
    try {
        const buf = fs.readFileSync(fp);
        const strs = [];
        let cur = "";
        for (let i = 0; i < buf.length && strs.length < 60; i++) {
            const c = buf[i];
            if (c >= 32 && c < 127) { cur += String.fromCharCode(c); }
            else { if (cur.length >= 6) strs.push(cur); cur = ""; }
        }
        const interesting = strs.filter(s => /\.(dll|exe|sys)$|http|key|licen|passw|regist|error|version|\\\\/i.test(s)).slice(0, 30);
        parts.push("### Stringhe rilevanti\n" + (interesting.join("\n") || strs.slice(0, 20).join("\n")));
    } catch (_) {}
    const out = parts.join("\n\n");
    return out.length > 40000 ? out.slice(0, 40000) + "\n…[troncato]" : (out || "Nessuna analisi disponibile (toolchain RE non trovata).");
}

module.exports = { analyzeBinary, RE_TOOLS };
