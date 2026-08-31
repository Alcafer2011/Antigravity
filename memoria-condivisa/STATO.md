# STATO — memoria condivisa Antigravity

> Questo file è il cervello comune. **Lo leggono e lo scrivono tutti**: Claude Code,
> l'Hermes lanciato da Claude, l'Hermes che lanci tu da PowerShell.
> Regola unica: **prima di lavorare lo leggi, dopo aver lavorato lo aggiorni.**
> Non serve raccontare a voce cosa è successo: sta scritto qui.

---

## 0. ⚠️ LEGGERE PRIMA — LA CAUSA VERA (2026-08-06)

**Le sezioni 1 e 2-bis qui sotto NON spiegano il guasto del telefono. Sono vere ma
non erano la causa.** Il 06/08 la RAM era a posto (10 GB liberi, **zero** browser
orfani) e il telefono non funzionava lo stesso.

**Causa provata: il ping del server era un COMMENTO SSE.**
`mobileServer.js` mandava `res.write(": ping\n\n")` ogni 20 s. Una riga che comincia
con `:` è un commento: **per specifica non fa scattare `onmessage`**. Quindi il
client non aggiornava mai `lastBeat` a chat ferma, e il suo watchdog (soglia 9 s)
dichiarava morto un canale sanissimo.

Misurato dal vivo, 45 s di chat FERMA: **4 riconnessioni, 1490 KB di history
riscaricata**, una ogni ~11 secondi. Ogni riconnessione rimanda `history` →
`renderHistory` → `clearThread()`, che **azzera `streamEl` e cancella la risposta
mentre la stai leggendo**. Poi `streamEnd` non trova più niente, `running` resta
`true` per sempre e `#send` resta inchiodato su **■**: il tocco dopo chiama `/stop`
invece di inviare. **Ecco perché "clicco al massimo un pulsante e poi non va niente".**

**Il watchdog nato il 05/08 per curare il canale morto era esso stesso il guasto.**

**Correzioni applicate (backup `*.bak-prima-ping-20260806`):**
1. `mobileServer.js` — ping = `data: {"type":"ping"}` **ogni 5 s** (evento vero);
2. `mobile-page.html` — soglia watchdog 9 s → **20 s** (2 punti);
3. `mobile-page.html` — `case "history"` **non ridisegna se `streamEl` è attivo**;
4. `mobile-page.html` — `case "ping": break;` no-op.

**Verificato dopo il riavvio:** 45 s di chat ferma → **1 sola connessione, 373 KB**
(erano 4 e 1490 KB). Ping osservati sul filo a +5s, +10s, +15s come `data:`.

### La scatola nera mentiva — e nascondeva gli errori veri

I 20 `BLOCCO` nel log del 05/08 sono **falsi**: tutti da `Electron` (VS Code, non il
telefono), tutti `visibile:"hidden"`, tutti ~59000 ms esatti a 60 s di distanza. È il
browser che a scheda nascosta rallenta i timer a 1 al minuto — non un congelamento.
Peggio: `segnala()` ha un tetto di **20 invii**, e quei 20 falsi allarmi lo
esaurivano → **gli errori VERI dopo di loro sparivano in silenzio.** Corretto: il
blocco si segnala solo con `document.visibilityState === "visible"`.

> **Regola per chi indaga dopo:** un `BLOCCO` con `visibile:"hidden"` va ignorato, e
> un UA con `Electron` **non è il telefono**. Il telefono è `iPhone ... Safari`.

---

## 0-bis. SECONDA CAUSA, TROVATA COL TELEFONO CHE PARLA (2026-08-06)

Corretto il ping, **dal telefono non funzionava ancora**. Aggiunta una tracciatura
che il telefono manda al server (`prontoJS`, `TOCCO`, `canaleAperto`, `apiKO`,
`historyResa`, tutti con `versione`). Risultato dal vero iPhone:

```
apertura     {"schermo":"430x932"}
prontoJS     {"canale":0,"haSend":true,"haInput":true,"haMenu":true,"nodiPagina":173}
canaleAperto {}
TOCCO        {"id":"llmProvider","tag":"SELECT","sopra":"#llmProvider"}
TOCCO        {"id":"(senza id)","tag":"DIV","testo":"📂 Studia un progetto"}
   ...poi SILENZIO TOTALE. Mai più niente.
```

**Cosa dimostra:** lo script arriva in fondo (`prontoJS`), i pulsanti SONO collegati,
il canale SI apre, e i tocchi ARRIVANO al JavaScript (`sopra` = il bersaglio giusto,
quindi nessun velo invisibile). Poi la pagina smette di esistere. **Il silenzio è il
sintomo**: quando il thread principale muore non resta nessuno che possa segnalarlo —
ecco perché in 3 giorni non è mai comparso un errore.

