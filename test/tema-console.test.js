"use strict";
// I test del TEMA «console» (2026-09-01). Il restyling è stato applicato per
// RITEMATIZZAZIONE (variabili CSS + ambiente vivo) proprio per non toccare la
// struttura né le funzioni: questi test presidiano che quella scelta regga, e
// soprattutto che NESSUNA funzione dell'app sia sparita nel ridipingere.
const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");

const page = fs.readFileSync(path.join(__dirname, "..", "src", "mobile-page.html"), "utf8");

test("l'ambiente vivo esiste (aurore + griglia) e sta dietro tutto", () => {
    assert.match(page, /id="ambiente"/, "manca il livello ambiente");
    assert.match(page, /#ambiente\s*\{[^}]*z-index:0/, "l'ambiente non è più dietro il contenuto");
    assert.match(page, /@keyframes auraA/, "le aurore non derivano più (movimento a pagina ferma perso)");
    assert.match(page, /@keyframes gridScroll/, "la griglia in prospettiva non scorre più");
});

test("la palette dei DATI resta quella validata (ciano/ambra/rosso)", () => {
    // Sono i colori passati al validatore daltonismo: non devono cambiare per capriccio.
    assert.match(page, /--ok:#3FBF8F/i, "il verde 'gratis/ok' non è più quello validato");
    assert.match(page, /--warn:#E0A44A/i, "l'ambra 'costa' non è più quella validata");
    assert.match(page, /--err:#E85D5D/i, "il rosso 'esaurito' non è più quello validato");
    assert.match(page, /--sig:#45C8D8/i, "il ciano 'macchina' non è più quello validato");
});

test("il tema chiaro dell'iPhone non è rotto: ha i suoi ripieghi", () => {
    assert.match(page, /html\.phone\[data-theme="light"\] header\{background:var\(--panel\)/,
        "in tema chiaro l'header resterebbe scuro (vetro non ribaltato)");
    assert.match(page, /html\.phone\[data-theme="light"\] #ambiente\{display:none\}/,
        "l'ambiente non è nascosto in tema chiaro: aurore su fondo bianco");
});

test("NESSUNA funzione persa: header, drawer e comandi ci sono ancora", () => {
    // Ogni pulsante/pannello che c'era prima del restyling deve esserci ancora:
    // il tema ridipinge, non rimuove.
    for (const id of ["menuBtn", "torBtn", "musicBtn", "keysBtn", "resumeBtn",
                      "clearBtn", "exportBtn", "newChat", "themeBtn"]) {
        assert.match(page, new RegExp('id="' + id + '"'), "sparito il comando #" + id + " nel restyling");
    }
    // I pannelli/funzioni maggiori.
    for (const id of ["keysDrawer", "resumeDrawer", "modelDrawer", "torPanel", "musicPanel"]) {
        assert.match(page, new RegExp('id="' + id + '"'), "sparito il pannello #" + id + " nel restyling");
    }
    // Le corsie e la barra Kaggle restano.
    assert.match(page, /id="provider"/, "sparito il selettore modalità");
    assert.match(page, /id="model"/, "sparito il modello (fonte di verità nascosta)");
});
