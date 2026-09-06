"use strict";
// LA CINTURA DI SICUREZZA DELL'APPARECCHIO 8K (05/09/2026).
//
// Serve a far lavorare sul box QUALSIASI modello — anche uno piccolo, anche
// distratto — senza che possa fare danni irreparabili. Come sempre in questo
// progetto, ogni caso qui sotto nasce da un guasto vero:
//
//   * il 05/09 un comando storto ha svuotato a 0 byte la lista dei canali del
//     box (157 KB -> 0). Si e' salvata solo grazie a un backup fatto a mano un
//     minuto prima. Da qui: backup automatico + rifiuto delle scritture che
//     rimpiccioliscono troppo un file.
//   * lo stesso giorno Kodi e' stato riavviato a TV spenta ed e' rimasto
//     parcheggiato a meta' avvio, sembrando riavviato. Da qui: il divieto.
//   * op="comando" con root e' una shell aperta: la conferma dell'utente non
//     protegge (si legge "sistemo la cache" e si preme si'). Da qui: la lista
//     nera, che vale ANCHE se l'utente conferma.
const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("fs");
const path = require("path");

const SRC = path.join(__dirname, "..", "src");
const sorgente = fs.readFileSync(path.join(SRC, "ultrahd8k.js"), "utf8");

/** La lista nera si prova isolata: non serve il box acceso per collaudarla. */
function caricaFiltro() {
    const inizio = sorgente.indexOf("const COMANDI_VIETATI");
    const fine = sorgente.indexOf("class UltraHD8K");
    assert.ok(inizio > 0 && fine > inizio, "la lista nera dei comandi non c'e' piu'");
    // eslint-disable-next-line no-eval
    return eval(sorgente.slice(inizio, fine) + "\ncomandoVietato");
}

// ── 1. I comandi che distruggono l'apparecchio non passano ──────────────────

test("comandi distruttivi: BLOCCATI", () => {
    const vietato = caricaFiltro();
    const devono_essere_fermati = [
        "rm -rf /data/data/org.xbmc.kodi",
        "rm -rf /storage/emulated/0/.kodi",
        "rm -rf /sdcard/Download/vecchi",
        "rm -rf /system/app/qualcosa",
        "dd if=/dev/zero of=/dev/block/mmcblk0",
        "chmod -R 777 /system",
        "pm uninstall com.android.settings",
        "settings put global adb_enabled 0",
        "svc wifi disable",
        "reboot bootloader",
        "mkfs.ext4 /dev/block/data",
    ];
    for (const c of devono_essere_fermati) {
        const motivo = vietato(c);
        assert.ok(motivo, "NON bloccato (e dovrebbe): " + c);
        assert.ok(motivo.length > 20, "il motivo deve spiegare, non solo dire di no: " + c);
    }
});

// ── 2. Il lavoro normale deve continuare a passare ──────────────────────────
// Una protezione che blocca anche il lavoro buono viene tolta dopo due giorni.

test("lavoro normale: PASSA (niente falsi allarmi)", () => {
    const vietato = caricaFiltro();
    const devono_passare = [
        "cat /sys/class/thermal/thermal_zone0/temp",
        "pidof org.xbmc.kodi",
        "am force-stop org.xbmc.kodi",
        "am start -n org.xbmc.kodi/.Splash",
        "echo antigravity_8k > /sys/power/wake_lock",
        "ls -la /storage/emulated/0/Download",
        "rm -f /data/local/tmp/ponte.tmp",
        // /data/local/tmp e' la cartella di appoggio: li' si fa pulizia
        "rm -rf /data/local/tmp/pann",
        "rm -rf /data/local/tmp/pann && cp -a x y",
        // Kodi si puo' disinstallare: e' il nostro, non un pacchetto di sistema
        "pm uninstall org.xbmc.kodi",
    ];
    for (const c of devono_passare) {
        assert.equal(vietato(c), null, "bloccato per sbaglio: " + c);
    }
});