**Causa: la cronologia scaricata all'apertura del canale.** Misurata:
**194 messaggi, 359.513 caratteri (~351 KB)**, di cui **due messaggi da 101.814
caratteri l'uno**. `renderHistory` li disegna in un ciclo **sincrono** con parsing
markdown a regex su stringhe da 100 KB → su iPhone il thread si inchioda, la pagina
resta disegnata ma non risponde, poi Safari uccide la scheda.

**Correzione:** nuovo `_historyForView()` in `mobileServer.js` — **solo per la
vista**: ultimi 40 messaggi, tetto 6000 caratteri per messaggio, **l'ultimo messaggio
utente mai troncato** (lo rispedisce `regenerate()`: troncarlo corromperebbe il
prompt). `a.messages`, `/history` ed esportazione restano completi: l'agente vede
tutto. Verificato: **359.513 → 26.526 caratteri, 194 → 41 messaggi**.

### ✅ CONFERMATO DAL TELEFONO — 2026-08-06 09:44

```
historyResa {"messaggi":41,"caratteri":26526,"ms":28,"nodiPagina":604}
```

**28 ms** per disegnare la cronologia (prima: 359.513 caratteri in un ciclo sincrono).
E soprattutto **20 tocchi consecutivi dalle 09:44:48 alle 09:45:36 — 48 secondi di uso
continuo senza un attimo di silenzio** (menu, ricerca modelli, campo di testo,
scorrimento). Prima erano 2 tocchi e poi il nulla per sempre.
Zero `BLOCCO`, zero `apiKO`, zero errori. **L'utente conferma: "adesso sembra che
funziona".**

