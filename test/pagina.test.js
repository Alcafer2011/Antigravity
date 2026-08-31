"use strict";
// I test della PAGINA. Tutti nascono da guasti veri, gia' successi:
// due volte renderMd e' finito in un ciclo infinito che ha sfondato il limite
// di stringa di V8 e ha bloccato il telefono (19/07 fine-riga CRLF, 31/08
// tabelle). Ogni caso qui sotto e' uno di quei bug, congelato perche' non
// possa tornare senza che qualcuno se ne accorga.
const { test } = require("node:test");
const assert = require("node:assert");
const { caricaRenderMd } = require("./_aiuto.js");

const renderMd = caricaRenderMd();

/** Rende e fallisce se ci mette troppo o produce una montagna di HTML:
 *  sono i due sintomi con cui si manifesta un ciclo che non avanza. */
function rendiInSicurezza(testo, etichetta) {
    const t0 = Date.now();
    const html = renderMd(testo);
    const ms = Date.now() - t0;
    assert.ok(ms < 1000, etichetta + ": ci ha messo " + ms + " ms (ciclo che non avanza?)");
    assert.ok(html.length < 100000, etichetta + ": HTML da " + html.length + " caratteri (ciclo che non avanza?)");
    return html;
}

test("tabella completa: resta una tabella", () => {
    const html = rendiInSicurezza("| a | b |\n|---|---|\n| 1 | 2 |", "tabella completa");
    assert.match(html, /<table>/);
});

test("tabella a meta' durante lo streaming: non blocca la pagina", () => {
    // Il caso che uccideva il telefono: la riga di intestazione arriva prima
    // del separatore, e nel mezzo la pagina veniva ridisegnata.
    rendiInSicurezza("| Nome | Righe |", "intestazione da sola");
});

test("ogni prefisso di una tabella e' sicuro (simula lo streaming carattere per carattere)", () => {
    const risposta = "Ecco:\n\n| File | Righe |\n|------|-------|\n| a.js | 12 |\n| b.js | 34 |\n\nFine.";
    for (let n = 1; n <= risposta.length; n++) rendiInSicurezza(risposta.slice(0, n), "prefisso di " + n);
});

test("riga con la barra ma senza separatore: diventa testo, non un ciclo", () => {
    rendiInSicurezza("| ciao", "barra non chiusa");
    rendiInSicurezza("| a | b |\n| 1 | 2 |", "tabella senza separatore");
});

test("fine-riga di Windows (CRLF): il titolo resta un titolo — guasto del 19/07", () => {
    const html = rendiInSicurezza("### Titolo\r\ntesto\r\n", "CRLF");
    assert.match(html, /<h3>/);
});

test("blocco di codice non chiuso: non manda in loop", () => {
    rendiInSicurezza("```js\nconst a = 1;", "codice non chiuso");
});

test("liste, citazioni e righe orizzontali continuano a funzionare", () => {
    const html = rendiInSicurezza("- uno\n- due\n\n> citazione\n\n---\n\n1. primo", "misto");
    assert.match(html, /<ul>/);
    assert.match(html, /<ol>/);
    assert.match(html, /<blockquote>/);
    assert.match(html, /<hr>/);
});
