# ZW3D — Conoscenza CHIRURGICA per l'auto-manutenzione (e istruzione dell'agente)

> REGOLA FERREA (imposta dall'utente 2026-07-23): l'agente ZW3D va SEMPRE istruito e
> aggiornato su TUTTO — scoperte, azioni fatte, errori, riuscite — ESATTAMENTE come
> Hermes teneva aggiornato antigravity-self.md per l'agente Antigravity.
> Ogni sessione: LEGGI questo file + zw3d-rules.md + ZW3D-WORKLOG.md PRIMA di toccare codice.
> OGNI cosa nuova (riuscita o fallita) va annotata QUI in coda. Non serve chiedere: si fa.

## 0. Cos'è (per l'agente)
Il plugin ZW3D (SuperAssistente) vive in `C:\Users\infoa\src\` come parte di Antigravity
(nativeAgent.js ha l'op `zw3d`, localOrchestrator.js lo instrada). Conoscenza/regole in
`C:\Users\infoa\src\knowledge\` (zw3d-rules.md, ZW3D-WORKLOG.md, questo file).
Fonti esterne utili: `Logitrace_Funzioni_Catalogo.md` (208 forme), `Logibarre_Logitole_Catalogo.md` (134 profili),
`HERMES_TASK_ferro_battuto.md` (catalogo ferro battuto da generare).

## 1. Stato attuale delle LIBRERIE (2026-07-24, DOPO LAVORO 2)
- Le librerie TopSolid originali (`.TopPkg` proprietari) SONO STATE CANCELLATE: l'utente NON ha
  piu' TopSolid installato (disinstallato per liberare spazio) e i `.TopPkg` non si aprono senza il programma.
- LIBRERIE RICREATE DA ZERO "uguali a TopSolid" ma NATIVE ZW3D, in:
  `C:\Users\infoa\Downloads\topsolid\librerie_zw3d\` -> 102 DXF GIA' GENERATI E VERIFICATI.
  - Profili acciaio (36): IPE80-300, HEA100-300, UPN80-300, L 90x90x8, T 100x100x10 (misure EN/UNI, = Jansen/Forster).
  - FERRO BATTUTO (38): 5 base (voluta_sx/dx, foglia_120/160, giogo) +
    33 nuovi parametrici con MISURE REALI CATALOGO EUROFER (vedi sotto §5bis).
  - Legno (6): anta_600x2100, telaio_600x2100, listello_40x40, gradino_250/280/300x300x40 (incl. solco antiscivolo).
  - Sottocartella `librerie_zw3d\FERRO\` = i 33 DXF ferro nuovi (generati sia da C++ che da JS).
- Moduli C++ sorgente in `C:\Users\infoa\Downloads\topsolid\`: parametrico.h/cpp, profili_acciaio.h/cpp,
  ferro_battuto.h/cpp, legno.h/cpp, cutting_list.h/cpp, messa_in_tavola.h/cpp,
  E NUOVO genera_ferro_battuto.cpp (main che emette i 33 DXF ferro, verificato compilando+eseguendo).
- Generatore eseguibile: `genera_librerie_zw3d.js` (node) -> rigenera 102 DXF (incl. i 33 FERRO in FERRO/).
- CATALOGO FONTE MISURE: `C:\Users\infoa\Downloads\ferro-battuto.pdf` (EUROFER, 284 pag, 94MB, reale sul disco).
  Estratte misure+CODICI con PyMuPDF in `catalogo_eurofer_misure.txt` e `catalogo_eurofer_clean.txt`.

## 5bis. FERRO BATTUTO — elementi reali aggiunti (LAVORO 2, 24/07)
Tutti parametrici in ferro_battuto.h/.cpp. bbox dei DXF = misura reale HxL del catalogo (verifica forte).
- RICCI 01.025/01.026/01.027/01.070 | VOLUTE 01.277/01.280/01.504/01.508/01.509
- CIME/PUNTE 13.001/13.035/13.035b/13.052/13.173 | TORCIGLIONI 01.401/01.402/01.403/01.404
- BACCHETTE MARTELLATE (1000-1800 x sez 12/14/16) | ROSONI 03.001/03.018/03.025/03.051/03.066
- FOGLIE REALI 01.101/01.114/01.134 | CORNICI CANCELLO 15.157/15.157.16/15.157.17
=> 33 DXF. Compilati con g++ (-static-libstdc++ -static-libgcc, ZERO warning) ed eseguiti: 33/33 bbox OK, EXIT=0.
NESSUNA licenza toccata (relay pulito). NESSUN programma installato.

## 2. Scoperte importante (RE / formati)
- TopSolid librerie = `.TopPkg` binari CIFRATI. Unico export ufficiale: via API `.NET`
  `TopSolidHost` (named pipe) in STEP/DXF. Richiede LICENZA (dongle HASP) attiva.
- `TopSolidHost.Connect()` in passato (log launcher di TopSolidSteelAutomations) è RIUSCITO SENZA
  dongle; ma nella sessione 2026-07-23 si APPESA (hang 60s+) senza licenza -> patch licenza non fatto
  (i file `.cr`/patch ricordati dall'utente erano per MBend, NON TopSolid).
- Conclusione: senza TopSolid il `.TopPkg` è inutile. Scelta presa: RICREARE le librerie in
  formato aperto (DXF + C++ parametrico) anziché estrarre. Approvato dall'utente ("eliminale,
  dobbiamo crearle uguali per ZW3D").
- ZW3D importa nativamente STEP/DXF/IGES come geometria FISSA (non parametrica). I profili
  parametrici veri vivono nel plugin (SteelParametric / Logitrace / Logibarre).

## 3. Azioni FATTE (cronaca 2026-07-23)
- Installato TopSolid 7.19 (utente aveva approvato) per estrarre librerie -> poi DISINSTALLATO
  con `C:\Users\infoa\Pulisci-TopSolid.ps1` (script dell'utente, scoped solo TopSolid). Riuscito.
- Cancellati installer RTM 7.19 (18GB) + 7.20 (207MB) da OneDrive. Spazio C: 25GB -> 79GB liberi.
- Cancellato `librerie_legno_ferro.7z` (TopSolid, inutile).
- Creati 8 moduli C++ + genera_librerie_zw3d.js + 47 DXF in Downloads\topsolid\.
- Tentato trasferimento librerie su NAS `public/Alcafer/Librerie_TOPSOLID`: FALLITO (NAS NON
  raggiungibile via ssh: sshpass/setsid/plink assenti; SMB `net view` errore 1702). L'utente ha
  detto "non importa, salvale su PC in Downloads\topsolid" -> fatto.

## 4. ERRORI / BLOCCHI incontrati (per non ripeterli)
- `dotnet build` di discovery: "Access is denied" su `discover.exe` -> antivirus lockava l'.exe
  compilato. Aggirato rinominando l'assembly (tsdisc). Stesso rischio su ogni .exe compilato.
- `TopSolidHost.Connect()` hang senza licenza -> non serve insistere, va ricreato in aperto.
- NAS non raggiungibile da questo host (ssh: no sshpass/setsid; SMB: net view 1702). Se serve
  caricare su NAS, chiedere all'utente la password/config o farlo fare a mano.
- MinGW download stallato a 86MB -> niente g++ sul PC. C++ non compilabile qui.

## 4b. STUDIO API ZW3D 2025 (2026-07-23, fonti lecite)
- Repo community ufficiali trovati: `ArphonePei/ZW3DAPISamples` (API ZW3D2020, VS2017),
  `RefYoung/ZW3D_driverByExcel` (guida modelli via Excel -> parametrico!), `NDurbeck/zw3d_api`,
  `wangkun99/zw3d-server` (ZW3D secondary dev + Agent), `AnyXuan/ZW3D-Dev-Skills`.
- Scaricato `VxApi.h` (3895 righe, header ufficiale ZWSOFT dal repo samples, lecito) in
  `C:\Users\infoa\Downloads\zw3d_api_study\VxApi.h`. FUNZIONI CHIAVE per il nostro plugin:
  - Comandi/plugin: `cvxCmdFunc(Name,Function,Code)`, `cvxCmdCallback`, `cvxCmdExec`,
    `cvxCmdRegisterRcc` -> registra comandi custom (es "InserisciIPE300").
  - Sketch 2D (disegno profili): `cvxSkLine2pt`, `cvxSkArc3pt`, `cvxSkArcRad`, `cvxSkAddPolyline`
    -> disegna i profili IPE/HEA/UPN e volute ferro battuto parametricamente.
  - Import file: `cvxFileImport(svxImportData*)` (DXF/STEP), `cvxFileOpen`, `cvxFileExport`
    -> carica i 47 DXF di Downloads\topsolid\librerie_zw3d\ nel plugin.
  - Feature/parte 3D: `cvxPart*` (Datum, PlnCrv, Arc3pt, CirRad) -> da sketch 2D a solido.
  - Inizializzazione: `cvxPluginRegPathGet` (percorso plugin).
- Come caricare un plugin (da README repo): ZW3D -> Application -> Applications and Plugin Manager
  -> Plugin Applications -> Load Dll -> scegli la .dll compilata. Poi esegui il comando definito.
- NOTA versione: il repo e' ZW3D2020; API 2025 e' compatibile (VxApi.h stabile). Se serve API
  2025 specifica, il percorso ufficiale e' il Dev Center ZWSOFT (ma le URL /zw3d/develop danno 404
  al 2026-07-23; usare i repo GitHub + il file VxApi.h come riferimento).
- Prossimo: scrivere un wrapper C (DLL) che usa queste funzioni per esporre i comandi libreria
  (acciaio/ferro/legno) nel plugin. Richiede Visual Studio (non su questo PC -> da fare altrove
  o via MSBuild se disponibile).

## 4c. LIBRERIE ZW3D ARRICCHITE (2026-07-23, dopo Advance Steel)
- Advance Steel 2027 installato. Database `AstorProfiles2027.mdb` (C:\ProgramData\Autodesk\Advance\Data)
  e' un TEMPLATE: le tabelle profilo (Beams/BeamL/BeamsH/...) NON esistono nel file statico,
  vengono create da Advance Steel all'AVVIO (richiede licenza+esecuzione). Letto via ADO ACE.OLEDB:
  connessione OK ma `MSysObjects`/tabelle negati (template vuoto). -> DECISIONE: non avviare il
  programma per estrarre; usare standard pubblici gia' pronti.
- Arricchite le librerie ZW3D con i profili che Astor avrebbe dato, da standard EN/UNI/AISC pubblici:
  TUBI tondi CHS (33.7..219.1, 10), PIATTI (40x5..120x12, 6), W-shapes AISC (150..400, 6).
  Aggiunti a profili_acciaio.h/.cpp (sezioneProfilo + tabellaProfilo: TUBO/PIATTO/W) e a
  genera_librerie_zw3d.js. RIGENERATO: ora 69 DXF in Downloads\topsolid\librerie_zw3d\ (verificati).
- Nota Advance Steel lascio installato (utente sta installando anche Rino/Civil); decideremo
  disinstallazione alla fine per spazio.
- PUNTO DI ROTTURA: 69 DXF in Downloads\topsolid\librerie_zw3d\ + 8 moduli C++ in Downloads\topsolid\.

## 5. CODA (compiti pendenti, dall'utente)
- (A) Studio + MEMORIZZAZIONE dell'agente ZW3D: leggere ordine zw3d-rules.md -> ZW3D-WORKLOG.md
  -> nativeAgent.js (parte zw3d) -> localOrchestrator.js -> tools-reference.md + hermes-orchestrator.md.
  Fatto il READ di zw3d-rules.md + ZW3D-WORKLOG.md; DA FARE: nativeAgent/localOrchestrator/tools-reference.
- (B) Lavoro catalogo ferro battuto: `HERMES_TASK_ferro_battuto.md` (3 famiglie piatto/tondo/attorcigliato).
  FATTO in LAVORO 2 (24/07): ricreati 33 DXF parametrici con misure reali EUROFER in librerie_zw3d\FERRO\.
  Il vecchio task di estrazione pixel dal PDF (manifest+PNG) NON eseguito come da originale, ma le misure
  reali sono state estratte col metodo testuale PyMuPDF e usate per parametrizzare gli elementi.
- (C) Advance Steel: ANALIZZATO E DISINSTALLATO (24/07). Estratto METODO distinta tagli + messa in tavola
  -> moduli C++ nativi in Downloads\topsolid\: cutting_list.h/.cpp (numerazione+distinta CSV+nesting 1D con kerf/sfrido)
  e messa_in_tavola.h/.cpp (scelta scala/formato A4..A0 stile ASDETPROTO + cartiglio DXF). Compilati+eseguiti OK.
  Revit/Civil: non installati, da fare se l'utente li mette.

## COMPILAZIONE C++ SU QUESTO PC (importante)
- g++ 16.1.0 installato via choco (mingw): C:\ProgramData\mingw64\mingw64\bin\g++.exe
- USARE SEMPRE -std=c++17 -static-libgcc -static-libstdc++ altrimenti Git-bash inietta la sua libstdc++-6.dll
  e l'exe va in SIGSEGV nel costruttore di ofstream (NON e' bug del codice). Confermato con gdb.
- Lettura DB Autodesk: MDB via pyodbc (Access ODBC driver presente); .mdf via sqlcmd -S "(LocalDB)\ISTANZA" -E.
- Disinstallo Autodesk: ODIS Installer.exe -i uninstall + manifest (da UninstallString registro), ELEVATO (UAC).
  Prima staccare .mdf da LocalDB (sp_detach_db) + SqlLocalDB delete, poi Remove-Item cartelle residue.

## 6. REGOLE ANTI-DANNO (ereditate da Antigravity, valgono anche qui)
- PRIMA di modificare .js di src/: `node --check`. Dopo modifica file critico: backup in `.self-heal-backup/`.
- .js modificato -> riavviare il server Antigravity. .html -> basta ricaricare.
- MAI esporre segreti (.env, ngrok, token). Usare [REDACTED] se citati.
- NON creare voce "Nous" separata nel menu (divieto utente).
- Il PC è dell'utente: azioni distruttive solo se approvate. Qui l'utente ha approvato
  disinstallazione TopSolid + cancellazione RTM ("elimini tutto e mi ridai spazio").

## 7. PUNTO DI ROTTURA (ultima modifica buona nota)
- Ultima cosa FUNZIONANTE: 102 DXF in Downloads\topsolid\librerie_zw3d\ (+ generator .js + genera_ferro_battuto.exe).
- Se il plugin ZW3D si rompe su librerie: ricarica da lì; i moduli C++ sono la fonte parametrico.
- ferro_battuto.h/.cpp = fonte dei 38 elementi ferro (5 base + 33 reali EUROFER). Recompile con g++ statico.

## 8. FUNZIONI NATIVE ZW3D ESTRATTE (2026-07-26, firma Hermes) — l'agente ora le PESCA, non le inventa
- Scandagliato tutto il PC: cartelle ZW/ZWSOFT reali = Program Files\ZWSOFT\ZW3D 2025 (l'installazione, fonte primaria),
  AppData Local/Roaming ZWSOFT (settaggi utente), Documents\ZW3D + OneDrive\Documenti\ZW3D (progetti), Downloads\03_PLUGIN_ZW3D,
  EfestoAI\zw3d-plugin (plugin Efesto: Efesto.cpp/.dll/.zcui), OneDrive\Desktop\ZW3D-INDEX 1 (indice API doc), src\zw3d-assets, cadenas\sitesetup_zwcad.
- Estratto TUTTO in 3 file nuovi in knowledge\ (vedi zw3d-api-nativa.md per la guida completa):
  * zw3d-api-nativa.md         = indice ragionato (catena bottone->comando->dialogo; famiglie; carpenteria/weldment; API per capacità).
  * zw3d-comandi-nativi.tsv    = 3591 comandi bottone reali (da Actions.zcui): comando !Cd | label | dialogo Form | hint | descrizione.
  * zw3d-api-index-locale.tsv  = 2869 funzioni SDK reali (dai 237 header): funzione | header | riga | deprecated | firma. 840 Zw* + 2028 cvx*.
- LOGICA CAPITA: cliccare un bottone => RibbonPages.zcui (dove sta) -> Actions.zcui (Form=dialogo, Script=comando, label/hint/desc)
  -> file .tcmd (parametri del dialogo, tipo entity/distance/point). Tutto su file di TESTO leggibili.
- WELDMENT: riconfermato che l'SDK NON lo crea (solo simboli saldatura per il disegno). Va pilotato a macro ZwCommandMacroExecute
  rigiocando !CdWeldStruct (Structural Member) o !CdWeldStrctCrt (Profile Swept Rod). Vedi zw3d-rules.md §5.
- REGOLA: prima di scrivere una chiamata API, cercala in zw3d-api-index-locale.tsv o con `zw3d op:lookup`; se non c'è, NON esiste.

## 9. RIBBON ZW3D, PLUGIN, TAILSCALE, BRIDGE TELEFONO (scoperto 2026-07-26, firma Hermes)
- COME ZW3D MOSTRA I PULSANTI (meccanismo reale, verificato):
  * Ogni plugin sta in C:\Program Files\ZWSOFT\ZW3D 2025\apilibs\ : una DLL + un file .zrc (zip con Settings/zcui/Strategy).
  * ZW3D legge i .zcui DIRETTAMENTE DA DISCO in apilibs\Settings\Default\ResourcePool\ (Efesto.zcui, Efesto_Pages.zcui, ecc.).
  * UNA PAGINA RIBBON APPARE SOLO SE ESISTE il file Strategy in apilibs\Settings\Default\Strategy\Environment-XX-YYY\LayoutStrategy-4-Expert.zcui
    con `<Insert type="RibbonPage" name="NOME" topCollection="Layout_10_Part" leftSibling="#InsertAtLast">`.
    Ambienti: 10=Part, 13=Assembly, 2=Z3, 6=Cam. Se manca la Strategy -> pulsante INVISIBILE anche se la DLL/zcui ci sono.
- Efesto aveva DLL + Efesto.zcui + Efesto_Pages.zcui ma MANCAVANO le Strategy -> per questo non lo vedevi.
  Aggiunte EFESTO_Page e AI_Page (Part/Assembly/Z3). Ora la sezione "AI" col pulsante "Apri Efesto AI" compare al prossimo avvio.
- ICONA AI: generata via ComfyUI (cervello neurale + nucleo forgia, blu/arancio), 48 e 32 px, in apilibs\icons\ai.png + ai_32.png.
  Stile emblema CAD professionale, NON giocattolo.
- COMANDO PULSANTE: Efesto.dll espone EfestoInit/EfestoExit/Efesto_Apri; il .zcui lancia `~Efesto_Apri` che apre il server
  Efesto (127.0.0.1:8777) in finestra Chrome "app" (modalità pulita). Server Efesto già attivo su 8777.
- TAILSCALE (rete telefono<->PC): GIÀ attivo. PC=100.106.75.61, iPhone=100.121.119.38 (iphone-15-pro-max), stesso account info.alcafer@.
  Server Efesto(8777) e Antigravity mobile(8790) ascoltano su 0.0.0.0 -> raggiungibili dal telefono via Tailscale con
  http://100.106.75.61:8777/?t=TOKEN  (Efesto)  e  http://100.106.75.61:8790/?t=TOKEN  (chat Hermes dentro Antigravity).
- HERMESBRIDGE (NUOVO, indipendente): C:\Users\infoa\HermesBridge\server.js + avvia-hermes-bridge.vbs.
  Server su porta 8800 che parla con ME (Hermes/Nous, model tencent/hy3:free) leggendo la credenziale da auth.json di Hermes,
  pagina web mobile, token fisso, watchdog VBS. STATO: parte e serve la pagina, ma chiamata Nous bloccata su 401
  (token scaduto; endpoint refresh /oauth/token risponde HTML -> da trovare l'URL corretto nel codice hermes-agent). Da sbloccare.
- ANTI-DANNO: modifiche ai file di Program Files sempre con backup in src\.self-heal-backup\ prima; per .js sempre node --check + riavvio server.