**✅ GIRO COMPLETO PROVATO — 09:45.** In `mobile-conversations.json`:
`[USER] Ciao` → `[ASSISTANT] Ciao! Come posso aiutarti oggi?` (provider "tutti /
auto"). La conversazione ora ha **196 messaggi in memoria**: la cronologia completa è
intatta, il taglio riguarda solo il disegno. **Attenzione al metodo:** `/send` NON
lascia una riga nel log — cercarlo lì e concludere "non è stato inviato" è sbagliato;
la prova sta in `mobile-conversations.json`.

**Il watchdog ora fa il suo mestiere vero:** alle 09:45:58 `canaleErrore`
(readyState 0) = caduta reale del canale, riconnesso e ridisegnato in **3,4 secondi**.
Prima sparava di continuo su canali sani; ora scatta solo quando serve.

**Rese misurate sul telefono:** 28 / 95 / 34 / 33 ms su 4 aperture. Stabile.

**Corretta anche la strumentazione (stessa trappola di stamattina):** i tetti di invio
ora sono DUE e separati — chiacchiere (tocchi/aperture) max 60, eventi seri
(errori/blocchi/canale caduto) max 200. Con un tetto unico gli eventi abbondanti
mangiavano il budget e gli errori veri sparivano: **il guasto cancellava le proprie
tracce, e il log vuoto veniva letto come "nessun errore".**

**Nota per chi arriva dopo:** `/vivo` è una rotta pubblica senza token né JS, per
distinguere "la rete non arriva" da "la pagina non si disegna".
**Su Safari un indirizzo digitato a mano viene tentato in https:// e fallisce** —
il server è solo http. L'icona nella Home funziona perché ha l'http:// salvato dentro.

---

## 1. DIAGNOSI DEL 2026-08-04 (vera, ma NON era questa la causa)

**Sintomo:** Antigravity si apre (telefono e VS Code), la pagina appare, ma i pulsanti
non rispondono e poi tutto crasha.

**Causa: NON è un bug di Antigravity. È la RAM del PC finita.**

Misurato il 2026-08-04 alle 10:30 su questa macchina (31,8 GB di RAM):

| cosa | quanti processi | RAM |
|---|---|---|
| **chrome.exe orfani** | **527 (66 browser distinti)** | **24,9 GB** |
| node.exe (server MCP) | 63 | 4,9 GB |
| Code.exe (VS Code) | 16 | 3,1 GB |
| claude.exe | 11 | 2,0 GB |

Restavano **7,6 GB liberi** su 31,8 con oltre 37 GB richiesti → Windows va in
compressione/swap, tutto si blocca.

**Da dove vengono i 66 browser orfani:** ognuno ha un profilo temporaneo suo,
`%TEMP%\agent-browser-chrome-<uuid>`, e il padre è `explorer.exe` (= sono orfani,
chi li ha aperti è morto senza chiuderli). Sono i browser degli agenti
(browser tool / automazioni), **mai chiusi a fine sessione, accumulati per giorni**.
Non sono il Chrome con cui navighi tu: quello ha il profilo di default, e va lasciato stare.

**Perché sembra colpa di Antigravity:**
- il server mobile su :8790 è vivo e a macchina scarica risponde in **129 ms**;
- sotto saturazione la stessa pagina ci ha messo **oltre 17 secondi** ad arrivare;
- il telefono riceve l'HTML lento e incompleto, disegna la grafica ma gli `addEventListener`
  in fondo allo script non arrivano mai → **si vede tutto, non si clicca niente**;
- poi Safari/Electron uccide la scheda per memoria → **crash**.

**Cosa è stato ESCLUSO con prova diretta (non ricontrollare, è tempo buttato):**
- ✅ sintassi dei 3 script inline di `mobile-page.html`: `node --check` passa, nessun errore;
- ✅ nessuna eccezione JS in console (solo due 401 su `/favicon.ico`, innocui);
- ✅ tutte le rotte a caldo sono veloci: `/` 129 ms, `/models` 110 ms, `/cantiere` 4 ms,
  `/kaggle/quota` 1 ms, `/piattaforme/scelte` 255 ms, `/bugHunter/queue` 3 ms;
- ✅ il server mobile risponde 200, il log non ha crash.

**Difetto minore, vero ma non è questo il crash:** `/models` restituisce **185 KB**
(~1500 modelli) e `fillModels()` costruisce tutte le `<option>` in un colpo solo.
Su iPhone pesa. Da sistemare **dopo**, non adesso — vedi Lavori aperti.

---

## 2. LA CURA

```powershell
& "C:\Users\infoa\Antigravity\memoria-condivisa\ag.ps1" diagnosi   # guarda
& "C:\Users\infoa\Antigravity\memoria-condivisa\ag.ps1" pulisci    # libera la RAM
& "C:\Users\infoa\Antigravity\memoria-condivisa\ag.ps1" guardia    # non succede più
```

`guardia` installa un'operazione pianificata che ogni 30 minuti chiude i browser
orfani. È **il fix definitivo**: senza, si riaccumulano da soli in un paio di giorni.

> **`ag guardia` devi lanciarlo tu, a mano, una volta sola.** Il classificatore di
> sicurezza di Claude Code non permette agli agenti di registrare operazioni
> pianificate. Non è un errore da indagare: è così di proposito.

### Come si scrive `ag` e basta

Il comando è nel profilo PowerShell (`Documenti\PowerShell\profile.ps1`): apri un
terminale **nuovo** e scrivi `ag diagnosi`, `ag pulisci`, o solo `ag` per l'elenco.
Se il profilo non fosse caricato, il percorso per esteso qui sopra funziona sempre.

---

## 2-bis. SECONDA CAUSA — il menu modelli (2026-08-04, dopo "si blocca ancora")

Liberata la RAM, l'app si bloccava ancora. Seconda misurazione, a PC scarico:

- la pagina si carica in **211 ms**, l'evento `load` scatta regolarmente;
- inviando un messaggio il thread principale **non si ferma mai**
  (120 battiti su 120 attesi, pausa massima 116 ms) → su Chrome desktop funziona;
- **ma `#model` conteneva 1534 `<option>`.** Su iPhone toccare quel menu apre la
  ruota nativa con 1534 righe: Safari smette di rispondere e poi uccide la scheda.
  È il "si vede tutto, non si clicca niente, poi crasha" **sul telefono**.

**Correzione applicata** in `mobile-page.html` (backup:
`mobile-page.html.bak-prima-modelli-20260804`):
- tetto di **15 modelli per provider** (200 se scegli un provider preciso);
- nuova casella **🔎 cerca modello** (`#modelCerca`) che filtra su **tutto** il
  catalogo: nessun modello è irraggiungibile, cambia solo come lo trovi;
- il modello già scelto resta nell'elenco anche se il tetto lo escluderebbe.

Verificato dopo la modifica: menu da **1534 a 243 voci**, nodi pagina da **3396 a
2106**, ricerca "qwen" → 202 risultati. Sintassi ricontrollata con `node --check`: OK.

> **Sul telefono va ricaricata la pagina** (chiudi la scheda e riapri dal link),
> altrimenti Safari continua a usare la versione vecchia in cache.

### Se si blocca ancora: la scatola nera

Un congelamento **non è un errore JS** — nessun handler lo vedeva, ed è per questo
che nel log comparivano solo le aperture. Ora dentro la pagina c'è un battito da 1
secondo: se il thread principale salta più di 3 secondi, appena torna a respirare
segnala **quanto è stato fermo e qual è stato l'ultimo gesto toccato**.

```powershell
ag blocchi     # <-- dopo che si e' bloccato, lancia questo
```

Mostra ora, dispositivo (TELEFONO / VS CODE), secondi di blocco, ultimo gesto e
quante voci aveva il menu. **Con quell'output la causa si trova senza rifare
l'indagine da capo.**

---

## 3. LAVORI APERTI (in ordine)

- [ ] **Provare dal telefono** dopo il fix del ping (2026-08-06). Chiudere la scheda
      e riaprire dal link: Safari tiene in cache la pagina vecchia.
- [x] ~~Blocco telefono~~ — causa trovata e corretta il 2026-08-06, vedi sezione 0.
- [x] ~~Alleggerire `/models`~~ — fatto il 2026-08-04, vedi 2-bis.
- [ ] **`renderMd` può esplodere su risposte lunghissime** — latente, non urgente.
      Nel log del **2026-08-04 09:32** (da VS Code, non dal telefono):
      `Uncaught RangeError: Invalid string length` in `renderMd` ← `paintAssist`
      ← `_flushPaint`, cioè **durante lo streaming**. Significa che la stringa
      costruita dal markdown ha superato la lunghezza massima ammessa da JS: su una
      risposta molto lunga la pagina muore a metà scrittura. Non si è più ripresentato
      e non c'entra col guasto di oggi, ma è un difetto vero, trovato solo perché ora
      il log non viene più svuotato dai falsi allarmi. Da limitare con un tetto alla
      dimensione del testo passato a `renderMd`.
- [ ] **Favicon** — il server risponde 401 su `/favicon.ico` perché la rotta pretende
      il token. Aggiungere `/favicon.ico` alle rotte pubbliche in `mobileServer.js`.
      Cosmetico, due righe.

## 4. FATTI

- **2026-08-04** — Diagnosi chiusa (sopra). Creata questa memoria condivisa + `ag.ps1`.
- **2026-08-04** — **Pulizia eseguita:** 65 browser orfani / 520 processi chiusi,
  70 profili temporanei rimossi. RAM libera passata da **7,4 a 12,1 GB**.
  Chrome sceso da 527 processi a 7 (solo quelli in uso). Il server mobile risponde
  in **73 ms**. Manca solo `ag guardia`, da lanciare a mano.
- **2026-08-04** — Aggiunto `ag` al profilo PowerShell.
- **2026-08-04** — Menu modelli portato da 1534 a 243 voci + casella di ricerca.
  Aggiunta la scatola nera dei blocchi nella pagina e il comando `ag blocchi`.
  Corretto `ag apri`: prima sceglieva l'IP dello switch virtuale Hyper-V
  (172.28.x), che dal telefono non è raggiungibile. Ora ordina
  **Tailscale (100.x) → Wi-Fi → schede virtuali**, e segnala quali non funzionano.
  Server mobile riavviato: serve la pagina nuova.

## 5. DIARIO
<!-- ag nota "..." scrive qui sotto. Non cancellare questa riga. -->
- **2026-08-04 10:37** — diagnosi: 7,4 GB liberi su 31,8, 65 browser orfani (24,36 GB), node 63
- **2026-08-04 10:38** — pulisci: chiusi 65 browser orfani, ~24,36 GB liberati
- **2026-08-04 10:42** — diagnosi: 12,8 GB liberi su 31,8, 0 browser orfani (0 GB), node 63
- **2026-08-04 10:51** — diagnosi: 15,8 GB liberi su 31,8, 0 browser orfani (0 GB), node 62
- **2026-08-04 10:59** — server mobile riavviato
- **2026-08-05 11:24** — diagnosi: 9,6 GB liberi su 31,8, 5 browser orfani (1,88 GB), node 23
- **2026-08-05 11:24** — pulisci: chiusi 5 browser orfani, ~1,88 GB liberati
- **2026-08-05 11:24** — guardia installata (pulizia automatica ogni 30 min)
- **2026-08-05 11:25** — pulisci -anche node: chiusi 20 processi MCP
- **2026-08-05 11:27** — server mobile riavviato
- **2026-08-05 11:30** — testo
- **2026-08-06** — CAUSA VERA TROVATA: ping SSE era un commento → watchdog riconnetteva
  ogni 11 s → clearThread cancellava la risposta → #send bloccato su ■. Corretto e
  verificato (4 riconnessioni → 1). I 20 "BLOCCO" del 05/08 erano falsi. Vedi sezione 0.