// ── 3. La shell del modello passa dal filtro, non da sh() ───────────────────

test("op='comando' passa da comando() (filtrata), non da sh() (grezza)", () => {
    const agente = fs.readFileSync(path.join(SRC, "nativeAgent.js"), "utf8");
    const pezzo = agente.slice(agente.indexOf('case "comando"'), agente.indexOf('case "comando"') + 600);
    assert.ok(/b\.comando\(/.test(pezzo),
        "op='comando' deve chiamare b.comando(): con b.sh() la lista nera viene scavalcata");
    assert.ok(!/return await b\.sh\(String\(args\.comando/.test(agente),
        "e' tornata la chiamata diretta a sh(): la protezione e' scavalcata");
});

// ── 4. Le scritture fanno backup e rifiutano il rimpicciolimento ────────────

test("ogni scrittura sul box fa PRIMA un backup .ag-bak-*", () => {
    const f = sorgente.slice(sorgente.indexOf("async _scriviRemoto"),
                             sorgente.indexOf("async apiAccendi"));
    assert.ok(/ag-bak-/.test(f), "il backup automatico non c'e' piu'");
    assert.ok(/Non riesco a fare il backup/.test(f),
        "se il backup fallisce NON si deve scrivere lo stesso");
    assert.ok(f.indexOf("ag-bak-") < f.indexOf("push"),
        "il backup deve venire PRIMA di caricare il file nuovo");
});

test("scrittura molto piu' piccola del file esistente: RIFIUTATA", () => {
    const f = sorgente.slice(sorgente.indexOf("async _scriviRemoto"),
                             sorgente.indexOf("async apiAccendi"));
    assert.ok(/SCRITTURA RIFIUTATA/.test(f), "manca il rifiuto sul rimpicciolimento");
    assert.ok(/forza/.test(f), "deve esistere una via d'uscita esplicita (forza:true)");
    assert.ok(/nuovaDim < vecchiaDim \* soglia/.test(f), "manca il confronto delle dimensioni");
});

test("dopo la scrittura si RILEGGE la dimensione dal box", () => {
    const f = sorgente.slice(sorgente.indexOf("async _scriviRemoto"),
                             sorgente.indexOf("async apiAccendi"));
    assert.ok(/Scrittura sospetta/.test(f),
        "«ho scritto» non e' una prova: va riletto quanto c'e' davvero sul box");
});

// ── 5. Kodi non si riavvia a schermo spento ─────────────────────────────────

test("kodi_avvia e kodi_riavvia si fermano se la TV e' spenta", () => {
    assert.ok(/NON AVVIO KODI/.test(sorgente), "manca la guardia su kodiAvvia");
    assert.ok(/NON RIAVVIO KODI/.test(sorgente), "manca la guardia su kodiRiavvia");
    const riavvia = sorgente.slice(sorgente.indexOf("async kodiRiavvia"),
                                   sorgente.indexOf("async kodiRiavvia") + 900);
    assert.ok(riavvia.indexOf("schermoAcceso") < riavvia.indexOf("kodiFerma"),
        "il controllo va fatto PRIMA di fermare Kodi: fermarlo e non riuscire a " +
        "riavviarlo e' il modo peggiore di scoprire che la TV era spenta");
});

// ── 6. Il modello deve SAPERE che le protezioni esistono ────────────────────

test("la descrizione dello strumento avvisa il modello delle protezioni", () => {
    const agente = fs.readFileSync(path.join(SRC, "nativeAgent.js"), "utf8");
    assert.ok(/PROTEZIONI ATTIVE/.test(agente),
        "senza avviso il modello prova, viene bloccato, e ci gira intorno all'infinito");
    assert.ok(/NON cercare la strada di lato/.test(agente),
        "va detto esplicitamente di fermarsi, non di aggirare il blocco");
});
