"use strict";
// Estrae una funzione dalla pagina mobile per poterla provare in node.
// mobile-page.html non e' un modulo: la pagina e' un file solo, e riscriverla
// per i test sarebbe un rischio piu' grande del test stesso. Qui la funzione
// viene ritagliata dal sorgente VERO (non da una copia), cosi' il test misura
// il codice che gira davvero sul telefono.
const fs = require("fs");
const path = require("path");

const PAGINA = path.join(__dirname, "..", "src", "mobile-page.html");

function estraiFunzione(nome) {
    const src = fs.readFileSync(PAGINA, "utf8");
    const inizio = src.indexOf("function " + nome + "(");
    if (inizio < 0) throw new Error("funzione '" + nome + "' non trovata in mobile-page.html");
    // La chiusura e' la prima "}" a inizio riga dopo l'apertura (stile del file).
    const fine = src.indexOf("\n}", inizio);
    if (fine < 0) throw new Error("fine di '" + nome + "' non trovata");
    return src.slice(inizio, fine + 2);
}

/** renderMd pronto all'uso, con gli aiutanti minimi che gli servono. */
function caricaRenderMd() {
    const corpo = estraiFunzione("renderMd");
    const aiutanti = `
        function esc(s){ return String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }
        function inline(s){ return esc(s); }
        function mdTable(righe){ return "<table>" + righe.length + "</table>"; }
    `;
    // eslint-disable-next-line no-new-func
    return new Function(aiutanti + corpo + "\nreturn renderMd;")();
}

module.exports = { estraiFunzione, caricaRenderMd, PAGINA };
