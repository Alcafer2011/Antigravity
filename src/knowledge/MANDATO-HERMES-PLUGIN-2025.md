# MANDATO HERMES — SuperAssistentePlugin per ZW3D **2025**
_Scritto da Claude il 2026-07-31. Questo file e' il mandato permanente: se una
sessione si interrompe, si riparte da qui. Aggiornare lo STATO in fondo._

## 0. PRIMA DI TOCCARE QUALSIASI COSA — LEGGI QUESTE
Non andare a memoria. Nell'ordine:
1. `C:\Users\infoa\Antigravity\src\knowledge\zw3d-rules.md` — **obbligatorio**.
   Contiene le regole anti-crash pagate con crash reali, build/deploy verificati,
   prove a freddo/caldo, regole d'officina dell'utente. **Erano irraggiungibili
   fino al 2026-07-31** perche' `hermes-orchestrator.md` puntava a
   `C:\Users\infoa\src\knowledge\` (cartella spostata il 30/07). Percorso corretto ora.
2. `C:\Users\infoa\Antigravity\src\knowledge\ZW3D-WORKLOG.md` — le ultime voci:
   dove si era arrivati.
3. `C:\Users\infoa\Downloads\01_REVERSE_CAD\CENSIMENTO\INVENTARIO_MANCANZE.md` —
   cosa manca sui 6 fronti, con le firme API gia' verificate.

## 1. BERSAGLIO: ZW3D **2025** (decisione utente 2026-07-31)
La 2027 WuKong si fara' in futuro. **Non toccare la 2027 adesso.**

Percorsi (la cartella e' stata RINOMINATA il 31/07: non ha piu' le parentesi,
perche' il tuo tool terminale rifiuta i path con `(` ):
- Plugin: `C:\Users\infoa\Downloads\03_PLUGIN_ZW3D\SuperAssistentePlugin_FINALE_3\FINALE\`
- ZW3D 2025: `C:\Program Files\ZWSOFT\ZW3D 2025\` (header in `api\inc`, esempi in `api\ApiExample`)

## 2. TRE DOCUMENTI CHE MENTONO — non seguirli
- **`README_BUILD.md`** (nel plugin): OBSOLETO. Parla di Visual Studio 2022, di una
  variabile `ZW3D_SDK` e di un `SuperAssistentePlugin.vcxproj` che non esiste.
  Ignoralo: la procedura vera e' §3 qui sotto e §3 di zw3d-rules.md.
- **`build_now.bat`**: nonostante il nome compila i progetti **2027**
  (`*.2027.vcxproj` → `bin2027\`). Per la 2025 NON usarlo.
- **`STATO_CLONE_LOGITRACE.md`**: dichiara "clone lamiera completo" e "icone
  verificate". Sono due affermazioni FALSE (verificato: 29 forme su 209; 6 icone
  in formato sbagliato). Non usarlo come fonte di stato.

## 3. BUILD 2025 (l'unica giusta)
```
MSBuild: "C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe"
vcvars:  "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
Progetti (SENZA suffisso 2027, in quest'ordine):
   SuperAssistenteBridge.vcxproj     ← nel PostBuild rigenera AUTOMAZIONE.zrc con zrc.exe
   SuperAssistenteEngine.vcxproj     ← la DLL con la logica
Parametri: /p:Configuration=Release /p:Platform=x64
Output: bin\x64\Release\
```
**0 errori o non e' fatto.** Codice non compilato = non consegnato.

## 4. DEPLOY 2025 (regole che si dimenticano sempre)
Destinazione `C:\Program Files\ZWSOFT\ZW3D 2025\apilibs\`:
- DLL → `Core\SuperAssistenteEngine.dll`
- `.zrc` compilato (quello in `bin\x64\Release\`, NON il sorgente) → `apilibs\`
- `.tcmd` → `apilibs\Resource\Commands\` **e** le copie sciolte in
  `apilibs\Settings\Default\ResourcePool\`
- ★★ **`.ui` → `apilibs\Resource\Forms\`** — ERRORE COSTATO UNA SERATA il 2026-07-31.
  ZW3D legge le form DA DISCO, non solo dal `.zrc`. Deployando il `.tcmd` ma NON la
  `.ui`, il comando risulta registrato, il template caricato, e cliccando **non
  succede niente**: la finestra da aprire non esiste su disco. Sintomo ingannevole,
  sembra un bug del codice e invece e' il deploy incompleto.
  Erano assenti anche le form di innesto a Y, profilo piegato, scatola e spirale.
  REGOLA: deployare SEMPRE `.tcmd` **e** `.ui` insieme, mai uno solo.
- **Come si diagnostica un comando che "non fa niente"** (metodo che ha funzionato):
  il plugin scrive `%TEMP%\profili_zw3d.txt` all'avvio SOLO se non esiste. Cancellalo,
  avvia ZW3D: se ricompare, l'Engine si carica ed esegue CoreInit fino in fondo →
  il problema NON e' il caricamento ne' la registrazione, ma le risorse. Restringe
  il campo in un minuto invece che a tentativi.
- ⚠️ ZW3D legge i `.tcmd` **da disco**: rigenerare il .zrc NON basta.
- ⚠️ `apilibs` e' CONDIVISA con CamApi/NCTI: **mai wildcard, mai svuotarla, mai
  toccare `languages\`**.
- La DLL si puo' sostituire con ZW3D aperto (gira da copia shadow in %TEMP%), ma
  ZW3D va **riavviato** per caricare DLL/ribbon/.tcmd nuovi.
- Scrivere in Program Files richiede permessi da amministratore.

## 5. I LAVORI, IN QUESTO ORDINE

### PASSO 1 — icone galleria: formato sbagliato (rompe cio' che esiste gia')
Il formato `.icn` e': 8 byte header (larghezza, altezza — due int32 LE), poi i
pixel **RGB interlacciati**, poi in coda il **piano alpha** (1 byte/pixel).
Il layout e' giusto negli script. **La misura no.**
- Funzionano: 18 file a **64x64** (16392 byte) = `g_00..g_15, g_17, g_18`.
- NON si vedono: 6 file a 96x96 (36872 byte) = `g_16, g_19, g_20, g_21, g_22, g_23`
  (innesto Y, spirale, profilo piegato, scatola, barra profilo, staffe) e tutti i
  213 `lt_*.icn` importati da LogiTrace.
- `g_16` ha anche il piano alpha tutto a 255 (opaco): sbagliato due volte.
AZIONE: in `gen_icons_1b.ps1` metti `$S = 64`; in `import_icons_logitrace.ps1`
sostituisci i `96` fissi con 64 (i PNG sorgente sono 96x96, `DrawImage` li
ridimensiona). Rigenera. Verifica con un comando che TUTTI i `.icn` pesino
**16392 byte**. Solo dopo collega le `lt_*` al manifest.

### PASSO 2 — icone AUTOMAZIONE con ComfyUI (richiesta utente 2026-07-31)
L'utente vuole le icone della sezione AUTOMAZIONE **generate da Comfy**, piu'
realistiche e belle di quelle sintetiche attuali.
- Quali: le 17 dichiarate in `Settings\Default\ResourcePool\AUTOMAZIONE.zcui`
  (`analizza_foto, cancello, cutting, distinta, galleria, generate, inferriata,
  preventivo_pro, recinzione, reload, scala, svil_asolatondo, svil_cono,
  svil_dxf, svil_flangia, svil_quadrotondo, svil_tramoggia`).
- ⚠️ **`cutting.png` NON ESISTE** in `icons\`: il bottone e' senza icona. Va creata.
- Formato: PNG (la doc ZW3D dice che le icone personalizzate supportano SOLO png),
  tre misure per ognuna: `nome.png` 64x64, `nome_48.png` 48x48, `nome_32.png` 32x32.
- ⚠️ **BLOCCO NOTO**: `Antigravity\src\comfyClient.js` ha
  `CHECKPOINT = "realisticVisionV60B1_v51HyperVAE.safetensors"` ma in
  `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Shared\models\checkpoints\` ci sono SOLO
  `cyberRealisticPony_v18.safetensors` e `ponyRealism_v23.safetensors`. Cosi'
  com'e' la generazione fallisce con "modello mancante". Scegli uno dei due
  presenti. I sampler del workflow (`dpmpp_sde`+`karras`, pochi passi) sono
  tarati sulla variante Hyper: con i modelli Pony servono piu' passi e cfg
  diverso — **prova su UNA icona, falla vedere all'utente, e solo dopo genera le
  altre 16.** Non bruciare un'ora su 17 immagini sbagliate.
- ComfyUI: locale su `127.0.0.1:8188`, si avvia da solo via `comfyClient.ensureUp()`.
- Le icone generate vanno in `icons\`, e vanno anche copiate nel deploy.

### PASSO 3 — build 2025 pulita + deploy + verifica dell'utente
Compila (§3), deploya (§4), poi CHIEDI ALL'UTENTE di riavviare ZW3D 2025 e dire
se vede le icone. **Questa e' la verifica che vale**: le icone si vedono a occhio,
non serve interpretare log.

### PASSO 4 — messa in tavola (il fronte che manca di piu' all'utente)
`messa_in_tavola.cpp/.h` esistono solo in
`Downloads\02_CODICE_PRODOTTO\codice-cpp-da-advance-steel\` e non sono mai entrati
nel plugin. La logica pura (scala, formati A4-A0, cartiglio) va tenuta com'e'.
API ZW3D **gia' verificate su header** (firma esatta in INVENTARIO_MANCANZE.md §2):
`ZwDrawingViewStandardCreate` (zwapi_drawing_view.h:665), `ZwDrawingViewFullSectionCreate`
(:299), `ZwDrawingViewDetailCreate` (:199), `ZwDrawingDimensionAutoCreate`
(zwapi_drawing_dimension.h:514), `ZwDrawingTableBOMCreate` (zwapi_drawing_table.h:97),
`ZwDrawingRegen` (zwapi_drawing_general.h:302), `ZwExternalPartImport`
(zwapi_dataexchange.h:83). Per **creare il foglio** non esiste API: da chiarire
con ZWSOFT, non inventare.

### PASSO 5 — forme lamiera mancanti (180)
Non sono 180 lavori. Ordine per resa (da FORME_MANCANTI_PRIORITA.md):
`Ellipse` e `RoundedRectangle` in `SheetUnfold` sbloccano la famiglia piu' grossa;
le 22 varianti di gomito sono solo `.tcmd` (il motore `ElbowSegment` c'e' gia' ed
e' testato). Una alla volta: costruttore → test a freddo → comando → build.

## 5bis. CARPENTERIA — la roadmap completa (richiamata dall'utente 2026-07-31)
"Non dimenticate cancelli, recinzioni, balconi, scale." Lo stato NON e' uguale per
tutti: sono tre livelli diversi, verificati nel sorgente il 2026-07-31.

**LIVELLO 1 — disegnano gia' in 3D, manca solo la form nativa**
`Cmd_Cancello`, `Cmd_Recinzione`, `Cmd_Scala` chiamano gia' `ShowWarningsAndDraw()`,
quindi generano geometria vera via `GenerateGeometry()` + `GeometryExecutor`.
Leggono pero' i parametri da un file di testo in `%TEMP%` (`cancello_input.txt`,
`recinzione_input.txt`, `scala_input.txt`) con `LoadParamsFromTemp()`, formato
chiave=valore. Serve solo la form `.tcmd`/`.ui`, sullo schema di `SA_SvilCono`.
★ I NOMI DEI CAMPI SONO GIA' DEFINITI dagli oggetti (usare ESATTAMENTE questi,
non inventarne di nuovi — sono i `SetParameter` accettati):
  `width_mm`, `height_mm`, `total_length_mm`, `panel_max_mm`,
  `baluster_spacing_mm`, `has_mid_rail`, `mid_rail_z_mm`,
  `rise_total_mm`, `going_mm`, `riser_target_mm`, `slope_deg`
Mantenere SEMPRE la lettura da `%TEMP%` come ripiego: se la form non c'e', il
comportamento attuale non deve rompersi.

**LIVELLO 2 — l'inferriata: manca l'oggetto stesso**
Non esiste `InferriataObject`, per questo calcola la distinta ma non disegna.
Vedi il mandato dedicato (crea l'oggetto + form + disegno 3D).

**LIVELLO 3 — non esistono per niente: BALCONE e TETTOIA**
Verificato: nessuna traccia di "balcon"/"tettoi"/"pensilin" nei sorgenti.
Per ognuno serve tutto: `<Nome>Object : ISteelParametricObject` con
`GenerateGeometry()` + `ValidateAgainstNorm()`, il comando, la form, l'icona, la
voce in `AUTOMAZIONE.zcui` + `AUTOMAZIONE_Pages.zcui`.
Il BALCONE e' concettualmente una ringhiera chiusa su 3 lati con un piano
calpestabile: partire da `RailingObject`/`FenceObject`, NON da zero.
Valgono le regole d'officina §6 di zw3d-rules.md (corrente passante, piantone a
piombo, quota = proiezione orizzontale, height_mm = estradosso).

ORDINE CONSIGLIATO (dal piu' vicino al traguardo): inferriata (in corso) →
form per cancello/recinzione/scala (i tre insieme, stesso schema, i campi sono
gia' noti) → balcone → tettoia.

## 5ter. LIBRERIE TOPSOLID — come separare i profili estrudibili dalle forme 3D
Scoperto e VALIDATO il 2026-08-01. Le librerie esportate contengono due cose
diverse mescolate: PROFILI a sezione costante (estrudibili su una retta, come
vuole il weldment profile di ZW3D) e FORME 3D vere (ornamenti ferro battuto, che
nessuna estrusione ricostruisce).

**Il criterio non richiede un kernel CAD.** I file STEP sono testo: basta leggere
quali TIPI DI SUPERFICIE contengono.
- solo `PLANE` + `CYLINDRICAL_SURFACE` → **PROFILO ESTRUDIBILE** (prisma con raccordi)
- compare `B_SPLINE_SURFACE`, `TOROIDAL_SURFACE`, `CONICAL_SURFACE`,
  `SPHERICAL_SURFACE` o `SURFACE_OF_REVOLUTION` → **FORMA 3D**, non estrudibile
Validato su due casi reali: Jansen `600.001 (56 x 50 x 1.5).step` = 17 PLANE +
10 CYLINDRICAL → estrudibile; Grande Forge `Posted Collection Castel.step` =
27 PLANE + 4 B_SPLINE → 3D vero.

Materiale: `Downloads\TopSolid_Export\librerie\`, 84 cartelle. DXF e STEP in
sottocartelle separate. **3806 nomi in comune** fra DXF e STEP: sono quelli su cui
si lavora, perche' avere entrambi permette il confronto 2D vs 3D.
Librerie chiave: `TopSolid Jansen`, `TopSolid Forster` (serramento/acciaio),
`TopSolid Grande Forge` (ferro battuto ornamentale).

I gusci weldment sono i 18 `.Z3` in `ZW3D 2025\languages\it_IT\resource\weldment
profiles\ISO\`: sono CONTENITORI, le misure sono le ROOT dentro (1424). Si leggono
solo da dentro ZW3D con `cvxRootList` (+`cvxMemFree`). ⭐ L'utente ne ha gia' creato
uno suo, `CORRIMANO FERRO.Z3`: e' la prova che la procedura manuale esiste ed e' il
modello da studiare per capire come si crea una famiglia e ci si inserisce un disegno.

## 5quater. LAVORO AUTONOMO — il runner notturno
`Downloads\03_PLUGIN_ZW3D\_LAVORO_NOTTURNO\` contiene `runner.ps1`, la cartella
`coda\` (mandati numerati, eseguiti in ordine) e `coda_prioritaria\`.
Il runner: fa uno SNAPSHOT dei sorgenti prima di ogni mandato → lancia Hermes
ruotando sui 4 modelli Nous free finche' uno risponde → **compila** → se la build
e' rotta RIPRISTINA lo snapshot e passa oltre. Log in `log\`, esito in
`log\_RIEPILOGO.md`. Non deploya mai: `Program Files` non si tocca senza sorveglianza.
⚠️ LANCIARLO con un meccanismo TRACCIATO. Un `Start-Process ... -WindowStyle Hidden`
staccato NON sopravvive alla fine del comando che lo crea: il 2026-07-31 e' andata
persa una notte intera cosi'. **Dopo l'avvio, VERIFICARE che `log\_runner.log`
esista e cresca**, prima di dichiarare che sta lavorando.

## 5quinquies. DUE DIFETTI TROVATI SU UN CANCELLO VERO (2026-08-01)
Prova fatta dall'utente sul suo disegno reale "Cancello Pontecurone":
`Distinta` → 135 corpi, 20 righe, 159 kg, CSV in `%TEMP%\distinta_completa.csv`.

**DIFETTO 1 — la distinta NON legge i profili, legge gli INGOMBRI.**
Le righe uscivano come `353x3`, `333x24`, `74x64`, `21x18`, `61x18`: sono bounding
box dei corpi, non nomi di profilo. `GeometryReader::BuildDistinta` deduce la
"sezione" dalla scatola che contiene il corpo. Conseguenze:
 - un tubo tagliato a 45 gradi ha una scatola PIU' GRANDE della sua sezione, quindi
   il nome esce sbagliato;
 - **non si puo' ordinare materiale con questi nomi**: al fornitore serve un profilo
   normalizzato, non "74x64".
 ⚠️ NOTA — errore di Claude da non ripetere: avevo scritto che nel cancello mancava
 il `30x30x2`. Sbagliato: il 30x30x2 e' il telaio delle INFERRIATE (R021), nei
 CANCELLI non si usa mai. La regola era giusta, l'ho applicata alla tipologia
 sbagliata. Prima di dedurre qualcosa da una regola, controllare il campo
 `vale_per`.
CORREZIONE: leggere il profilo dalla FEATURE WELDMENT (categoria + misura), non
dalla geometria. Ora e' possibile: la sequenza `!CdWeldStruct` e la struttura dei
contenitori `.Z3` sono note (zw3d-rules.md §5). Dove il corpo NON e' un membro
weldment, la deduzione da ingombro resta come ripiego, ma va MARCATA come stimata.

**DIFETTO 2 — i risultati devono vivere DENTRO ZW3D, non in %TEMP%.**
Parole dell'utente: "Distinta non deve solo darmi un output così e io devo andare a
cercarlo, tutto deve essere fruibile dentro ZW con i suoi cartigli se serve".
Un CSV in una cartella temporanea non e' un risultato utilizzabile da un fabbro che
sta disegnando. La distinta, l'ordine materiale e il preventivo devono comparire
come TABELLE sul foglio disegno, con il cartiglio.
Le API ci sono e sono gia' verificate (INVENTARIO_MANCANZE.md §2):
`ZwDrawingTableBOMCreate` (zwapi_drawing_table.h:97) per la distinta nativa,
`ZwDrawingViewStandardCreate` / `...FullSectionCreate` / `...DetailCreate` per le
viste, `ZwDrawingDimensionAutoCreate` per le quote.
Il CSV resta, ma come EXPORT accessorio: non come unico risultato.

## 6. REGOLE DI CONDOTTA (non negoziabili)
1. **Mai inventare una funzione ZW3D.** Se non e' in un header, non esiste.
   Copia la firma da `zw3d-api-index-locale.tsv` o dall'header, con file e riga.
   Inventarla = far crashare ZW3D dell'utente, che ci lavora davvero.
2. **Mai dire "fatto" per qualcosa che non hai scritto su disco.** Rileggi il file
   dopo aver scritto e confermalo con un conteggio/grep. "Non ci sono riuscito
   perche' X" e' una risposta ACCETTATA; un "fatto" falso no — viene sempre
   controllato e costa un giro in piu' a tutti.
3. **Se un tuo strumento viene bloccato, dillo.** Non fingere di aver eseguito.
4. **Regole anti-crash di zw3d-rules.md §1**: niente `cvxPart*` di creazione forma,
   uscire dagli schizzi solo con `cvxRootExit()`, `RequirePart` prima di creare
   geometria, `ZwCommandFunctionUnload` per ogni comando in CoreExit, SEH attorno
   alle creazioni forma, niente funzioni @deprecated.
5. **Regole d'officina (zw3d-rules.md §6)**: sono vincoli di produzione reali, non
   si "migliorano" di testa propria.
6. **Diario obbligatorio**: a ogni intervento scrivi una voce in
   `knowledge\ZW3D-WORKLOG.md` (data reale, file toccati, build OK/errori, prova
   fredda/calda, stato, prossimo passo). Se rompi qualcosa annota il SINTOMO
   esatto e l'ultima modifica prima del guasto.
7. **Niente cartelle `[FileCR]`** (Tekla, ZW3D Wukong scaricati): contengono crack,
   restano fuori dal progetto. Di Tekla serve solo la logica per vie lecite.
8. Non toccare `C:\Users\infoa\Antigravity` senza motivo: e' il codice vivo
   dell'estensione. Se un automatismo deve riscrivere file li' dentro, passa da
   `cantiere.guardia()`.

## 7. STATO — aggiornare a ogni sessione
- 2026-07-31: censimento chiuso e verificato (209 forme, 29 fatte). Cartella
  rinominata senza parentesi. Percorsi knowledge riparati. Difetto formato icone
  diagnosticato (64x64, non 96). Blocco checkpoint Comfy diagnosticato.
  **Prossimo passo: PASSO 1 (icone .icn a 64x64).**
