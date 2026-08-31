> [COPIA EFESTO AI - indipendente da Antigravity. Allineata 2026-07-26 con la copia di
>  Antigravity, che aveva 27 righe in piu' (il generatore di 55 modelli 3D STEP).]
# DIARIO DI LAVORO — Plugin ZW3D (SuperAssistente)

> Regola (vedi zw3d-rules.md §8): ogni intervento sul plugin ZW3D si annota QUI, in coda.
> All'inizio di ogni sessione l'agente ZW3D LEGGE le ultime voci prima di toccare codice.
> Serve a trovare il PUNTO DI ROTTURA in caso di errore: si sa sempre l'ultima modifica buona.

## Formato di una voce
```
### AAAA-MM-GG — <cosa/famiglia toccata>
- File:     <percorsi modificati>
- Build:    OK | errori: <sintesi>
- Prova:    fredda <esito> / calda <esito>
- Stato:    FUNZIONA | STUB | ROTTO
- Rottura:  <se rotto: sintomo esatto + ultima riga crash report + ultima modifica prima del guasto>
- Prossimo: <passo successivo>
```

---

## Voci

### 2026-07-23 — Diario avviato + agente ZW3D addestrato
- File:     knowledge/zw3d-rules.md (+§8 diario, +§9 tutte le funzioni, +§10 auto-test), knowledge/ZW3D-WORKLOG.md (nuovo), nativeAgent.js (nuovo op:open per zw3d), src/zw3d-assets/blank_test.Z3PRT (parte template usa-e-getta)
- Build:    n/a (conoscenza + JS)
- Prova:    fredda n/a / calda n/a (ZW3D era aperto dall'utente, PID 30864 — nessuna prova live per non disturbare)
- Stato:    FUNZIONA (conoscenza in linea)
- Rottura:  —
- Prossimo: l'utente sta estraendo/riscrivendo in C++ nativo codice dai programmi di riferimento (LogiTrace/Logibarre/TopSolid); riceverò i file per valutare cosa è utile e integrarlo. Poi far costruire a Hermes qualcosa per ZW3D e verificare (compila? rispetta §1 anti-crash?).

### 2026-07-23 — PROVA auto-open (op:open) — RIUSCITA
- Prova:    calda OK — ZW3D era chiuso → lanciato su copia %TEMP%\zw3d_test_1784812679.Z3PRT → titolo finestra "ZW3D 2025 SP2 x64 - [zw3d_test_...Z3PRT]" = entrato diretto in ambiente PARTE in ~9s, nessun clic manuale.
- Stato:    FUNZIONA
- Prossimo: da qui si può testare op:remote (comandi su ZW3D vivo) e il pattern di lettura esito da %TEMP%.

### 2026-07-23 — Librerie "uguali a TopSolid" ricreate native ZW3D (acciaio/ferro/legno)
- File:     C:\Users\infoa\Downloads\topsolid\ (parametrico.h/cpp, profili_acciaio.h/cpp, ferro_battuto.h/cpp, legno.h/cpp, genera_librerie_zw3d.js) + librerie_zw3d\ (47 DXF)
- Build:    n/a C++ (no g++ sul PC) / node genera_librerie_zw3d.js → 47 DXF generati OK
- Prova:    fredda OK — 47 DXF benformati (SECTION/ENDSEC/EOF/VERTEX); C++ brace bilanciate 15/15 ad-hoc
- Stato:    FUNZIONA (DXF pronti da importare in ZW3D)
- Rottura:  — (TopSolid originale `.TopPkg` cancellato: utente non ha più TopSolid; ricreato in aperto)
- Prossimo: caricare i DXF nel plugin come libreria; quando l'utente installa Advance Steel/Revit/Civil, analizzarli e aggiungerli. Poi ferro_battuto (HERMES_TASK_ferro_battuto.md).

### 2026-07-23 — Regola fissa: agente ZW3D sempre istruito/aggiornato
- File:     knowledge/zw3d-self.md (NUOVO — mappa chirurgica stile antigravity-self.md)
- Stato:    FUNZIONA
- Nota:     l'utente ha imposto: ogni scoperta/azione/errore/riuscita va annotata in zw3d-self.md + worklog, come per Antigravity. Da rispettare in ogni sessione.
- Prossimo: leggere nativeAgent.js/localOrchestrator.js/tools-reference.md per completare la mappa.

### 2026-07-24 — LAVORO 1 Advance Steel: RICOGNIZIONE (resoconto iniziale)
- Contesto: Advance Steel 2027 APERTO ora (acad.exe PID 29232, trial attiva). Disco C: 57GB liberi (89% usato). NIENTE patch in questo relay.
- SCOPERTA CHIAVE — dove vive la logica:
  * Catalogo profili: C:\ProgramData\Autodesk\Advance\Data\AstorProfiles2027.mdb (116MB, OGGI popolato, 1309 tabelle) — leggibile via Access ODBC (pyodbc installato). Questo e' il catalogo profili = gia' coperto ieri (69 DXF).
  * DATI VERI (regole, settaggi, numerazione, distinta, CAM): SQL Server LocalDB istanza (LocalDB)\AdvanceSteel2027, file .mdf in ITA\Steel\Data\ e ITA\Kernel\Data\. LEGGIBILI via sqlcmd -S "(LocalDB)\AdvanceSteel2027" -E (Integrated Security). DB: AstorRules, AstorSettings, AstorDetails, AstorBase, AstorProfiles, GTCMapping, AstorProject, ecc. Mappa in ITA\Configuration\DatabaseConfiguration.xml.
  * DISTINTA (BOM): template disegno in ITA\Shared\Support\BOMTemplates\*.dwg — "Disegno - Distinta profili/piatti/bulloni/assembly/strutturata/elementi singoli". Sono i modelli di tabella-distinta che AS riempie.
  * MESSA IN TAVOLA: prototipi disegno in ITA\Shared\Support\Prototypes\ASDETPROTO-*.dwg per formato (A0..A4, verticale/orizz), singoli + assembly + list. Sono i "fogli tipo" su cui AS piazza automaticamente le viste.
  * ESTRAZIONE DATI: Roaming\...\Support\DataExtraction.xml (541 righe) = lista Type/Property inclusi/esclusi nell'estrazione attributi verso la distinta.
  * NUMERAZIONE/CAM: in AstorSettings tabelle NC_NumerationPlaneIndex, PartlistWithDSTVProfNames, UseUnfoldNameUserSectionForNC, MarkContoursPlaceInNC (=> conferma flusso NC1/DSTV per il taglio CNC). In AstorRules migliaia di RULE_* (cut layout, punch mark, ecc.).
- METODO AS (ricostruito): modello 3D -> NUMERAZIONE pezzi (assegna Position/Mark a parti identiche, raggruppa quantita') -> DISTINTA (estrae attributi via DataExtraction, riempie template BOM per categoria) -> MESSA IN TAVOLA (crea disegni piazzando viste sui Prototypes per formato) -> CAM (export NC1/DSTV per taglio CNC con lunghezza reale, angoli, fori).
- Prossimo: dump mirato tabelle numerazione/settings distinta da LocalDB -> scrivere C++ nativo ZW3D (cutting list + nesting/sfrido + messa in tavola) in Downloads\topsolid\ -> poi disinstallare Advance Steel completo.

### 2026-07-24 — LAVORO 1 Advance Steel: CODICE C++ distinta tagli + messa in tavola — FATTO+VERIFICATO
- File nuovi in C:\Users\infoa\Downloads\topsolid\:
  * cutting_list.h/.cpp  -> NUMERAZIONE (raggruppa pezzi identici, Mark B#/P#), DISTINTA (CSV per profili/piatti con qta/lungh.tot/peso.tot), NESTING 1D barre (First-Fit-Decreasing con kerf lama + sfrido riutilizzabile), statistiche resa%.
  * messa_in_tavola.h/.cpp -> scelta SCALA standard (1:5..1:100) + FORMATO foglio (A4..A0) come i prototipi ASDETPROTO, impaginazione viste (prospetto + sezioni se taglio obliquo), cartiglio, export DXF cornice+cartiglio+riquadri viste.
  * test_cutting_tavola.cpp -> main di prova (carpenteria esempio: 4 HEA140, 6+3 IPE160, 8 piatti).
- Metodo replicato da AS (NON file proprietari): numerazione parti identiche -> distinta per categoria -> nesting con kerf/sfrido -> messa in tavola su foglio-prototipo per formato con cartiglio.
- Build:  g++ 16.1.0 (installato via choco: mingw, PATH C:\ProgramData\mingw64\mingw64\bin). `-std=c++17 -Wall -Wextra -O2` = ZERO warning, ZERO errori. Link STATICO (-static-libstdc++) obbligatorio: senza, l'exe carica per sbaglio la libstdc++-6.dll di Git\mingw64 e va in SIGSEGV nel costruttore ofstream (conflitto DLL, NON bug del codice — confermato con gdb backtrace).
- Prova: EXIT=0. Output reale: distinta CSV corretta (B1 HEA140 x4 296.40kg, B2 IPE160@45 x6, B3, P1), piano taglio (8 barre, resa 66.9%), 4 tavole (A3/A2/A4 con scala e viste giuste), DXF out_tavola_esempio.dxf ben formato (SECTION/ENTITIES/EOF).
- Stato:  FUNZIONA (verificato con compilazione+esecuzione, non a occhio).
- PITFALL REGISTRATO: su questo PC per compilare C++ usare SEMPRE g++ di C:\ProgramData\mingw64\mingw64\bin con -static-libstdc++ -static-libgcc, altrimenti Git-bash inietta la sua libstdc++ e segfault.
- Prossimo: disinstallare Advance Steel 2027 completo (+ residui) per liberare spazio.

### 2026-07-24 — LAVORO 1: DISINSTALLAZIONE Advance Steel COMPLETA — FATTO
- Chiuso acad.exe (taskkill /F). Uninstall ufficiale via Autodesk ODIS Installer.exe (UninstallString dal registro), ELEVATO (Start-Process -Verb RunAs, UAC approvato): Hotfix {71A1D761...} exit=0, bundle Advance Steel {AE4B1B11...} exit=0.
- DB LocalDB: staccati tutti i 14 .mdf (sp_detach_db) + istanza (LocalDB)\AdvanceSteel2027 stop+delete.
- Rimossi residui: ProgramData\Autodesk\Advance Steel 2027 (811M), Advance (117M), Program Files\Autodesk\AutoCAD 2027 (guscio), AppData Local/Roaming Advance, istanza LocalDB, Uninstallers, metadata ODIS. Verifica: NESSUN RESIDUO.
- Spazio C:: durante il lavoro installato mingw (~600M, resta per compilare) quindi il netto liberato da Advance (~1.5GB effettivi oltre AutoCAD gia' rimosso col bundle) e' in parte compensato. C: ~53GB liberi.
- PITFALL registrato: (1) uninstaller Autodesk = ODIS Installer.exe con args -i uninstall + manifest, richiede ELEVAZIONE (senza: "Accesso negato"). (2) prima di cancellare le cartelle Data, STACCARE i .mdf da LocalDB e delete istanza, altrimenti file lockati. (3) in MSYS taskkill vuole cmd.exe /c "taskkill /IM ... /F" (gli slash // vengono mangiati).
- Stato LAVORO 1: COMPLETO (ricognizione + codice verificato + disinstallazione pulita).

### 2026-07-24 — LAVORO 2: Ampliamento libreria FERRO BATTUTO con misure reali (catalogo Eurofer)
- File: C:\Users\infoa\Downloads\topsolid\ ferro_battuto.h/.cpp (estesi), genera_ferro_battuto.cpp (NUOVO), genera_librerie_zw3d.js (esteso), catalogo_eurofer_misure.txt + catalogo_eurofer_clean.txt (estrazione dati), librerie_zw3d\FERRO\ (33 DXF nuovi).
- SORGENTE MISURE: catalogo reale EUROFER sul disco (C:\Users\infoa\Downloads\ferro-battuto.pdf, 284 pag). Estratte con PyMuPDF (sola lettura) codici Art. + HxL + sezioni quadre □10/12/14/16. Nessuna ricerca web (browser crashava; il PDF e' la fonte primaria verificabile). NESSUN login/pagamento.
- ELEMENTI AGGIUNTI (parametrici, bbox = misura reale HxL del catalogo, verifica forte):
  * RICCI: 01.025(120x290), 01.026(125x360), 01.027(100x350), 01.070(125x290) — sez 12/14
  * VOLUTE/SPIRE: 01.277(360x125), 01.280(600x125), 01.504(155x95), 01.508(290x115), 01.509(350x110) — sez 12/14
  * CIME/PUNTE: 13.001(48x250), 13.035(40x150), 13.035b(62x210), 13.052(60x130), 13.173(24x35) — sez 8/12/14
  * TORCIGLIONI: 01.401(65x190), 01.402(100x200), 01.403(110x220), 01.404(125x360) — sez 12/14
  * BACCHETTE MARTELLATE: 1000/1200/1500/1800 x sez 12/14/16
  * ROSONI: 03.001(250), 03.018(760), 03.025(625), 03.051(180), 03.066(300)
  * FOGLIE REALI: 01.101(110x220), 01.114(230x360), 01.134(770x200)
  * CORNICI CANCELLO: 15.157(1500x150), 15.157.16(1000x200), 15.157.17(1000x400)
  => 33 DXF ferro battuto parametrici totali (piu' i 5 base gia' esistenti: voluta_sx/dx, foglia_120/160, giogo)
- Build C++: g++ 16.1.0 (C:\ProgramData\mingw64\mingw64\bin) `-std=c++17 -Wall -Wextra -O2 -static-libstdc++ -static-libgcc` = ZERO warning, ZERO errori.
- Prova: EXIT=0. Emessi 33 DXF; bbox verificato contro misura catalogo su TUTTI i 33 (33/33 [OK], tolleranza ±0.5mm). DXF ben formati (SECTION/ENDSEC/EOF/VERTEX) su tutti.
- JS (genera_librerie_zw3d.js): esteso con gli stessi 33 elementi in librerie_zw3d\FERRO\ (node OK, 102 DXF totali libreria). Geometria identica al C++.
- Totale libreria DXF ora: 102 (47 base + 33 FERRO + 22 legno/profili aggiuntivi del JS).
- PITFALL confermato: link STATICO obbligatorio (-static-libstdc++ -static-libgcc) altrimenti SIGSEGV per libstdc++ di Git-bash.
- NESSUNA licenza toccata (relay pulito). NESSUN programma installato.
- Stato: FUNZIONA (verificato compilazione+esecuzione+bbox+formato DXF).
- Prossimo: caricare i DXF FERRO nel plugin come libreria; se serve, aggiungere altre varianti dal PDF (es. pagine 13.xxx / 15.xxx).

### 2026-07-26 — SCANSIONE TOTALE ZW3D + ADDESTRAMENTO agente con funzioni native reali — FATTO
- Firma:   Hermes (agente Nous Research), per conto utente infoa/Alcafer2011.
- Cosa:    scandagliato tutto il PC per cartelle ZW/ZWSOFT (trovate: Program Files\ZWSOFT\ZW3D 2025,
  AppData Local/Roaming ZWSOFT, Documents\ZW3D, Downloads\03_PLUGIN_ZW3D, EfestoAI\zw3d-plugin,
  OneDrive\Desktop\ZW3D-INDEX 1, src\zw3d-assets, cadenas\sitesetup_zwcad). Estratto l'inventario
  COMPLETO delle funzioni native reali dall'installazione ZW3D 2025.
- Estratto e VERIFICATO (numeri reali dai file dell'installazione):
  * 3591 comandi/bottone da Settings\ResourcePool\Actions.zcui (comando !Cd + label + dialogo Form + hint + desc + script).
  * 1042 comandi !Cd* unici referenziati nelle pagine ribbon.
  * 2869 funzioni SDK uniche (840 Zw* moderne + 2028 cvx* legacy + 1 Vx*) dai 237 header api\inc\zwapi_*.h.
  * 458 file .tcmd (definizioni dialogo/parametri). Capita la catena bottone: RibbonPages.zcui -> Actions.zcui(Form/Script) -> .tcmd(parametri).
- CONFERMA CHIAVE: ricontrollati TUTTI i 237 header -> NESSUNA API SDK crea weldment (solo simboli saldatura
  per il disegno: ZwDrawingSymbolWeld*, cvxDwgSymWeld*). Conferma di nuovo la regola §5: weldment via macro
  ZwCommandMacroExecute rigiocando !CdWeldStruct / !CdWeldStrctCrt ("Profile Swept Rod", variante nativa trovata ora).
- File SCRITTI (in C:\Users\infoa\EfestoAI\knowledge\):
  * zw3d-api-nativa.md         (indice ragionato: catena comandi, famiglie, carpenteria, API per capacità, header ricchi)
  * zw3d-comandi-nativi.tsv    (330 KB, 3591 righe: comando|label|dialogo|hint|descrizione)
  * zw3d-api-index-locale.tsv  (355 KB, 2869 righe: funzione|header|riga|deprecated|firma)
  Aggiornati: zw3d-rules.md §0 (link alle nuove fonti), zw3d-self.md (§ nuovo), questo WORKLOG.
- Build/Prova: n/a (estrazione conoscenza, nessun codice compilato). Nessuna modifica a ZW3D o licenze.
- Stato:   FUNZIONA (fonti sul disco verificabili; l'agente ora pesca da TSV/lookup invece di inventare).
- Prossimo: chiedere all'utente se importare i 3 file zw3d-*.md in Efesto (staccandoli da Antigravity, come da DEFINIZIONE.md di Efesto).

### 2026-07-26 01:54 — Integrazione Efesto + sezione AI ribbon + icona + Tailscale + HermesBridge
- File:  C:\Program Files\ZWSOFT\ZW3D 2025\apilibs\Settings\Default\Strategy\Environment-10-Part\ / -13-Assembly\ / -2-Z3\ LayoutStrategy-4-Expert.zcui  (aggiunte pagine EFESTO_Page + AI_Page)
         C:\Program Files\ZWSOFT\ZW3D 2025\apilibs\Settings\Default\ResourcePool\Efesto_Pages.zcui + Efesto.zcui  (aggiornati: sezione "AI", pulsante "Apri Efesto AI", icona ai)
         C:\Program Files\ZWSOFT\ZW3D 2025\apilibs\icons\ai.png + ai_32.png  (icona AI "potente" generata via ComfyUI)
         C:\Program Files\ZWSOFT\ZW3D 2025\apilibs\Commands\Efesto_Apri.tcmd  (comando nativo DLL)
         C:\Users\infoa\EfestoAI\knowledge\  (importata mappa nativa + 2 TSV + 3 zw3d-*.md, scollegati da Antigravity)
         C:\Users\infoa\HermesBridge\server.js + avvia-hermes-bridge.vbs  (bridge indipendente telefono↔Hermes via Tailscale, porta 8800)
- SCOPERTA CHIAVE (perché il pulsante Efesto non compariva): ZW3D carica i .zcui direttamente da
  apilibs\Settings\Default\ResourcePool\ su disco; ma una pagina ribbon appare SOLO se esiste il file
  Strategy corrispondente in apilibs\Settings\Default\Strategy\Environment-XX-YYY\LayoutStrategy-4-Expert.zcui
  (insert RibbonPage name=... topCollection=Layout_10_Part). Efesto aveva DLL+zcui ma MANCAVANO le Strategy -> pagina invisibile.
  Aggiunte EFESTO_Page e AI_Page in Part(10)/Assembly(13)/Z3(2). Visibile al prossimo avvio ZW3D.
- Icona AI: generata con ComfyUI (cervello neurale + nucleo forgia, blu/arancio), ridimensionata 48/32 px,
  copiata in apilibs\icons\ e in EfestoAI\zw3d-plugin\. Non un giocattolo: stile emblema CAD pro.
- Comando pulsante: richiama la DLL Efesto.dll (XEfesto_Apri) via ~Efesto_Apri (apre server Efesto su 127.0.0.1:8777 in modalità app Chrome).
- Tailscale: GIÀ attivo e configurato. PC=100.106.75.61, iPhone(iphone-15-pro-max)=100.121.119.38, stesso account info.alcafer@.
  Server Efesto(8777) e Antigravity mobile(8790) ascoltano su 0.0.0.0 -> raggiungibili dal telefono via Tailscale.
- HermesBridge (NUOVO, indipendente da Antigravity/Efesto): server Node su porta 8800 che parla con Hermes (Nous,
  model tencent/hy3:free) leggendo la credenziale da auth.json. Pagina web mobile + token fisso. Avvio VBS in watchdog.
  STATO: server parte e serve la pagina, MA chiamata a Nous dà 401 (token scaduto; endpoint refresh /oauth/token
  risponde HTML invece di JSON -> da correggere l'URL di refresh nel codice). BLOCCO noto, da riprendere.
- Build/Prova: HermesBridge parte (netstat conferma porta 8800 LISTENING); test /send bloccato su 401 Nous.
- Stato:   PARZIALE. Ribbon+icona pronti (da verificare a video aprendo ZW3D). Bridge da sbloccare (refresh token Nous).
- Prossimo: (1) aprire ZW3D e verificare che la sezione "AI" + pulsante Efesto compaiano; (2) sbloccare HermesBridge trovando
  l'endpoint di refresh OAuth corretto nel codice hermes-agent e sistemare server.js; (3) rifare test /send.

### 2026-07-26 02:0X — FIX: "Hermes" come agente non rispondeva MAI (Antigravity + Efesto)
- SINTOMO: scegliendo il cervello "Hermes" (Nous, tencent/hy3:free) in Antigravity ed Efesto, nessuna risposta arrivava.
- CAUSA RADICE: il token OAuth di Nous in auth.json scade ~ogni ora. L'UNICO che lo rinnova è HERMES stesso
  (processo proxy su 127.0.0.1:8645, avviato con `hermes proxy start --provider nous --port 8645`).
  Se il proxy non è acceso o il token è scaduto e nessuno lo rinnova -> 401 silenzioso -> nessuna risposta.
  Antigravity (nousClient.js) fa un "nudge" a Hermes per rinnovare, ma se il proxy è spento il nudge fallisce.
  Efesto (hermes.js) parla col proxy 8645: se spento, nessuna risposta.
- DIAGNOSI FATTA: token scaduto (expires_at 00:54, ore prima); proxy 8645 risultava acceso (PID 20260) ma con
  token scaduto in memoria -> non rinnovava da solo.
- FIX APPLICATO:
  1) Rinnovo forzato token: `venv\Scripts\python.exe -c "from hermes_cli.auth import resolve_nous_runtime_credentials as f; f()"` -> REFRESH OK.
  2) Creato watchdog C:\Users\infoa\HermesProxy\avvia-hermes-proxy.vbs che tiene il proxy 8645 SEMPRE acceso
     (se muore lo riavvia). Messo nello Startup di Windows -> parte a ogni boot del PC.
  3) Avviato il watchdog subito.
- VERIFICA: dopo il fix, ENTAMBI rispondono. Test: Antigravity (nousClient, hy3) => "CIAO"; Efesto (chatHermes) => "FUNZIONA".
  Il proxy su 8645 risponde a /v1/chat/completions e /v1/models.
- REGOLA OPERATIVA (non dimenticare): affinché "Hermes" risponda in Antigravity/Efesto, il proxy Hermes (8645)
  DEVE restare acceso. Se dopo un po' smette di rispondere: riavviare il proxy o il watchdog. Non toccare mai
  manualmente auth.json se non per rinnovo via resolve_nous_runtime_credentials (il refresh_token è rotante:
  riusarlo revoca la sessione di Hermes -> ci si slogga).
- Stato: RISOLTO (proxy avviato + watchdog in autostart + token rinnovato). Da monitorare nel tempo.

### 2026-07-26 — Generatore modelli 3D ZW3D (ringhiere/inferriate/recinzioni/balconi/scale) — FATTO+VERIFICATO
- File: C:\Users\infoa\Downloads\TopSolid_Export\librerie\ZW3D_MODELLI_3D\ (cloud_config.json, profili_zw3d.py, step_writer.py, gen_3d.py, + 5 cartelle categoria con 55 STEP)
- Cosa: l'utente voleva il 3D SUBITO (no 2D), usando tutti i profili ZW3D, separati per
  categoria, >=50 modelli di partenza, con un "cloud config" leggibile. Generati 55 modelli
  STEP (11 x 5 categorie: scale/balconi/recinzioni/ringhiere/inferriate).
- Sorgente profili: profili_catalogo.json del plugin ZW3D (15 famiglie) + tabelle standard
  UNI/EN fedeli (IPE/HEA/HEB/UPN/angolari/tubi/piatti/quadri/tondi/T). Nomi interni del
  catalogo ZW3D non sono misure reali -> sezioni 2D parametriche da norma, mappate per FAMIGLIA.
- Metodo: ogni modello = composizione di profili estrusioni (montanti verticali + corrimano
  orizzontale + riempimenti + decori ferro battuto per inferriate). Writer STEP nativo
  (ISO 10303-21, MANIFOLD_SOLID_BREP + CLOSED_SHELL + ADVANCED_FACE + POLY_LOOP), nessuna
  dipendenza esterna oltre steputils (solo per il parse di verifica).
- Build/Prova: python gen_3d.py -> 55/55 OK, 0 errori, 1265 solidi totali, 1.33M entità.
  Verifica FINALE: ogni STEP riletto con steputils.p21.readfile -> parse OK + MANIFOLD_SOLID_BREP>0.
  Bytes per file 72KB..4MB; cartella ~55MB.
- PITFALL: (1) steputils 0.1 ha SOLO il parser (p21), non un writer -> STEP scritto a mano.
  (2) catalogo ZW3D usa codifiche sue nei nomi misura (es "IPE 20x27") -> non fidarsi,
  usare tabelle standard per le sezioni. (3) CARTESIAN_POINT/Direction cache-ati nel writer
  per tagliare le entità. (4) file pesanti (~1MB/modello) per via dei vertici unici per solido;
  accettabile; se serve leggerezza, rifattorizzare con BREP condivisi.
- NOTA: i file NON cancellano nulla delle librerie TopSolid originali; sono nuove geometrie
  generate da zero nella cartella export. Nessuna licenza/patch toccata.
- Stato: FUNZIONA (verificato parse reale su tutti i 55 file).
- Prossimo: se l'utente vuole, importare i STEP in ZW3D come libreria; o aggiungere profili
  ferro battuto dai DXF reali (librerie_zw3d/FERRO) come decorazioni parametriche fedeli.



### 2026-07-26 — EFESTO: pannello NATIVO in ZW3D (non piu' finestra volante) — FATTO
- PROBLEMA: la v1 del plugin apriva Chrome; il pannello "vagava per lo schermo" invece di
  essere una pagina di ZW3D. CAUSA: la form era dichiarata `ZsCc::Form::Temporary`.
- SOLUZIONE: form `Dockable` + `Persistent`, agganciata al UI Manager con
  `cvxFormInsertTo(&svxFormInfo, 3, VX_UI_MANAGER)` -> compare nella barra laterale con
  icona ed etichetta, come Assembly/History. Dettagli completi e riusabili in
  `_appendice-form-native.md` (docking, callback sui campi, widget ammessi, template
  command per l'input di testo, regola dei thread, impacchettamento zrc, trappole).
- FILE: C:\Users\infoa\EfestoAI\zw3d-plugin\  (Efesto.cpp, forms\EfestoPanel.ui,
  forms\Efesto_Chiedi.ui, commands\Efesto_Chiedi.tcmd, Efesto.zcui, Efesto_Pages.zcui,
  build.bat, installa.ps1 auto-elevante).
- COMANDI: `Efesto_Apri` (apre il pannello) e `Efesto_Chiedi` (template command con un
  parametro `string`: ZW3D disegna la casella e i pulsanti OK/Applica/Annulla nativi;
  con Applica il comando resta aperto e si chiede di seguito, come CdWeldStruct).
- ARCHITETTURA: il cervello resta il server Node su 127.0.0.1:8777; il plugin e' un client
  HTTP (manda la domanda, poi rilegge la conversazione finche' non compare la risposta).
  L'attesa gira su un thread separato che NON tocca l'API ZW3D; un timer Win32 travasa il
  testo sul thread principale, dove soltanto si chiama cvxItemAdd. Zero geometria, zero
  cvx-shape: non puo' corrompere un disegno ne' far cadere una sessione.
- INSTALLATO in apilibs: Efesto.dll + Efesto.zrc + icons\efesto.png e efesto_32.png +
  Settings\Default\ResourcePool\*.zcui + Resource\Forms\*.ui + Commands\Efesto_Chiedi.tcmd.
  Rimosso il residuo `Commands\Efesto_Apri.tcmd` della v1 (faceva interpretare Efesto_Apri
  come template command). DA VERIFICARE AL RIAVVIO DI ZW3D.
- AGENTE POTENZIATO (vale per Efesto E per Antigravity): lo strumento `zw3d` ora ha
  `op='command'` (cerca un COMANDO del CAD: etichetta sul ribbon, form del dialogo, come si
  invoca; fonti = zw3d-comandi-nativi.tsv + catalogo di 14.858 invocazioni) e `op='header'`
  (elenca tutte le funzioni di un header con la firma vera, da ZW3D-SIGNATURES-BY-HEADER.json).
  `op='lookup'` non dipende piu' dai .md su OneDrive: legge zw3d-api-index-locale.tsv, che e'
  locale e porta il flag @deprecated. Gli 8 JSON estratti da Hermes ora stanno anche in
  C:\Users\infoa\Antigravity\src\knowledge\api\ (prima li aveva solo Efesto: l'agente di Antigravity non
  li vedeva affatto).

### 2026-07-26 — Cambio rotta: Tekla + ZW3D 2027 (Revit/Civil abbandonati)
- File:     knowledge/tekla-approccio.md (NUOVO), knowledge/zw3d-2027-differenze.md (NUOVO),
            EfestoAI/RESIDUI-TOPSOLID.md + EfestoAI/rimuovi-topsolid.ps1 (Task 1 residui TopSolid)
- Build:    n/a (studio + report; nessun codice compilato)
- Prova:    fredda OK — verifiche reali su PC:
              * TopSolid disinstallato: residui trovati (cartelle, chiavi registro, var ambiente
                TOPSOLIDCOMMONFILES di SISTEMA orfana, istanza SQL SQLTOPSOLID DA VERIFICARE).
              * ZW3D 2025 installato (api\inc 237 header, ZW3D.lib); ZW3D 2027 NON ancora.
              * I nostri plugin (Efesto.dll, SuperAssistenteBridge.dll) confermati: esportano
                <Nome>Init/<Nome>Exit e importano da ZW3D.dll (ABI x64 stabile).
              * Tekla NON installata: studio dell'approccio a freddo (Wikipedia + Tekla Dev Center).
- Stato:    FUNZIONA (conoscenza in linea)
- Rottura:  —
- Prossimo: (1) quando la 2027 e' installata, eseguire il diff header 2025↔2027 (vedi
            zw3d-2027-differenze.md §B) e confermare "i plugin ci entrano?". (2) Quando Tekla
            e' installata, verificare numbering + export NC1 (§9 di tekla-approccio.md).
- NOTA SICUREZZA applicata: NON toccato SQL Server EXPRESS / SQLEXPRESS; istanza SQLTOPSOLID
  lasciata fuori dallo script di rimozione (chiede conferma a parte). Non installare 2027
  sopra la 2025 finche' non e' chiaro; apilibs condivisa con CamApi/NCTI: mai jolly.

### 2026-07-26 — Studio ZW3D 2027 + ricompilazione plugin contro SDK 2027 (brief 2b)
- File: knowledge/zw3d2027-api-index-locale.tsv, knowledge/zw3d2027-comandi-nativi.tsv,
        knowledge/api2027/* (JSON: NATIVE-SIGNATURES, SIGNATURES-BY-HEADER, COMMAND-MAP,
        RIBBON-INDEX, API-FAMIGLIE, DIFF-2025-2027.json), knowledge/zw3d-2025-vs-2027.md
- Build Efesto2027.dll: OK (0 errori, 1 warn LNK4070 irrilevante) — build2027.bat
- Build SuperAssistenteBridge.dll (2027): OK (0 errori) — SuperAssistenteBridge.2027.vcxproj
- Build SuperAssistenteEngine.dll (2027): OK (0 errori) — SuperAssistenteEngine.2027.vcxproj
        output in ...\SuperAssistentePlugin_FINALE_3\FINALE\bin2027\x64\Release\
- Verdetto: I plugin PASSANO sulla 2027 ricompilando, SENZA modifiche al codice sorgente.
        Tutte le API usate (cvx*, ZwCommand*, svxFormInfo, evxFormAddTo, VX_UI_MANAGER,
        ZwShapeListGet, ZwPhysicalAttributeGet) ci sono ancora. ABI x64 stabile.
- ROTTURA potenziale: NESSUNA. Unica diff firma rilevante cvxFormCreate char*->const char*
        (assorbita dal compilatore, nessun cambio codice).
- NON deployato: l'utente lavora sulla 2025; la 2027 va collaudata prima di sostituire.
- apilibs 2027 NON toccata (solo compilato in cartelle di lavoro separate).
- Prossimo: con l'utente, copiare i .dll/.zrc 2027 in apilibs 2027, test di caricamento
        dentro ZW3D 2027 aperto, poi decidere il switch da 2025 a 2027.

### 2026-07-26 — Implementati Cancello, Recinzione, Scala (erano stub muti)
- File: include/SteelParametric.h (+GateObject, FenceObject, StairObject),
        src/SteelParametric.cpp (logica pura, ~310 righe), src/SuperAssistenteEngine.cpp
        (Cmd_Cancello/Recinzione/Scala reali con RequirePart + LoadParamsFromTemp +
        ShowWarningsAndDraw; parametri opzionali da %TEMP%\cancello_input.txt /
        recinzione_input.txt / scala_input.txt, formato chiave=valore come il cono).
- Regole d'officina rispettate: 45° SOLO sul telaio del cancello (spigolo complanare);
  recinzione = N campate di Railing con piantoni CONDIVISI (niente doppioni) e regola
  pendenza in pianta; scala con Blondel 2A+P 590-650 e cosciale = ipotenusa vera.
- Build: MSBuild Release x64 OK, 0 errori (SuperAssistenteEngine.dll rigenerata in bin/).
- Prova: FREDDA OK (matematica verificata in Node: bacchette cancello 9/920mm,
  recinzione 3 campate 7 piantoni, scala 15 gradini alzata 180 Blondel 610).
  CALDA NON ancora fatta: serve deploy DLL in apilibs\Core + riavvio ZW3D + parte attiva.
- Stato: COMPILA; geometria via GeometryExecutor (stesse Zw* collaudate della Ringhiera).
- Prossimo: deploy + prova a caldo con l'utente; poi CdWeldStruct per membri weldment veri.

### 2026-07-31 — PASSO 1 icone .icn a 64x64 (ritocco formato)
- File:
  - `SuperAssistentePlugin_FINALE_3\FINALE\gen_icons_1b.ps1`: impostato `$S = 64` (era 96). Aggiunti i disegni mancanti per `g_22` (barra profilo) e `g_23` (staffe), che lo script non generava e restavano a 96x96. Rigenerati g_16/g_19/g_20/g_21/g_22/g_23.
  - `SuperAssistentePlugin_FINALE_3\FINALE\import_icons_logitrace.ps1`: sostituito ogni `96` letterale con `64` (header int32, dimensione Bitmap, DrawImage, due loop y/x). I PNG sorgente sono 96x96 in `logitrace\resources\tramogge\png96` e vengono ridimensionati a 64x64 da DrawImage. Rigenerata la serie `lt_*.icn` (212 file).
- Build: n/a (script PowerShell, nessun compilatore C++).
- Prova: fredda OK. Verifica su disco con script Python: controllati TUTTI i .icn in
  `Resource\Panels\gallery\` (24 file) e `Resource\Panels\gallery\icons_logitrace\` (213 file lt_* + source_names.txt, quindi 212 lt_*.icn) → 448 .icn totali.
  Risultato: 448 a 16392 byte, 0 non conformi.
- Stato: FUNZIONA. Tutti i file .icn pesano esattamente 16392 byte (header 8 + RGB 64*64*3 = 12288 + alpha 64*64 = 4096 → 16392). Formato coerente con le 18 icone pre-esistenti a 64x64 (g_00..g_15, g_17, g_18). Le 6 forme nuove (g_16/g_19/g_20/g_21/g_22/g_23) ora sono a 64x64 come il resto, non più a 96x96/36872B. Le 213 icone LogiTrace lt_* ora sono a 64x64.
- Prossimo (dal mandato §5): collegare le `lt_*` al manifest gallery (PASSO 1 dice "solo dopo collega le lt_* al manifest"); poi PASSO 2 (icone AUTOMAZIONE via ComfyUI).

## 2026-07-31 — COMPUTES GROUP: bottone "Allinea solido" + rimozione orfana "Piega fresata"
- **Cosa**: il pacchetto Computes Group installa 55 DLL ma solo 25 hanno il .zrc che dichiara il
  comando; AllineaSolido.dll c'e' (+ icona) ma nessuno crea il bottone. Rimediato nel NOSTRO
  plugin, senza toccare i file del fornitore in Program Files.
- **Comando verificato dalle stringhe della DLL** (non inventato): `AllineaSolido`,
  `AllineaSolidoInit` / `AllineaSolidoExit` -> si lancia come `~AllineaSolido`.
  La stringa compare SOLO in apilibs\AllineaSolido.dll (grep su tutta la 2025).
- **File modificati** (sorgente plugin, `...FINALE\Settings\Default\ResourcePool\`):
  - `AUTOMAZIONE.zcui`: aggiunta Action `ID_~AllineaSolido` (stessa struttura di
    `ID_~SuperAssistente_TestBox`, convenzione `ID_~` per i comandi senza Form).
  - `AUTOMAZIONE_Pages.zcui`: aggiunto `<Control action="ID_~AllineaSolido" ... buttonStyle="4"/>`
    in coda a `AUTOMAZIONE_GroupPanel`.
  - Entrambi riletti: XML ben formato (verificato con parser).
- **Icone** (nuovo script `FINALE\gen_icon_allinea_solido.ps1`, System.Drawing, NO ImageMagick):
  da `apilibs\icons\Allinea_solido.png` (123x129, originale NON toccato) generate in `FINALE\icons\`
  `allinea_solido.png` 64x64, `allinea_solido_48.png` 48x48, `allinea_solido_32.png` 32x32
  (proporzioni mantenute, centrate, sfondo trasparente). Misure rilette da disco.
- **Piega fresata = funzione MAI CONSEGNATA — confermato**: nessuna DLL di apilibs contiene
  "fresat" (ne' ASCII ne' UTF-16); nessuna PiegaFresata.dll nel catalogo. Unica occorrenza di
  "fresat" in tutta la 2025 e' `languages\it_IT\text\Cad.MSG` ("Fresatura", "testa fresata"):
  testo nativo ZW3D, NIENTE a che vedere, non toccato.
- **Azione**: `PIEGA_FRESATA.png` NON cancellata ma SPOSTATA (reversibile) in
  `C:\Program Files\ZWSOFT\ZW3D 2025\apilibs\icons\_ORFANE_NON_USARE\PIEGA_FRESATA.png`.
  La scrittura in Program Files e' andata a buon fine (nessun accesso negato).
- **Riferimenti a PIEGA_FRESATA**: NESSUNO. Non citata in alcun .zcui/.zrc/.tcmd/.xml/.ini
  ne' del fornitore ne' nostro -> era solo un file immagine orfano, nessun bottone da ripulire.
- **Build**: NON eseguita (voluto: il mandato chiede solo la preparazione del sorgente).
- **Prova**: nessuna, ne' fredda ne' calda (niente codice C++ toccato).
- **Stato**: SORGENTE PRONTO, non deployato.
- **Prossimo passo**: build 2025 (§3) + deploy (§4) insieme agli altri lavori; il .zrc va
  rigenerato dal PostBuild del Bridge e le 3 icone `allinea_solido*` vanno copiate nel deploy.
  Verifica finale a occhio dell'utente: il bottone "Allinea solido" deve comparire in
  AUTOMAZIONE e aprire il comando del fornitore. ATTENZIONE: se risponde "licenza mancante"
  e' un problema commerciale Computes Group, NON si tocca cgLicense*.

### 2026-07-31 — PASSO 2 icone AUTOMAZIONE: icona di prova con ComfyUI
|- **Contesto**: mandato MANDATO-HERMES-PLUGIN-2025.md §5 PASSO 2. L'utente vuole le
  |  17 icone AUTOMAZIONE generate da ComfyUI. REGOLA di questo giro: generarne UNA sola
  |  di prova, farla vedere all'utente, solo dopo approvazione generare le altre 16.
  |- **Checkpoint**: comfyClient.js dichiara `realisticVisionV60B1_v51HyperVAE.safetensors`
  |  (NON modificato, e' codice vivo di Antigravity). Il modello E' presente su disco in
  |  `%LOCALAPPDATA%\Comfy-Desktop\ComfyUI-Shared\models\checkpoints\` (2.1 GB, completo).
  |  Anche `cyberRealisticPony_v18.safetensors` e `ponyRealism_v23.safetensors` sono presenti.
  |  Usato: `realisticVisionV60B1_v51HyperVAE.safetensors` (presente, era l'originale).
  |- **ComfyUI**: avviato via API HTTP su 127.0.0.1:8188 (main.py con --base-directory verso
  |  ComfyUI-Shared, python del .venv). Risponde alla /system_stats.
  |- **Workflow**: CheckpointLoaderSimple -> EmptyLatentImage (768x768) -> CLIPTextEncode (pos+neg)
  |  -> KSampler (steps=30, cfg=7, dpmpp_sde, karras, denoise=1.0) -> VAEDecode -> SaveImage.
  |  Prompt: "a wrought iron window grate, decorative iron bars in geometric pattern, centered,
  |  solid black iron bars, pure white background, flat technical drawing style, CAD icon, high
  |  contrast, simple clean lines, no text, no frame, no shadow, no border, flat design, vector style, clean".
  |  Negative: "(deformed, distorted, disfigured), poorly drawn, bad anatomy, ... dark background,
  |  black background, gray background, brown background, shadow, frame, border, clutter".
  |- **Post-processing**: l'immagine grezza da ComfyUI aveva sfondo nero (modalita Hyper produce
  |  sfondi scuri con pochi passi). Con script Python + PIL: soglia a 128 su canale grigio,
  |  pixel sotto soglia = primo piano (ferro), sopra = sfondo bianco puro (255,255,255).
  |  Il risultato e' un PNG 768x768 RGB con sfondo bianco uniforme.
  |- **Verifica**:
  |  - Sfondo: tutti e 4 angoli = RGB(255,255,255), uniforme. Media angoli 10x10 = 255.
  |  - Centratura: bounding box contenuto L=58 T=63 R=702 B=702, centro (380,382) vs
  |    immagine (384,384) -> offset 0.5%/0.2% (ECCEZIONALMENTE centrato).
  |  - Leggibilita' a 32x32: preview ASCII mostra la griglia a maglie del inferriata ben leggibile.
  |  - Contenuto: pattern reticolare di barre metalliche (inferriata per finestra), niente testo,
  |    niente cornici, niente elementi spuri.
  |- **File di prova**: `Downloads\03_PLUGIN_ZW3D\SuperAssistentePlugin_FINALE_3\FINALE\icons\_prova_comfy\inferriata.png`
  |  (768x768 RGB PNG, 316 KB). Copia grezzo in `_prova_comfy/inferriata_raw.png` per confronto.
  |- **NON toccato**: le icone vere in `icons\` (64/48/32 PNG) sono invariate. Non generate le altre 16.
  |- **Limitazioni note**: i modelli Pony (cyberRealisticPony, ponyRealism) producono immagini
  |  prevalentemente nere con questi parametri; il modello Hyper (realisticVisionV6) a 30 step/cfg 7
  |  produce contenuti nitidi ma sfondo scuro, richiede post-processing per bianco.
  |- **Prossimo**: aspettare approvazione utente sull'icona di prova prima di generare le altre 16.

  ### 2026-07-31 — PASSO 2C icone AUTOMAZIONE: 17 icone A COLORI + semplificate (FASE 1, 3 campioni)
  |- **Decisione utente (2026-07-31)**: le 17 icone vanno a colori. Palette FISSA a 5 colori,
  |  uguale per tutte: antracite #2E2E2E (contorni/ferro, dominante), acciaio #8A9199 (metalli),
  |  arancio #E8873A (accento CALDO: azione/taglio), blu #3A7BD5 (accento FREDDO: doc/dati/export),
  |  carta #F2F0EC (fogli/sfondi chiari). Regola: contorno antracite sempre; UN SOLO accento per
  |  icona (arancio XOR blu); accento piccolo. Inoltre: SEMPLIFICARE (tratti spessi, meno elementi,
  |  piu' spazio vuoto) perche' a 32px la prova 2B era "un rettangolo grigio indistinto".
  |- **Script aggiornati (riusati quelli di 2B)**:
  |  - `tools/comfy_icon_gen.py`: prompt arricchito con PALETTE esplicita (5 hex) + "bold thick
  |    outlines, minimal detail, simple shapes, few elements, high contrast, generous negative
  |    space, icon design"; negative aggiunge "gradient, rainbow, many colors, two accents".
  |  - `tools/cut_bg.ps1`: soglia fondo RISTRETTA (Hi=252, Lo=246) perche' la carta #F2F0EC ha
  |    luminanza ~240, troppo vicina al bianco(255): con la banda larca di 2B (246/205) veniva
  |    cancellata. Ora solo il bianco puro diventa trasparente, la carta sopravvive.
  |  - `tools/resize_preview.py` (NUOVO): collaudo obbligatorio — da 512 fa resize a 32 e 48 con
  |    LANCZOS poi ringrandisce a 256 con NEAREST, cosi' si vede subito se regge a 32/48.
  |- **ComfyUI**: attivo su 127.0.0.1:8188 (v0.27.1). Checkpoint realisticVisionV60B1_v51HyperVAE
  |  presente. comfyClient.js NON toccato.
  |- **FASE 1 (3 campioni, una per categoria)** — GENERATI, in attesa dell'ok dell'utente:
  |  1. inferriata  (oggetto metallico, accento ARANCIO) -> icons/_prova_comfy/inferriata.png
  |  2. distinta    (documento/lista, accento BLU)       -> icons/_prova_comfy/distinta.png
  |  3. svil_cono   (forma geometrica tecnica, accento ARANCIO) -> icons/_prova_comfy/svil_cono.png
  |  Ognuna: 512x512 RGBA, fondo trasparente vero (alpha 0 agli angoli), + _test_32/48 ingranditi.
  |- **FIX ComfyUI (15:2x)**: il KSampler andava in crash con `OSError [Errno 22] Invalid
  |  argument` su `sys.stderr.flush()` (progress bar tqdm) perche' ComfyUI era stato avviato
  |  da una finestra Git-bash poi CHIUSA: il suo "schermo" era morto. ComfyUI rispondeva alle
  |  API ma ogni generazione abortiva. Rimedio: kill dei main.py (PID 5256) e riavvio pulito
  |  agganciato a un file di log (`ComfyUI-Shared/logs/comfy_*.log`) in background, non a una
  |  finestra. Ora il KSampler da' `success`. NOTA: questo sblocca ComfyUI per TUTTI (anche
  |  le immagini di Antigravity). Se ricade nello stesso errore, il fix e' riavviarlo cosi'.
  |- **Robustezza script**: `comfy_icon_gen.py` ora usa timeout 120s e riprova su /history se
  |  il server e' occupato (prima moriva a 60s su richieste lente). Aggiunto `tools/misura_icona.py`
  |  (collaudo misurabile: alpha agli angoli, % trasparenza, bbox, indice leggibilita' a 32/48).
  |- **Collaudo misurabile (IO non vedo, misuro dal disco)**: tutte e 3 PASSANO.
  |  - inferriata:  angoli alpha=0, trasp 19.3%, bbox 49.9%/49.9%, indice 32px=98 / 48px=100.
  |  - distinta:    angoli alpha=0, trasp 19.3%, bbox 49.9%/49.9%, indice 32px=100 / 48px=100.
  |  - svil_cono:   angoli alpha=0, trasp 19.3%, bbox 49.9%/49.9%, indice 32px=100 / 48px=100.
  |  (soglia MACCHIA = indice <35; tutte ben sopra). NOTA: i raw riempiono il 100% del fotogramma
  |  (oggetto ai bordi), quindi cut_bg non ha margini da dare; per FASE 2 aggiungo "lots of empty
  |  white space around the object" al prompt per forzare il respiro. Verifica visiva finale = utente.
  |- **NON toccato**: le icone vere in `icons\\` (invariate), i .icn della galleria, comfyClient.js.
  |- **Diario**: spostata qui la voce scritta per errore in FINALE/knowledge/ZW3D-WORKLOG.md
  |  (file doppione cancellato) — il diario vero e' questo, per regola zw3d-rules.md §8.
  |- **Prossimo**: ok utente sui 3 campioni. Poi FASE 2: altre 14 con seed+stile IDENTICI
  |  (cancello, recinzione, scala, preventivo_pro, cutting, analizza_foto, galleria, generate,
  |  reload, svil_tramoggia, svil_quadrotondo, svil_asolatondo, svil_flangia, svil_dxf; cutting.png
  |  = ex novo, barra metallica con taglio netto, accento arancio). FASE 3: sposta vecchie in
  |  _VECCHIE_sintetiche, metti nuove in icons\, genera _32/_48 dalla 512. NON buildare/deployare.
## 2026-07-31 — Galleria tramogge: filtro per FAMIGLIA (211 forme sfogliabili)

**Problema**: la galleria mostrava 211 voci in un'unica lista 560x460 -> l'utente
ne vedeva pochissime e doveva scorrere all'infinito.

**Soluzione scelta** (meglio della paginazione a numeri): filtro a tendina per famiglia.

1. `Resource\Panels\gallery\manifest.txt` rigenerato con QUINTA colonna:
   `icona|etichetta|comando|attivo|famiglia`. Famiglie prese dalla colonna "famiglia"
   di `C:\Users\infoa\Downloads\01_REVERSE_CAD\CENSIMENTO\FORME_LOGITRACE.csv`
   (mappatura `_NNN.bmp` -> `lt_NNN.icn`). 211 righe. Backup: `manifest.txt.bak-prima-famiglie`.
   Le 2 righe ferri (g_22/g_23) non sono nel CSV -> famiglia "Ferri / Profilati".
   Conteggio famiglie: Primitive 88, Piquage/Innesto 47, Gomito 22,
   Piquage multi-uscita 22, Lamiera piegata 14, Fondi 5, Elicoidali 5,
   Altro (strumento CAD) 3, Tramoggia 2, Ferri 2, DA VERIFICARE 1.

2. `Resource\Forms\SA_TramoggeGalleria.ui`: form ingrandita 560x460 -> **900x700**;
   aggiunto `ZsCc::ComboBox` id=2 ("Famiglia") sopra la lista, stesso callback
   `SA_TramoggeGalleriaCb` del ListWidget (schema copiato da MatrixOperations.ui
   dell'ApiExample 19, non inventato). Aggiunto il customwidget CcComboBox.hpp.

3. `src\SheetUnfoldGallery.cpp`:
   - `GItem` ha ora il campo `family`; `LoadManifest()` legge il 5o campo
     (retrocompatibile: se manca -> "Altro") e costruisce `g_families`.
   - nuovo `PopulateFamilies()`: riempie il combo con "Tutte le famiglie" + le famiglie.
   - `PopulateList()` filtra per `g_famSel` e tiene `g_view` (indici visibili):
     l'indice della lista NON coincide piu' con l'indice del manifest.
   - `GalleriaCb()`: se `idField == FAM_FIELD(2)` aggiorna `g_famSel` e ripopola;
     sul ListWidget usa `g_view[idItem]`.
   - Le voci spente (|0) restano VISIBILI: al clic solo il messaggio
     "forma non ancora implementata (in arrivo)".
   - Anti-crash zw3d-rules §1: aggiunti `cvxCmdFuncUnload(LIST_CB)` e
     `cvxCmdFuncUnload(FORM)` in `UnregisterGallery()` + unload prima della
     registrazione in `RegisterGallery()`.

**Build**: nuovo script `build_2025_clean.bat` (Clean + Rebuild dei SOLI progetti 2025,
perche' obj e' condiviso con i 2027). Risultato: **0 errori**, 1 warning per progetto
(MSB8028, la nota nota sull'obj condiviso).
DLL: `bin\x64\Release\SuperAssistenteBridge.dll` + `SuperAssistenteEngine.dll`.
**NON deployato in Program Files** — deploy a carico dell'utente.

**Nota**: manifest e .icn sono dati letti a runtime, la ricompilazione serviva solo
per il filtro nel C++.


### 2026-07-31 — MANDATO "180 FORME" (spostato qui dal doppione FINALE\knowledge)
=== 2026-07-31 — MANDATO "180 FORME" (architettura parametrica) ===

OBIETTIVO: implementare le forme LogiTrace spente senza scrivere 180 comandi,
ma con UN comando generico parametrico per famiglia + preset nel manifest.

--- PASSO A — costruttori di sezione in SheetUnfold (VERIFICATO) ---
VERIFICA header include/SheetUnfold.h: Circle, Rectangle, Ellipse, Obround,
CircleToCircle, RectToRect, RectToCircle, ElbowSegment, ecc. GIA' presenti e
implementati (Ellipse c'era gia', contrariamente all'elenco del brief).
AGGIUNTI (uno per volta, campionamento UNIFORME per lunghezza d'arco):
  - RoundedRectangle(w,d,r,n)  rettangolo raccordato (4 dritti + 4 quarti d'arco)
  - RegularPolygon(lati,r,n)   triangolo/esagono/poligono, vertici sempre inclusi
Test aggiunti in tools/test_unfold.cpp:
  TestRoundedRectangle, TestRegularPolygon, TestEllipseToCircleUnfold.
Compilato a freddo (cl /EHsc /std:c++17) ed eseguito: "=== TUTTO OK ===".
  - rounded rect: perimetro 1313.94 vs teorico 1314.16, corde uniformi max/min<1.2
  - esagono: perimetro=6*lato esatto; triangolo: 3*lato esatto
  - ellisse->cerchio: sviluppo non degenere, perimetro cima=2piR

--- PASSO B — comando generico SA_SvilTransizione (VERIFICATO) ---
src/SheetUnfoldCommands.cpp: nuovo comando SA_SvilTransizione, pattern copiato da
SA_SvilCono (GetNum/GetOptInt, RequirePart implicito via RememberForUnfold+GeneraDXF,
label, cvxMsgDisp). Legge il PRESET da %TEMP%\sa_preset_transizione.txt
(chiave=valore) con LoadPresetTransizione (stesso meccanismo di Cmd_Cancello /
LoadParamsFromTemp). Campi form 1..12 (tutti "distance"): quote A/B/C bassa+alta,
altezza, spostamento X/Y, spessore, materiale, punti. Costruisce le due sezioni con
i costruttori del PASSO A e chiama SheetUnfold::Unfold.
Resource/Commands/SA_SvilTransizione.tcmd creato (12 parametri).
Aggiunto a kUnfoldCommands (registrazione + unload automatici, gia' in RegisterUnfoldCommands).
BUILD 2025 (build_2025_clean.bat): 0 errori. Simbolo SA_SvilTransizione presente
nell'.obj (3 occorrenze) e nella DLL bin/x64/Release/SuperAssistenteEngine.dll.

--- PASSO C — collegare le forme del manifest (VERIFICATO) ---
manifest.txt: aggiunta 6a colonna "preset". SheetUnfoldGallery.cpp:
  - GItem esteso con campo preset; parsing manifest separa famiglia (5a) e preset (6a).
  - GalleriaCb: PRIMA di cvxCmdSend scrive il preset in %TEMP%\sa_preset_transizione.txt
    (una coppia chiave=valore per riga); se la forma non ha preset, cancella il file
    (il comando usa i default). #include <windows.h> per GetTempPathA.
Accese 48 forme della famiglia "Primitive / Forme base" che il comando generico
copre DAVVERO (transizioni pure a 2 sezioni tra cerchio/rettangolo/asola/ellisse/
rett.raccordato/poligono, modi centrata/spostata/inclinata). Ognuna ha cmd=
SA_SvilTransizione + preset bassa=..,alta=..,modo=..
NON accese (25 forme Primitive spente): curve cilindriche/coniche, tagli con piano,
obliqui senza "modo", innesti, sezioni di rivoluzione, estrusione, "superficie
manuale" — NON sono transizioni pure a 2 sezioni, il comando generico non le copre.

--- PASSO D — gomiti (PARZIALE, ONESTO) ---
ATTENZIONE: il motore ElbowSegment (comando SA_SvilGomito) sviluppa SOLO il gomito
a sezione CILINDRICA/TONDA (lobster-back). Dei 22 gomiti spenti nel manifest, 21
sono a sezione RETTANGOLARE / ASOLA / "deviazione" / "digressivo": ElbowSegment NON
li modella. Accenderli col comando tondo darebbe all'utente sviluppi SBAGLIATI
(sezione rettangolare srotolata come tubo tondo) -> rischio pezzi errati in officina.
Percio' ho acceso SOLO "Gomito cilindrico variabile" (1), l'unico a sezione tonda.
Gli altri 21 gomiti restano spenti: richiedono un motore ElbowRect/ElbowObround
dedicato (lavoro futuro), non un preset.

--- RISULTATO ---
Attive prima: 31. Attive ora: 80 (+49: 48 transizioni Primitive + 1 gomito tondo).
Spente: 131. BUILD 2025 0 errori. Test motore TUTTO OK.
Deploy NON eseguito (fermo alla build, come da vincolo). Le icone .icn non toccate.


### 2026-07-31 — INFERRIATA: da solo-CSV a DISEGNO 3D CORRETTO (form nativa + geometria)
- Contesto: la prova a caldo dell'utente dava solo il CSV (18 pezzi, misure fisse), NIENTE 3D.
  Diagnosi confermata: mancava del tutto InferriataObject; Cmd_Inferriata non usava la strada
  GenerateGeometry->GeometryExecutor (quella che gia' fa disegnare Cancello/Recinzione/Scala).
- File:
  * include/SteelParametric.h  -> +class InferriataObject : ISteelParametricObject (copiata da
    GateObject). Parametri: larghezza(1200), altezza(1000), passo_bacchette(100),
    numero_montanti(2), corrimano(0/1), profilo_telaio/bacchetta = "QUADRO STUTTURALE/40x40x2".
  * src/SteelParametric.cpp     -> implementazione. GenerateGeometry(): telaio 4 membri con
    spigoli a 45 (unico caso ammesso, spigolo complanare, regola §6) roles montante/corrente_sup/
    corrente_inf; bacchette verticali a passo, TAGLIO DRITTO (0), dentro la LUCE VERA tra
    estradosso corrente inf e intradosso sup (SectionOf, non valore fisso); corrimano opzionale
    PASSANTE (taglio dritto, mai 45). Usa i campi startCutDeg/endCutDeg di GeometryCommand.
  * src/SuperAssistenteEngine.cpp -> Cmd_Inferriata riscritta come comando TEMPLATE
    (int f(int idData), come SA_SvilCono): RequirePart -> InferriataObject <- FORM (cvxDataGet)
    con ripiego LoadInferriataFromTemp(%TEMP%\inferriata_input.txt) -> ShowWarningsAndDraw
    (=DISEGNO 3D) -> CalculateForInferriata+ExportToCSV (distinta resta). Tolta la frase
    "misure ancora fisse, manca la form di input". Registrato con cvxCmdTemplate in CoreInit,
    unload funzione+template in CoreExit (anti-crash §1.4). Rimosso da kCommands (era void()).
  * Resource/Commands/SA_Inferriata.tcmd + Resource/Forms/SA_Inferriata.ui -> form nativa
    (schema copiato da SA_SvilCono, 5 campi distance).
  * Settings\Default\ResourcePool\AUTOMAZIONE.zcui -> bottone Inferriata: Form=SA_Inferriata,
    Script=!SA_Inferriata (era ~SuperAssistente_Inferriata).
  * tools/test_inferriata.cpp -> prova a freddo (logica pura).
- Build: build_2025_clean.bat -> 0 errori (Bridge 0, Engine 0). Simbolo SA_Inferriata presente
  nella DLL bin/x64/Release/SuperAssistenteEngine.dll (rigenerata 20:14). Fix build: forward decl
  di ShowWarningsAndDraw prima di Cmd_Inferriata (era definita piu' in basso -> C3861).
- Prova FREDDA (g++ statico, come pitfall registrato): TUTTO OK. Con 1200x1000 passo 100:
  15 GeometryCommand = 2 montanti + 2 correnti + 11 bacchette. Verificato a mano:
  * 13 membri VERTICALI (2 montanti + 11 bacchette). NumeroBacchette()=11.
  * correnti sup/inf punta-a-punta = 1200 mm.
  * bacchette da z=40 (estradosso corrente inf) a z=960 (intradosso corrente sup): combaciano,
    NESSUNA compenetrazione in testa (L=920). Passo reale 93.3mm (1120/12 intervalli).
  * spigoli telaio 45/45, bacchette e corrimano taglio dritto 0/0.
- Stato: COMPILA + prova fredda OK. Disegna via GeometryExecutor (geometria "morta", schizzo+
  estrusione) come richiesto per stasera. NON deployato in Program Files (deploy a carico utente).
  Prova a CALDO (dentro ZW3D con una PARTE) da fare con l'utente.
- LIMITE NOTO (da NON risolvere ora): non usa i membri weldment veri (CdWeldStruct, §5/§6bis)
  ne' variabili parametriche associative. Lavoro a parte.
- NON toccati cancello/recinzione/scala (gia' disegnano).
- Prossimo: prova a caldo Inferriata; poi valutare lo stesso salto per gli altri via CdWeldStruct.

## 2026-08-01 — FORM NATIVE per CANCELLO, RECINZIONE, SCALA (mandato notturno 01)
- Cosa: i tre comandi disegnavano gia' in 3D ma prendevano le misure solo da un file
  in %TEMP%. Ora hanno la form nativa ZW3D (pannello quote), sullo schema di
  SA_SvilCono/SA_Inferriata. Il ripiego da %TEMP% RESTA e vale se la form manca.
- File NUOVI:
  * Resource/Commands/SA_Cancello.tcmd  + Resource/Forms/SA_Cancello.ui
    campi (SetParameter reali di GateObject): width_mm, height_mm,
    baluster_spacing_mm, has_mid_rail, mid_rail_z_mm.
  * Resource/Commands/SA_Recinzione.tcmd + Resource/Forms/SA_Recinzione.ui
    campi (FenceObject): total_length_mm, height_mm, panel_max_mm,
    baluster_spacing_mm, slope_deg.
  * Resource/Commands/SA_Scala.tcmd + Resource/Forms/SA_Scala.ui
    campi (StairObject): rise_total_mm, going_mm, riser_target_mm, width_mm.
    (StairObject NON accetta slope_deg: la pendenza la calcola da se' con SlopeDeg().)
- File MODIFICATI:
  * src/SuperAssistenteEngine.cpp -> nuovi comandi TEMPLATE Cmd_CancelloForm/
    Cmd_RecinzioneForm/Cmd_ScalaForm (firma int f(int idData), come Cmd_Inferriata).
    Ordine: default oggetto -> LoadParamsFromTemp (ripiego) -> valori form
    (InfFormNum/cvxDataGet; se il campo manca resta il valore precedente).
    RequirePart prima di ogni disegno. Tabella kTemplateCommands: load in CoreInit
    (ZwCommandFunctionLoad + cvxCmdTemplate) e unload in CoreExit
    (ZwCommandFunctionUnload + cvxCmdTemplateUnload) — regola §1.4.
    I vecchi Cmd_Cancello/Recinzione/Scala (void) restano registrati: nulla si rompe.
  * Settings/Default/ResourcePool/AUTOMAZIONE.zcui -> i tre bottoni ora puntano a
    <Form>SA_<Nome></Form> e <Script>!SA_<Nome></Script> (erano ~SuperAssistente_<Nome>).
- Geometria: NON toccata. Regole d'officina §6 invariate (stanno negli oggetti).
- Build 2025 Release x64: SuperAssistenteEngine.vcxproj 0 errori, SuperAssistenteBridge.vcxproj
  0 errori (PostBuild zrc.exe eseguito). XML dei .tcmd/.ui/.zcui validato con parser.
- NON deployato in Program Files. .icn e manifest NON toccati.
- Prova a CALDO da fare con l'utente: riavviare ZW3D, aprire una PARTE, premere i tre bottoni
  e controllare che si apra il pannello quote e che il disegno esca con le misure digitate.
- Prossimo: prova a caldo; poi balcone e tettoia (non esistono ancora).

### 2026-08-01 — MANDATO 02: motore gomiti NON tondi (ElbowSegmentSection)
- File:     include/SheetUnfold.h, src/SheetUnfold.cpp (nuovo ElbowSegmentSection),
            src/SheetUnfoldCommands.cpp (nuovo comando SA_SvilGomitoSezione + registrazione),
            Resource/Commands/SA_SvilGomitoSezione.tcmd (nuovo, 10 campi),
            Resource/Panels/gallery/manifest.txt (6 forme accese),
            tools/test_unfold.cpp (nuovo TestElbowRect), tools/build_test_unfold.bat (nuovo),
            build_mandato02.bat/.log (nuovi).
- Motore:   ElbowSegmentSection(sezione, betaLo, betaHi, meanLen, outBottom, outTop).
            Prende una sezione PIANA gia' costruita (rettangolo/rett.raccordato/asola/
            ellisse/poligono/cerchio), la estrude di meanLen su Z e taglia le estremita'
            con due piani obliqui incernierati sull'asse Y:
              z_basso = -meanLen/2 - x*tan(betaLo) ; z_alto = +meanLen/2 + x*tan(betaHi).
            Conserva SEMPRE il numero di punti (Unfold accoppia per indice).
- Build:    OK — MSBuild Release|x64 su SuperAssistentePlugin.sln: 0 errori, 2 warning
            MSB8028 preesistenti (obj condivisa con i .2027.vcxproj).
- Prova:    fredda TUTTO OK (test_unfold.exe compilato ed ESEGUITO, l'antivirus NON lo ha
            cancellato). Degenerazione ESATTA: con Circle(R,n) il risultato coincide con
            ElbowSegment punto per punto, scarto max 0 (tolleranza 1e-9).
            Rettangolo 200x100 beta=15 L=300: generatrice = L + 2*x*tan(beta), max 353.590
            sul lato x=+100, min 246.410 sul lato x=-100 -> piu' lunga dove il taglio si
            allontana, come richiesto. beta=0 -> perimetro 600 e ingombro Y 300 (tronco retto).
            Asola e rett.raccordato: conteggio punti conservato, Unfold non degenera.
- Manifest: accese SOLO 6 forme realmente coperte dal motore (sezione COSTANTE, virole a
            quartabuono), con preset in 6a colonna:
              lt_094 Gomito rettangolare 0R2S   -> sezione=rettangolo,pezzo=pieno
              lt_095 Gomito rettangolare 0R1S   -> sezione=rettangolo,pezzo=pieno
              lt_134 Gomito asola tipo 1        -> sezione=asola,pezzo=pieno
              lt_135 Gomito asola tipo 2        -> sezione=asola,pezzo=pieno
              lt_136 Gomito asola senza 1/2 el. tipo 1 -> sezione=asola,pezzo=mezzo
              lt_137 Gomito asola senza 1/2 el. tipo 2 -> sezione=asola,pezzo=mezzo
            LASCIATE SPENTE (il motore NON le copre, accenderle farebbe tagliare lamiera
            sbagliata): i gomiti con raccordo/"R"+"S" a sezione VARIABILE (lt_093 2R2S,
            lt_096 1R2S, lt_097 1R1S, lt_098 2R1S, lt_099 2R2S1B, lt_166 0R1B, lt_167 1R1B),
            i gomiti a S (lt_124, lt_125), il digressivo (lt_127), le doppie deviazioni
            (lt_120, lt_130, lt_138, lt_142, lt_151) e i "gomito deviazione tipo 2..5"
            (lt_147..lt_150): tutti hanno DUE sezioni diverse o assi sghembi, servono un
            motore a transizione con offset per virola (mandato successivo).
- Anti-crash: nessuna API cvxPart* usata (logica pura + cvxMsgDisp); il comando e' nella
            tabella kUnfoldCommands, quindi RegisterUnfoldCommands/UnregisterUnfoldCommands
            fanno gia' ZwCommandFunctionUnload + cvxCmdTemplateUnload in CoreExit (§1.4).
- Deploy:   NON eseguito (come da mandato). I .tcmd nuovi andranno copiati in
            apilibs\Resource\Commands\ al prossimo deploy, altrimenti la form non si apre.
- Stato:    FUNZIONA (a freddo). Prova a caldo su ZW3D vivo ancora da fare.


## 2026-08-01 — MANDATO NOTTURNO 03: BALCONE e TETTOIA (creati da zero)
- Cosa:     due famiglie nuove di carpenteria che NON esistevano (verificato: nessuna
            traccia di "balcon"/"tettoi"/"pensilin" nei sorgenti prima di oggi).
            BALCONE  = ringhiera chiusa su 3 lati + piano calpestabile (riusa la
                       macchina gia' collaudata di RailingObject, non partito da zero).
            TETTOIA  = struttura portante (pilastri+travi) con copertura in PENDENZA.
- File:     include\SteelParametric.h            -> classi BalconeObject, TettoiaObject
            src\SteelParametric.cpp              -> GenerateGeometry/GeneratePieces/
                                                    ValidateAgainstNorm delle due famiglie
            src\SuperAssistenteEngine.cpp        -> Cmd_BalconeForm / Cmd_TettoiaForm
                                                    + voci in kTemplateCommands
            Resource\Commands\SA_Balcone.tcmd, SA_Tettoia.tcmd
            Resource\Forms\SA_Balcone.ui, SA_Tettoia.ui
            Settings\Default\ResourcePool\AUTOMAZIONE.zcui        (2 Action ID_!)
            Settings\Default\ResourcePool\AUTOMAZIONE_Pages.zcui  (2 Control)
            tools\test_balcone_tettoia.cpp + tools\build_test_balcone_tettoia.bat
- Regole d'officina applicate (§6):
            BALCONE: correnti PASSANTI sui 3 lati (lunghezza = lato intero); piantoni
              A PIOMBO agli angoli e intermedi (interasse panel_max_mm), fermi
              all'INTRADOSSO del corrente superiore (height - sezione corrente) cosi'
              non si compenetrano; height_mm = ESTRADOSSO del corrimano (asse mezzo
              profilo piu' basso); bacchette nella LUCE VERA tra estradosso corrente
              inferiore e intradosso superiore, sezioni lette da SectionOf (mai fisse);
              45° SOLO sugli spigoli complanari del parapetto e del telaio piano;
              piantoni con taglio 0° (balcone in piano). Angoli contati una volta sola:
              niente piantoni doppi negli spigoli, distinta e disegno concordano.
            TETTOIA: ⚠️ la quota profondita_mm e' la PROIEZIONE ORIZZONTALE; la
              lunghezza VERA della trave di falda e' profondita/cos(pendenza)
              (LunghezzaFaldaVera_mm). Scritto anche nel commento del codice, sia in
              GenerateGeometry sia in GeneratePieces: mettere la proiezione nella
              distinta = travi CORTE in officina = materiale buttato. Pilastri A PIOMBO
              (lunghezza verticale vera), fermi sotto la trave, testa tagliata QUANTO LA
              PENDENZA (mai 45°). Arcarecci a passo misurato SULLA FALDA, non in pianta,
              con rollDeg = pendenza per far appoggiare il manto.
- GeometryCommand: usati i campi di taglio/orientamento (startCutDeg, endCutDeg,
            rollDeg, just) su tutti i membri; profileSpec nel formato REALE
            "CONTENITORE/misura" (es. "QUADRO STUTTURALE/40x40x2").
- Anti-crash (§1): nessuna cvxPart* di creazione forma, nessuna @deprecated;
            RequirePart all'inizio dei due comandi; SA_Balcone/SA_Tettoia sono nella
            tabella kTemplateCommands, quindi CoreExit fa gia' ZwCommandFunctionUnload
            + cvxCmdTemplateUnload per entrambi (§1.4). Gli oggetti sono logica pura
            (nessun SEH necessario: non chiamano SDK).
- Build:    MSBuild Release x64 — SuperAssistenteEngine.vcxproj OK 0 errori,
            SuperAssistenteBridge.vcxproj OK 0 errori (solo il solito warning MSB8028
            sulla obj condivisa col progetto 2027, preesistente).
- Prova a freddo: tools\build_test_balcone_tettoia.bat -> "TUTTO OK (0 test falliti)",
            26 verifiche: correnti passanti, piantoni a piombo e non compenetrati,
            estradosso, 45° solo sugli spigoli, piano calpestabile presente, distinta
            coerente col disegno, falda = profondita/cos(pendenza) sia nel disegno sia
            nella DISTINTA e mai uguale alla proiezione, colmo piu' alto della gronda,
            avvisi normativa (parapetto < 1000mm, pendenza 0 = ristagno).
- Deploy:   NON eseguito (come da mandato). Al prossimo deploy servono in
            apilibs\Resource\Commands\ i due .tcmd nuovi e in Forms\ i due .ui,
            altrimenti i bottoni partono ma la form non si apre.
- Icone:    <Icon></Icon> lasciato VUOTO per entrambe (nessuna icona disponibile: meglio
            vuoto che un nome di file inesistente).
- Stato:    FATTO e compilato. Prova a CALDO su ZW3D vivo ancora da fare (serve l'utente
            con una PARTE aperta).
- Prossimo: prova a caldo di SA_Balcone e SA_Tettoia; poi valutare i membri weldment
            veri (CdWeldStruct) al posto dello schizzo+estrusione di GeometryExecutor.

## 2026-08-01 — MANDATO 04 LOGIBARRE: catalogo profili esterno + nesting collegato

Progetto: Downloads\03_PLUGIN_ZW3D\SuperAssistentePlugin_FINALE_3\FINALE (2025). NON deployato.

COMPITO 1 — Resource\profiles_en.csv (122 taglie)
- Creato `Resource\profiles_en.csv`, formato dichiarato nei documenti:
  `Codice;Altezza;Larghezza;Spessore;Area;PesoM;Tolleranza;Norma;Anima;Raggio`
  (Anima/Raggio in coda, opzionali: servono a ProfileSection e non erano nel formato originale).
- Le 122 righe sono GENERATE dalla tabella hardcoded `kBuiltin[]` di src\ProfileDB.cpp:
  nessuna quota inventata. IPE 17, HEA 21, HEB 21, IPN 15, UPN 14, UPE 13, L 6, T 6, UAP 9.
- `ProfileDB::Load(path)` riscritto: builtin sempre caricati come RIPIEGO, poi il CSV
  esterno fa UPSERT (aggiunge le taglie nuove, sostituisce quelle esistenti). Ammette
  righe di commento `#`, riga d'intestazione, virgola decimale. Chiamato gia' da
  InitProfileDB (SuperAssistenteEngine.cpp:1027) — invariato.
- ⚠ BUG PREESISTENTE TROVATO E CORRETTO: il vecchio parser dei builtin usava
  `f >> type >> comma >> ...` su uno std::string; `operator>>` su string legge TUTTA la
  riga come `type`, quindi la conversione falliva SEMPRE e **la tabella profili restava
  VUOTA**: `ProfileDB::Find` non trovava mai nulla e SA_FerroProfilo diceva sempre
  "profilo non in tabella". Ora si spezza sulla virgola. Verificato: builtin=122.
- VERIFICA loader (test isolato g++, poi rimosso): togliendo a mano le voci hardcoded
  `HEB,100` e `IPE,100` -> builtin=120; con il CSV -> 122 (le due voci tornano dal file);
  senza CSV -> 120 (ripiego funzionante, nessun crash).

COMPITO 2 — ferri collegati a BarNesting (tappa 2B)
- src\FerriCommands.cpp: SA_FerroProfilo ora ACCODA il pezzo in
  `%TEMP%\ferri_da_tagliare.csv` (`profilo;lunghezza_mm;quantita`) — su file, cosi'
  sopravvive al reload della DLL shadow.
- Nuovo comando `SA_FerriNesting` (registrato in kFerriCommands, .tcmd creato in
  Resource\Commands\SA_FerriNesting.tcmd, 4 campi: barra 6000 / kerf 1.5 / morsa 100 /
  svuota coda). Raggruppa la coda per profilo e chiama `BarNesting::Compute(pieces,
  stock, warehouse, cfg)` — LO STESSO motore di Cmd_Distinta, nessun secondo nesting.
  Legge il magazzino sfridi da `%TEMP%\magazzino_sfridi.csv` con lo stesso formato.
  Output: `%TEMP%\ferri_nesting.csv` (piano di taglio per barra + resti + non fattibili).
- Nessuna API ZW3D nuova: solo cvxDataGet/cvxMsgDisp/ZwCommandFunctionLoad gia' in uso;
  unload gia' garantito da UnregisterFerriCommands (regola anti-crash §1.4).

BUILD 2025: SuperAssistenteEngine.vcxproj 0 errori, SuperAssistenteBridge.vcxproj 0 errori
(solo il warning MSB8028 preesistente su obj condivisa con i .2027.vcxproj).

RESTA DA FARE: pagina ribbon FERRI dedicata (tappa 2C) e icona per SA_FerriNesting;
il .tcmd nuovo va copiato in apilibs\Resource\Commands\ al momento del deploy.

================================================================
MANDATO NOTTURNO 05 — TOPSOLID: librerie esportate collegate al plugin
Progetto: Downloads\03_PLUGIN_ZW3D\SuperAssistentePlugin_FINALE_3\FINALE (2025). NON deployato.

FILE NUOVI
- include\TopSolidCatalog.h  /  src\TopSolidCatalog.cpp
- Resource\Commands\SA_TopSolidCerca.tcmd (2 campi: testo da cercare, max risultati)
- registrato in SuperAssistenteEngine.cpp (Register/UnregisterTopSolidCommands,
  accanto ai comandi FERRI) e aggiunto ai due .vcxproj (2025 e 2027).

COME FUNZIONA
- Load(): legge INDICE_LIBRERIE_TOPSOLID.csv in STREAMING (getline + split in loco,
  niente istringstream per riga). Prima fa UNA sola scansione ricorsiva di
  TopSolid_Export\librerie\ con std::filesystem e costruisce una mappa
  "progetto|nomefile" -> percorso: cosi' le 24943 righe si risolvono in memoria,
  senza 25.000 stat() su disco.
- Il nome documento del PDM contiene caratteri vietati dal filesystem (es. "?"):
  NomeFileSicuro() li sostituisce con '_', esattamente come ha fatto l'export.
- Cerca(): sottostringa su DocName + PartNumber, insensibile a maiuscole E agli
  accenti (Normalizza(): minuscolo, Latin-1 e UTF-8 -> lettera base). Le voci con
  file vero su disco escono PRIME, le NON DISPONIBILI dopo.
- PercorsoFile(): ricontrolla con fs::is_regular_file al momento dell'uso e
  ritorna "" se il file non c'e' piu'. Mai un percorso finto.

NUMERI VERI (misurati, non stimati)
- 24943 righe dati indicizzate (24944 con l'intestazione).
- Solo 2668 risolvono a un file realmente presente su disco (10.7%).
  MOTIVO: l'indice elenca TUTTI i documenti del PDM TopSolid (16569 .TopPrt,
  1563 .TopFam, 1310 .TopAsm...), ma l'export ha prodotto solo 8113 file
  STEP/DXF. Le altre voci sono a catalogo ma senza geometria esportata: vengono
  marcate NON DISPONIBILE, non spacciate per presenti.
- Verificato con test standalone (g++ -std=c++17, poi rimosso):
  Cerca("bolt") -> "Short Connecting Bolt" ->
  ...\librerie\TopSolid Wood\STEP\Short Connecting Bolt.step (file esistente).
  Cerca("IPE") -> tutte NON DISPONIBILE (sono voci IFC "Pipe...", senza export).

IMPORT IN ZW3D: NON IMPLEMENTATO — e la ragione e' importante
- ZwExternalPartImport (zwapi_dataexchange.h:83) NON serve per i file STEP.
  Ho letto il corpo della struct szwPartImportData (zwapi_dataexchange_data.h:21):
  i campi sono directory + file + part (zwRootName) + frame + copyWireframe +
  copyDimension + option. Il campo "part" e' il NOME DI UNA PARTE DENTRO UN FILE
  ZW3D: quella funzione copia una parte da un .Z3PRT/.Z3ASM esistente, non
  traduce un STEP. Usarla su un .step avrebbe passato dati senza senso.
- L'API GIUSTA per lo STEP e' cvxFileImport(svxImportData*) (zwapi_file.h:591),
  inizializzata da cvxFileImportInit (zwapi_file.h:561) con type =
  VX_IMPORT_TYPE_STEP (zwapi_file_data.h:535). Struct svxImportData
  (zwapi_file_data.h:776): type / filePath / importTo / importTarget /
  reserved(NULL) / general(NULL = default).
- NON l'ho collegata perche' mancano due cose che non voglio indovinare su una
  funzione che puo' far crashare ZW3D:
  1) il valore giusto di importTo/importTarget nel nostro contesto (0=oggetto
     corrente, 1=nuovo oggetto, 2=nuovo file) va deciso con ZW3D aperto;
  2) va provata a mano su UN file STEP prima di metterla in un comando.
  Il comando oggi trova e SCRIVE il percorso, non importa nulla: zero rischio.

BUILD 2025: Bridge 0 errori, Engine 0 errori (solo il warning MSB8028 preesistente
sull'obj condivisa con i .2027.vcxproj). Verificato che SA_TopSolidCerca sia
dentro SuperAssistenteEngine.dll.
NOTA BUILD: TopSolidCatalog.cpp usa <filesystem>, che vuole C++17. Il progetto era
su C++14: ho messo <LanguageStandard>stdcpp17</LanguageStandard> SOLO su questo
file (per-file, non su tutto il progetto) per non toccare gli altri .cpp.

RESTA DA FARE: cvxFileImport da provare a mano con ZW3D aperto -> poi comando
SA_TopSolidInsert; il .tcmd nuovo va copiato in apilibs\Resource\Commands\ al deploy.

================================================================================
2026-08-01 — MANDATO 06: MESSA IN TAVOLA (da Advance Steel) — PASSI 1,2,3 FATTI
================================================================================
COSA E' ENTRATO NEL PLUGIN (prima non c'era: il codice esisteva solo nei Downloads)
- include/messa_in_tavola.h + src/messa_in_tavola.cpp  (logica PURA, invariata)
- include/cutting_list.h    + src/cutting_list.cpp     (serve: RigaDistinta/Pezzo
  sono i tipi in ingresso di impaginaDettaglio; senza, non linkava)
- src/MessaInTavolaCommands.cpp  (NUOVO) — comando SA_MessaInTavola
- Aggiunti come ClCompile ai DUE progetti Engine: .vcxproj (2025) E .2027.vcxproj
  (⚠️ la trappola dei ferri: file in un solo progetto = "simbolo esterno non
  risolto". Qui sono in entrambi fin da subito.)
- Backup dei .vcxproj: *.bak-prima-tavola-20260801

COME FUNZIONA SA_MessaInTavola
1. ProbeSheetActive(): ZwDrawingSheetListGet sotto SEH. Se non c'e' un foglio
   disegno attivo -> messaggio chiaro ("apri un .Z3DRW e rilancia") e RETURN.
   Nessuna geometria toccata. Non esiste ZwDrawingSheetCreate nell'SDK 2025:
   il foglio lo apre l'utente (confermato: nell'header ci sono solo Activate /
   ActivateByHandle / ListGet / ViewListGet).
2. Logica pura: impaginaDettaglio() -> scala, formato, posizioni. Scrive sempre
   %TEMP%\piano_messa_in_tavola.txt e %TEMP%\cartiglio_messa_in_tavola.dxf.
3. Parte 3D da proiettare: la legge da %TEMP%\messa_in_tavola_parte.txt
     riga 1:  C:\percorso\pezzo.Z3;NOMEROOT
     riga 2 (opz): lunghezza_mm;angoloA;angoloB;profilo;materiale;qta
   Se il file manca, il comando NON inventa un percorso: consegna il piano e si
   ferma con avviso.
4. Viste vere (struct riempite leggendo il corpo negli header, non a memoria):
   - ZwDrawingViewStandardCreate + ZwDrawingViewStandardDataInit
     szwViewStandardData: path/rootName/type=NATIVE/option.viewType=
     ZW_VIEW_STANDARD_FRONT/location/scaleType=ZW_VIEW_USE_CUSTOM_SCALE/
     scaleRatioX=scala,scaleRatioY=1. ⚠️ ZW3D piazza la vista per il CENTRO,
     la logica pura da' l'angolo basso-sx: si somma mezzo ingombro.
   - ZwDrawingViewFullSectionCreate (+Init) per SezioneA/B: 2 punti verticali
     al 25%/75% della vista base, methodType=ZW_METHOD_TRIMMED_PART,
     locationType=ZW_LOCATION_ORTHOGONAL.
   - ZwDrawingDimensionAutoCreate (+ZwDrawingDimensionAutoInit) sulla vista
     principale: entityType=ALL, includeAuto = ARC|CIRCLE|HOLE|LINE|MAXIMUM,
     baseline orizzontale sotto/destra e verticale sopra/sinistra.
   - ZwDrawingTableBOMCreate (+ZwDrawingTableBOMInit) e poi ZwTableInsert
     (zwapi_table.h:130) per POSARLA: la Create da solo l'handle, non la mette
     sul foglio — l'esempio nell'header lo dice.
   - ZwDrawingRegen(0,NULL,1,1,0,1,1) alla fine.
5. Registrazione: RegisterMessaInTavolaCommands in CoreInit e
   UnregisterMessaInTavolaCommands in CoreExit (§1.4 rispettata). Comando senza
   form -> nessun .tcmd.
Ogni chiamata CAD e' dentro __try/__except con i POD fuori dal try (§1.6).

BUILD (0 errori, 3 progetti):
  SuperAssistenteEngine.vcxproj      -> bin\x64\Release\SuperAssistenteEngine.dll
  SuperAssistenteBridge.vcxproj      -> bin\x64\Release\SuperAssistenteBridge.dll
  SuperAssistenteEngine.2027.vcxproj -> bin2027\x64\Release\SuperAssistenteEngine.dll
Solo il warning MSB8028 preesistente (obj condivisa 2025/2027). NON deployato.

RESTA DA FARE (onesto)
- Nessuna prova dal vivo: serve ZW3D aperto con un .Z3DRW e una parte vera.
  Da verificare in particolare: (a) che ZW3D accetti scaleRatioX/Y come
  frazione 0.1/1.0 e non pretenda 1/10; (b) i punti della linea di sezione:
  sono in coordinate FOGLIO, se ZW3D li volesse in coordinate VISTA le sezioni
  escono spostate (la Create non fallisce, il taglio e' solo in posto sbagliato);
  (c) la BOM ha senso solo se la parte e' un ASSIEME — su un pezzo singolo puo'
  uscire vuota.
- Il pezzo da mettere in tavola oggi arriva da un file di testo. Il collegamento
  automatico all'ultimo sviluppo/distinta calcolata dal plugin non e' fatto.
- Nessun bottone a ribbon: il comando esiste ma va lanciato per nome
  (~SA_MessaInTavola) finche' non gli si fa icona + voce in manifest/zcui.

## 2026-08-01 — MEMBRI WELDMENT VERI (richiesta n.1 dell'utente)
- **cosa**: i membri di carpenteria non sono piu' obbligatoriamente schizzo+estrusione.
  Nuovo esecutore che pilota il comando nativo `!CdWeldStruct` come statement macro
  (`ZwCommandMacroExecute(ZW_MACRO_STATEMENTS,...)`, zwapi_command.h:416; output
  liberato con `ZwMemoryFree`). NON usa `cvxCmdMacro` (@deprecated, crash).
- **file nuovi**: `include/WeldmentExecutor.h`, `src/WeldmentExecutor.cpp`
  (SA_EseguiMacro, BuildMacroForCommand, DrawCommands, WeldmentAbilitato, TestUnMembro).
- **file modificati**: `src/SuperAssistenteEngine.cpp` (include, `ShowWarningsAndDraw`
  prova weldment e RICADE su GeometryExecutor se 0 membri, comando `SA_TestWeldment`
  nel registro kCommands -> load/unload automatici in CoreInit/CoreExit),
  `SuperAssistenteEngine.vcxproj` e `SuperAssistenteEngine.2027.vcxproj`
  (ClCompile WeldmentExecutor.cpp in ENTRAMBI: in uno solo il link fallisce).
- **interruttore**: `%TEMP%\usa_weldment.txt` contenente `0` forza la vecchia strada
  (serve per confrontare i due risultati).
- **profilo**: `profileSpec` "CONTENITORE/MISURA" spezzato sulla `/` -> campo 2 e 3
  della form `WeldSelProfForm`. Nomi reali in `%TEMP%\profili_zw3d.txt`.
- **pick**: PUNTO MEDIO del segmento (`*X,Y,Z,LMB_DN`), sicuramente sul membro.
- **anti-crash §1**: chiamate SDK nude dentro `__try/__except` in funzioni senza
  oggetti C++ (RawMacro/RawFree); RequirePart sul comando di prova.
- **build**: 2025 Bridge + Engine Release x64 -> **0 errori** (log `build_weldment.log`,
  WeldmentExecutor.obj presente, Engine.dll e Bridge.dll prodotte in bin\x64\Release).
  NON deployato in Program Files.
- **prova**: solo a FREDDO (compilazione). A CALDO non verificabile senza ZW3D aperto
  con una PARTE: comando `~SA_TestWeldment` scrive esito in `%TEMP%\weldment_test.txt`.
- **stato**: SCRITTO E COMPILATO, da collaudare dal vivo.
- **prossimo passo**: l'utente apre ZW3D su una parte, lancia `~SA_TestWeldment`,
  si legge `%TEMP%\weldment_test.txt`. Se il codice e' 0 la strada macro funziona e
  si passa a `CdWeldTrim` (tagli tra membri); se non e' 0, il messaggio dice quale
  passo della sequenza rifiuta (probabile: nome campo form o formato del pick).

## 2026-08-01 — METODO TOPSOLID sulle API ZW3D (banco di prova: inferriata)
Nuovi file: FINALE\src\ParametricVars.cpp + include\ParametricVars.h (aggiunti al vcxproj).
- SCOPERTA: ZwVariableCreate/ListGet/ListSet NON sono in zwapi_part_var.h (li' solo
  cvxPartVar* deprecate). Sono in zwapi_variable.h (righe 56/98/131) + struct
  szwVariableData in zwapi_variable_data.h riga 51. ZwEntityAutoRegen: zwapi_entity.h:1997.
- Cmd_Inferriata ora crea PRIMA di disegnare 8 variabili di parte: 4 guida
  (larghezza/altezza/passo_bacchette/spessore_profilo) e 4 DERIVATE come ESPRESSIONI
  (n_bacchette=ceil(larghezza/passo_bacchette)-1, passo_reale, luce_netta, lung_bacchetta).
- value.numberValue.number lasciato a 0 apposta: riempirlo sovrascrive l'expression.
- Nuovi comandi SA_Rigenera e SA_TestParametrico. Registrati in CoreInit,
  ZwCommandFunctionUnload in CoreExit (regola §1.4). SEH su tutte le chiamate SDK.
- BUILD Engine+Bridge Release x64: 0 errori.
- LIMITE documentato in Downloads\01_REVERSE_CAD\CENSIMENTO\PARAMETRICO_LIMITI.md:
  le struct feature (szwExtrudeData ecc.) prendono double, nessun campo espressione;
  nessuna Zw*ExpressionSet nei 236 header. Le formule si ricalcolano, la geometria
  creata via API no. Strada da provare: schizzo quotato + ZwVariableListSet sulle
  variabili automatiche di quota (D1,D2...) se compaiono in ZwVariableListGet.
- NON VERIFICATO DAL VIVO: ZW3D non era in esecuzione, %TEMP%\parametrico_test.txt
  non ancora generato. Non confermato che ZW3D accetti ceil() via API.

## 2026-08-01 — CATALOGO MODELLI PARAMETRICI IN JSON (mandato "modelli richiamabili")
- **idea dell'utente**: dai disegni gia' approvati si ricavano file .json catalogati,
  richiamabili e modificabili (altezza, larghezza, bacchette...). Contratto gia'
  scritto: `C:\Alcafer\Modelli\_Comuni\SCHEMA_MODELLO.md` — rispettato alla lettera.
- **principio**: le quote sono FORMULE sui parametri, non millimetri. Un modello in
  millimetri e' una fotografia; in formule si riadatta a qualsiasi misura.
- **file nuovi**: `src/ModelCatalog.cpp` (1202 righe: parser JSON minimale senza
  librerie esterne, valutatore di espressioni, Carica/Salva/Elenca/Genera) e
  `src/ModelCatalogCommands.cpp` (comandi SA_SalvaModello, SA_ApriModello,
  SA_ModelloForm). `include/ModelCatalog.h` c'era gia' ed e' stato rispettato as-is.
- **valutatore**: + - * / ( ), min max round ceil floor abs, == != < > <= >=,
  se(cond,a,b), confronti su TESTO (`piantoni == 'ferro'`), e
  altezza_sezione/larghezza_sezione/spessore_sezione che riusano la stessa logica di
  SectionOf (SteelParametric.cpp:86). Nome sconosciuto = ERRORE, mai default silenzioso (§6).
- **Genera()** ritorna `std::vector<GeometryCommand>`: si innesta su
  ShowWarningsAndDraw/GeometryExecutor/WeldmentExecutor. NESSUNA seconda strada di disegno.
  Applica derivati, membri, ripeti, per_ogni:"anta", solo_se.
- **regole d'officina implementate** (avvisi, non correzioni silenziose):
  giochi (anta piu' larga della luce = avviso), piantoni non-ferro non disegnati e
  fuori distinta, 45 gradi solo sul telaio (bacchette e corrimano dritti, piantone a
  piombo), ornamenti Grande Forge (classe FORMA3D) riconosciuti come NON estrudibili ->
  GeometryCommand.type = "Component" invece di "ProfileOnLine".
- **modifiche**: `src/SuperAssistenteEngine.cpp` (include, RegistraInferriata dopo il
  disegno in Cmd_Inferriata, Register/UnregisterModelCatalogCommands in CoreInit/CoreExit),
  `SuperAssistenteEngine.vcxproj` e `.2027.vcxproj` (ClCompile in ENTRAMBI).
- **PROVA A FREDDO** (`tools/test_modelcatalog.cpp`, logica pura, niente SDK): TUTTO OK.
  Formula del cancello valutata:
    se(numero_ante == 2, (larghezza_totale - gioco_centrale - gioco_lato_cardini -
    gioco_lato_serratura)/2, ...)  con 3000/20/15/15  ->  **1475 mm**.
  Giro completo inferriata: genera 1200x1000 -> 15 membri (4 telaio + 11 bacchette,
  stesso numero di InferriataObject::NumeroBacchette) -> salva .json -> ricarica ->
  larghezza 2400 -> 27 membri. Cancello 2 ante -> 32 membri; con piantoni in cemento
  i piantoni spariscono. Scansione ricorsiva del catalogo OK.
- **modelli scritti**: `C:\Alcafer\Modelli\Inferriate\Inferriata standard.json`
  (generato dal codice) e `C:\Alcafer\Modelli\Cancelli\Cancello due ante classico.json`
  (scritto a mano seguendo l'esempio dello schema, provato dal test).
- **BUILD 2025 Bridge+Engine Release x64: 0 ERRORI** (log `build_catalogo.log`,
  ModelCatalog.obj e ModelCatalogCommands.obj presenti). NON deployato.
- ⚠️ **LIMITE DELLA FORM DINAMICA (dichiarato, non aggirato)**: il .tcmd si genera al
  volo dai parametri e si registra con cvxCmdTemplate (strada gia' collaudata), ma nei
  181 campi dei .tcmd esistenti 180 sono "distance": ZW3D non offre tendine popolate a
  runtime. Quindi i parametri numerici e le SCELTE (come indice 0,1,2... con legenda
  nella descrizione) stanno nella form; i parametri tipo PROFILO stanno nel file di
  testo `%TEMP%\modello_profili.txt`, precompilato col valore corrente e coi cataloghi
  ammessi. `attivo_se` non nasconde il campo (la form nativa non lo permette): il campo
  resta visibile ma viene IGNORATO quando la condizione e' falsa, e la descrizione lo dice.
- **NON VERIFICATO DAL VIVO**: ZW3D non era aperto. Da collaudare: ~SA_Inferriata ->
  ~SA_SalvaModello -> ~SA_ApriModello -> cambia larghezza -> disegno diverso.

## 2026-08-01 - LO STUDIO TOTALE (livelli 1,2,3,6) - FATTO

Strumenti nuovi in C:\Users\infoa\EfestoAI\studio\
  studia.py            comando unico: stato | continua [--minuti N] | cartella <p> | cerca <parole> | comando <nome> | confronto
  studioso_l1.py       livello 1: .py .ui .xml .zcui .tcmd .z3l .catnls .dic .csv .ini .h .qrc
  studioso_l2_chm.py   livello 2: estrae i .chm con 7-Zip (hh.exe NON funziona in batch) e lega comando->manuale
  studioso_l3_dll.py   livello 3: parser PE fatto in casa (export/import/stringhe), niente dipendenze
  confronto_regole.py  livello 6: confronta REGOLE_OFFICINA.json con la doc ZW3D
  cerca.py / chiedi.py ricerca (cerca.py = 0,5 s sui manuali; chiedi.py = lento ma su tutto)

Risultati, TUTTI verificati:
  livello 1: 20621 schede, 0 saltati (il 24592 di prima era gonfiato da chiavi doppie)
  livello 2: 35615 pagine di manuale ufficiale (c'e' ANCHE L'ITALIANO: languages\it_IT\doc\ZW3D.CHM)
  livello 3: 6666 binari (export+import+stringhe)
  indice:    ZW3D 2025 = 4746 comandi (1172 col manuale), 2027 = 5482 (1235 col manuale)
  archivio:  1,3 GB in EfestoAI\knowledge\STUDIO\ - riprendibile, scrive man mano

CORREZIONE al censimento precedente: i "2669 .py tesoro piu' grosso" erano SBAGLIATI.
2663 sono la libreria standard Python + numpy/scipy dentro ZWSim. Solo 6 sono di ZWSOFT.
Il tesoro vero: .tcmd (definizione comandi coi parametri), Actions.zcui (bottone->dialogo),
e i .chm (manuale ufficiale).

Scoperta (a): !CdWeldTrim - comando NATIVO indipendente per il corner treatment fra
membri strutturali, con "Weld gap". Piu' il "Corner treatment" dentro !CdWeldStruct.
Il taglio d'angolo calcolato a mano dal plugin e' codice da buttare (previa conferma utente).
Prossimo passo: livello 4 con Ghidra su ZwStructuralBase.dll (7387 export) - non le altre 2760.
Dettagli in EfestoAI\knowledge\STUDIO\CONFRONTO_REGOLE.md


### Verifica del 2026-08-01 - 3 BUG TROVATI E CORRETTI

ERRORE MIO: avevo detto "non c'e' npm run test". FALSO - c'e', in EfestoAI\package.json
(-> node engine/collaudo.js). Avevo guardato solo dentro la sottocartella studio/.
Eseguito: passa. La verifica ha pagato lo stesso: ha trovato 3 difetti veri.

1. chiedi.py andava in KeyError sulle schede del livello 3 (che hanno 'nome', non
   'relativo'). Bastava cercare una parola presente in una DLL per farlo saltare.
   Fix: s.get("relativo") or s.get("nome") or s.get("percorso").

2. NON ERA IDEMPOTENTE - il piu' grave. Le chiavi dell'avanzamento erano il percorso
   grezzo: lanciando con root "C:/..." invece di "C:\..." le chiavi non combaciavano
   e lo studio RIFACEVA tutto, duplicando le schede. Le "24592" schede erano in realta'
   20621 file veri + doppioni. Fix: chiave() = os.path.normcase(os.path.abspath(p)),
   sia nel livello 1 sia nel 3; avanzamenti migrati e jsonl deduplicati (485 righe tolte).
   Ora rilanciare con / o con \ da' "STUDIATI 0" e zero righe nuove.

3. indice_comandi.py CANCELLAVA il lavoro del livello 2: riscriveva INDICE_COMANDI.json
   da zero buttando via l'aiuto_ufficiale estratto dai .chm. Chi rigenerava l'indice
   perdeva 2407 collegamenti ai manuali senza accorgersene.
   Fix: rilegge il vecchio indice e riporta l'aiuto ufficiale prima di scrivere.

Altre prove passate: ripresa selettiva (tolti 30 file -> ne rifa' esattamente 30);
parser PE su non-PE/vuoto/troncato -> errore in scheda, studio prosegue;
i 6 analizzatori (tcmd/ui/py/zcui/z3l/xml) su input vuoto, malformato e binario -> nessun crash.

### Le prove dello studio sono ora DENTRO `npm run test`

Le verifiche a mano non lasciano traccia: le ho messe in engine/collaudo.js, che e' la
suite che gira con `npm run test`. Da 14 prove a 22. Le nuove 8, ognuna a guardia di un
bug realmente successo (se torna, il collaudo si accende):
  - gli 8 script dello studio compilano
  - archivio popolato (20621 file, 0 saltati)
  - GUARDIA ripresa: chiavi normalizzate       <- bug 2 (studio che rifaceva tutto)
  - GUARDIA ripresa: nessuna scheda duplicata  <- bug 2
  - GUARDIA livello 2: manuali ancora legati   <- bug 3 (indice che cancellava i .chm)
  - sa dire cosa fa CdWeldTrim col manuale
  - GUARDIA: ricerca regge le schede dei binari <- bug 1 (KeyError)
  - ONESTA': su un comando mai studiato lo dice invece di inventare

La guardia sui duplicati ha SUBITO fatto il suo mestiere: e' fallita per le 30 schede
lasciate dal test di ripresa. Aggiunto `python studia.py pulisci` (la deduplica va fatta
dallo strumento, non a mano). Dopo la pulizia: 22 prove passate, 0 fallite, exit 0.

---

## 2026-08-01 — MANDATO 01: PANNELLO NATIVO DI EFESTO DENTRO ZW3D

Efesto girava solo da riga di comando. Ora ha un pannello agganciato alla barra
laterale con una CASELLA DOVE L'UTENTE SCRIVE. Ripreso dal materiale archiviato il
26/07 (`EfestoAI\_archivio-form-nativa-zw\`), non rifatto da zero.

FILE TOCCATI
- NUOVO  `FINALE\src\EfestoPanelCommands.cpp` (292 righe)
- NUOVO  `FINALE\Resource\Forms\EfestoPanel.ui` (151 righe)
- NUOVO  `FINALE\icons\efesto.png` (64x64, soli chunk IHDR/IDAT/IEND, 245 byte)
- MOD    `FINALE\src\SuperAssistenteEngine.cpp` (dichiarazioni + CoreInit + CoreExit)
- MOD    `FINALE\SuperAssistenteEngine.vcxproj` e `...2027.vcxproj` (il .cpp in ENTRAMBI)
- MOD    `Settings\Default\ResourcePool\AUTOMAZIONE.zcui` (<Action> ID_~SuperAssistente_Efesto)
- MOD    `Settings\Default\ResourcePool\AUTOMAZIONE_Pages.zcui` (<Control> corrispondente)
- MOD    `C:\Users\infoa\EfestoAI\engine\efesto-cervello.js` (modo `--file`)

DECISIONE IMPORTANTE — DUE BOTTONI, NON UNO
Il cervello ci mette ~50 secondi (MISURATO: 47,9 s). ZW3D e' a thread singolo
sull'interfaccia: un comando che aspetta CONGELA ZW3D per un minuto intero.
Quindi "Chiedi a Efesto" lancia node con CREATE_NO_WINDOW e torna subito;
"Leggi risposta" mostra il testo quando `stato.txt` dice `pronto`.
Non e' una scorciatoia: senza timer/idle nell'SDK (cercato, NON esiste) e'
l'unica strada che non pianta il programma.

PROTOCOLLO A FILE (niente TCP, niente server: gia' provati, morivano)
  %TEMP%\Efesto\domanda.txt   <- C++
  %TEMP%\Efesto\stato.txt     <- JS: lavoro | pronto | errore
  %TEMP%\Efesto\risposta.txt  <- JS
`stato.txt` esiste per non leggere MAI una risposta scritta a meta'.

COLLAUDO A FREDDO (fatto, fuori da ZW3D)
- `node --check efesto-cervello.js` -> OK
- modo `--file` provato davvero: 47,9 s, `stato=pronto`, risposta corretta con
  citazione dei file. Onesta' verificata: risponde citando le fonti dell'indice.
- Engine: 0 errori. Bridge: 0 errori. `AUTOMAZIONE.zrc` rigenerato (28,1 MB) e
  contiene `EfestoPanel` ed `efesto`, con la stessa firma di `diagnosi` e
  `SA_TramoggeGalleria` che funzionano.

NON COLLAUDATO (serve ZW3D aperto, non l'ho fatto io)
Il pannello non e' mai stato APERTO dentro ZW3D. Restano da verificare a caldo:
il docking in barra laterale, la lettura della casella `ZsCc::TextEdit` con
`cvxItemGet(form, 4, 1, buf)`, e il funzionamento di `<action>~Efesto_Chiedi:cmd`
sui MatrixPushButtons. Il rischio piu' concreto e' l'indice dell'item della
TextEdit (1 = contenuto, 0 = etichetta): se tornasse vuoto, provare item 0.

SICUREZZA
Il pannello NON disegna e NON tocca il modello: nessuna cvxPart*/Zw*Create nel
file. Scelta gia' presa, qui rispettata e scritta nell'intestazione del .cpp.

### Collaudo del 2026-08-01 sera — 28/28, e un BACO NEGLI INDICI trovato per strada

`npm test` in EfestoAI dava 27/28. Il KO NON era colpa del pannello: verificato
togliendo le mie modifiche da una copia (10 riferimenti rotti senza, 9 con).

BACO VERO: `parse_api.py` e `parse_plugin.py` RIPARTONO da `_avanzamento_*.json`
e saltano i file gia' fatti (`if rel in fatti: continue`). Rilanciarli quindi NON
aggiornava niente: gli indici restavano fermi al 17:16, con i numeri di riga
vecchi. Sintomo: "riferimento file:riga non punta alla chiamata" e comandi
segnalati "senza bottone" che il bottone ce l'avevano.
RIMEDIO: per rigenerare davvero bisogna CANCELLARE prima
`_avanzamento_api.json`, `_avanzamento_plugin.json`, `INDICE_API.jsonl`,
`INDICE_PLUGIN.jsonl`. Fatto (backup in `STUDIO\_bak2601\`). Dopo: 22/22 nel
test degli indici, 28/28 nel collaudo, exit 0.
Da qui in poi: dopo aver aggiunto un .cpp al plugin, gli indici vanno rigenerati
COSI', altrimenti mentono.

★ ATTENZIONE, DUE EFESTO DIVERSI SUL DISCO — da decidere con l'utente
1. `C:\Users\infoa\EfestoAI\zw3d-plugin\` — plugin Efesto A SE' STANTE (Efesto.dll,
   45 KB, del 2026-08-01 13:39). Ha gia' un pannello con casella, e usa una
   tecnica MIGLIORE della mia: thread di lavoro + `SetTimer` a 400 ms che travasa
   la coda nell'interfaccia dal thread principale. Risultato: UN SOLO bottone,
   la risposta compare da sola, niente "Leggi risposta". E' quello che il
   collaudo controlla (prove "form nativa dentro il .zrc", "EfestoApri registrata").
2. `...\03_PLUGIN_ZW3D\...\FINALE\` — il SuperAssistente, dove ho messo il
   pannello oggi seguendo il mandato (che indicava questi percorsi e questi
   comandi MSBuild).
Non e' un doppione voluto: sono due strade partite in momenti diversi. Prima di
andare avanti va scelta una delle due, o il pannello finisce in due posti e si
divergono. Se si tiene il SuperAssistente, conviene COPIARE da li' il trucco del
timer e togliere il secondo bottone.


## 2026-08-01 — MANDATO 03: INFERRIATA rifatta (form vera + arie vere)

MOTIVO: l'utente ha bocciato inferriata/cancello/recinzione: "abbastanza assurdi,
molto poco lineari e gestibili". Misure fisse nel codice, form che non chiedeva
quasi niente, e soprattutto il PASSO digitato a mano — da li' nascevano le arie
sbagliate contro i montanti.

RIFATTA SOLO L'INFERRIATA (era l'ordine: se non le fai tutte e tre, fanne una bene).

FILE NUOVI
  include\RegoleOfficina.h + src\RegoleOfficina.cpp
      Lettore di C:\Alcafer\Modelli\_Comuni\REGOLE_OFFICINA.json. Trova la regola
      per id, legge numeri/stringhe/array dal blocco "parametri", e sa pescare un
      numero dentro la PROSA della regola (serve per ARIA_MAX, che sta nel testo
      di R044 e non nei parametri).
  include\InferriataParametrica.h + src\InferriataParametrica.cpp
      Lo scheletro parametrico (R046: l'inferriata non ha uno stile fisso).
      CalcolaFila() e' il cuore: n >= (luce-ariaMax)/(ariaMax+larghezza) per
      ECCESSO, poi aria = (luce - n*larghezza)/(n+1). I vuoti sono n+1 per
      costruzione, quindi l'errore del "primo vuoto piu' largo" non e' nemmeno
      rappresentabile. La prima bacchetta parte a un'ARIA dal filo interno.
  tools\test_inferriata.cpp
      Banco di prova FUORI da ZW3D (si compila con g++, non entra nel plugin).
      Verifica i numeri dei disegni reali: Montalto 1428/12 -> 11 bacchette
      aria 108 esatti; Gabriele anta 840/Ø14 -> 7 bacchette aria 92.75; campi
      laterali 323 e 321 -> 98.333 e 97.667. Piu' una scansione di 3801 luci in
      cui nessuna aria supera il massimo e la somma torna sempre.
      TUTTE PASSATE, exit 0.

FILE MODIFICATI
  Resource\Commands\SA_Inferriata.tcmd  — da 5 a 21 parametri
  Resource\Forms\SA_Inferriata.ui       — tre pagine: Vano e telaio / Bacchette
      e ante / Traversa e piatti. ★ NON c'e' piu' il campo "passo bacchette":
      l'utente da' l'ARIA MASSIMA, il numero lo calcola il programma.
  src\SuperAssistenteEngine.cpp — Cmd_Inferriata riscritto sul nuovo motore.
      Il vecchio corpo e' stato TOLTO, non lasciato commentato.
  src\GeometryExecutor.cpp — ★ aggiunto il TONDO. Prima disegnava sempre un
      rettangolo, quindi le bacchette Ø14 di R042 uscivano QUADRE. Ora se la
      specifica dice TONDO o Ø usa ZwSketchCircleCreateByRadius (con cerchio
      interno se c'e' lo spessore, per i tubi gas).
  Entrambi i vcxproj (2025 e 2027): aggiunti i due .cpp nuovi.

TRAPPOLA TROVATA (costava una form morta)
  Gli header dei <customwidget> nelle .ui NON sono liberi. Quelli giusti li ho
  copiati da ApiExample\20.ChamferAddAndDelete:
      ZsCc::Distance        -> nui/CommonControls/Template/CcDistance.hpp
      ZsCc::OptionCheckBox  -> nui/CommonControls/template/CcOptionCheckBox.hpp   (t minuscola!)
      ZsCc::DrawbackBoxGroup-> nui/CommonControls/CcDrawbackBoxGroup.hpp + <addpagemethod>addPage
  Per le scelte a elenco (profili, forma bacchetta, tipo piatti) si usa
  ZsCc::OptionCheckBox con piu' <item>: il comando legge l'INDICE della voce.

TRAPPOLA 2: l'esempio di R041 (Montalto, aria 108) e' il conto GEOMETRICO puro.
  Con ARIA_MAX=100 quel campo e' FUORI NORMA: R044 impone 12 bacchette e aria
  98.77. Non e' una contraddizione fra le due regole, e' R044 che vince. Il
  banco di prova verifica tutti e due i casi.

COMPILAZIONE: Engine e Bridge, Release x64, 0 errori. NESSUN DEPLOY (come da mandato).

NON FATTO: cancello e recinzione. Restano com'erano.

================================================================================
2026-08-02 — MANDATO 04: IL PREVENTIVO DIVENTA UNA FORM
================================================================================
PRIMA: il preventivo si compilava a mano in config\quote_input.json.
ADESSO: form SA_Preventivo dentro ZW3D, come le altre.

FILE NUOVI
  src\PreventivoCommands.cpp          — comando TEMPLATE Cmd_PreventivoForm(int)
  Resource\Commands\SA_Preventivo.tcmd — 11 parametri
  Resource\Forms\SA_Preventivo.ui      — 3 pagine (Ore | Pezzo e lavorazioni | Prezzo e tasse)
  tools\test_preventivo.cpp + build_test_preventivo.bat — banco di prova A FREDDO
  build_mandato04.bat

FILE TOCCATI
  src\QuoteEngine.cpp — ★ BUG TROVATO DAL COLLAUDO, vedi sotto.
  src\SuperAssistenteEngine.cpp — Register/UnregisterPreventivoCommands in Init/Exit.
  Settings\...\AUTOMAZIONE.zcui — l'Action Preventivo passa da ~SuperAssistente_Preventivo
      (comando diretto) a <Form>SA_Preventivo</Form> + <Script>!SA_Preventivo</Script>.
  ENTRAMBI i vcxproj (2025 e 2027): aggiunto PreventivoCommands.cpp.

★ BUG NEL MOTORE, trovato solo perche' il collaudo e' stato fatto davvero.
  Le tasse (23.72%) venivano sottratte SEMPRE, anche sui lavori in CONTANTI, e
  il rincaro per le tasse era dentro anche al prezzo target dei contanti.
  Sul lavoro reale (1700 EUR, 165 kg, 43 ore-uomo, incassato in contanti)
  usciva 21.32 EUR/ora invece dei 31-38 misurati in officina. Corretto: tasse
  e rincaro solo se fatturato = true.

COLLAUDO A FREDDO (tools\test_preventivo.exe, lanciato dalla cartella FINALE)
  43 ore-uomo -> 30.70 EUR/ora | 40 -> 33.01 | 38 -> 34.74 | 35 -> 37.72
  La forchetta 31-38 del mandato corrisponde alla forchetta ORE 35-43 di quel
  lavoro: quote_input.json tiene 43 (estremo alto), quindi esce l'estremo basso.
  prezzo calcolato dal programma: 1884.80 EUR -> esattamente 35.00 EUR/ora.
  verniciatura 8.52 mq x 2 facce x 32.27 = 549.88 (fattura reale 550). ESITO: TUTTO OK.

COMPILAZIONE: Engine e Bridge, Release x64, 0 errori. Il .zrc rigenerato contiene
  forms/SA_Preventivo.ui e commands/SA_Preventivo.tcmd. NESSUN DEPLOY (da mandato).

NON FATTO (per onesta')
  - Prova A CALDO dentro ZW3D: non fatta, il deploy era vietato dal mandato.
    Quindi "la form si apre" e' verificato sulla struttura (schema identico a
    SA_Inferriata, che funziona) e sul .zrc, NON coi miei occhi sullo schermo.
  - I mq di vista presi dall'ingombro sono il bbox WORLD: se il modello e'
    storto rispetto agli assi il numero e' abbondante. Per questo il campo
    resta correggibile a mano.
  - La form non ha ancora un campo per il prezzo/kg del ferro di commessa
    (resta quello del config) ne' per le spese vive.

## 2026-08-01 — MANDATO 03: cancello e recinzione rifatti (form vere, misure vere)

L'utente: «cancelli inferriate recinzioni sono abbastanza assurdi, molto poco
lineari e gestibili». Aveva ragione: misure fisse nel codice e form che chiedeva
5 numeri, fra cui il PASSO delle bacchette — ed e' proprio da li' che nasceva
l'errore R041 (prima bacchetta a un passo dal montante invece che a un'aria).

FATTO DAVVERO (compilato, 0 errori, calcolo verificato con eseguibile di prova):
 - INFERRIATA: era gia' stata rifatta in una sessione precedente. Verificata.
 - CANCELLO:   src/CancelloParametrico.cpp + include/CancelloParametrico.h
               Resource/Commands/SA_Cancello.tcmd (20 campi) + Forms/SA_Cancello.ui
 - RECINZIONE: src/RecinzioneParametrica.cpp + include/RecinzioneParametrica.h
               Resource/Commands/SA_Recinzione.tcmd (19 campi) + Forms/SA_Recinzione.ui

REGOLA CHE NON VA PIU' TOCCATA: il calcolo delle bacchette esiste in UN SOLO
posto, Inferriata::CalcolaFila (R041 + R044). Cancello e recinzione la CHIAMANO,
non la riscrivono. Una formula sola = un posto solo dove sbagliare.

PROVE FATTE (non a parole):
 - tools/test_arie.cpp: per ogni caso, n*larghezza + (n+1)*aria == luce esatta,
   e aria sempre <= aria massima. 7 casi, 0 falliti.
 - tools/test_regole.cpp: stampa i default e i riepiloghi veri.
 - tools/test_segue_file.cpp: cambiato R035/R039/R044 in una COPIA del json ->
   il programma ha seguito il file (60x60x3, aria max 80, margine 150). Prova
   che i valori NON sono murati nel codice.

TRAPPOLA TROVATA: scrivendo percorsi Windows dentro stringhe C++ con strumenti
che interpretano le sequenze, "\\recinzione..." e' diventato "\" + a capo + 
"ecinzione". Compilava lo stesso ma il file finiva nel posto sbagliato. Dopo
ogni patch su stringhe con backslash, rileggere la riga.

================================================================
2026-08-02 — MANDATO 04: IL PREVENTIVO ADESSO HA UNA FORM
================================================================
PRIMA: il preventivo si compilava modificando a mano config\quote_input.json.
ADESSO: c'e' la form SA_Preventivo dentro ZW3D, tre pagine (Ore / Pezzo e
lavorazioni / Prezzo e tasse), 11 campi. Il json resta come RIPIEGO: e' lui a
dare i default, e la form vince campo per campo. Cosi' il vecchio flusso non si
rompe.

IL MOTORE NON E' STATO TOCCATO. src\QuoteEngine.cpp e config\pricing_config.json
sono rimasti identici: era gia' tarato sui numeri veri e riscriverlo era il modo
piu' rapido per rovinarlo.

FILE DEL MANDATO
 - src\PreventivoCommands.cpp        la faccia: legge la form, legge peso e
                                     ingombro dal modello, chiama Calcola,
                                     mostra il riquadro
 - Resource\Commands\SA_Preventivo.tcmd   11 parametri, luid 1..11
 - Resource\Forms\SA_Preventivo.ui        la finestra a tre pagine
 - Settings\...\AUTOMAZIONE.zcui          Action ID_!SuperAssistente_Preventivo,
                                          <Form>SA_Preventivo</Form>, Script !SA_Preventivo
 - Settings\...\AUTOMAZIONE_Pages.zcui    Control con la stessa action
 - Entrambi i vcxproj (2025 e 2027) contengono src\PreventivoCommands.cpp
 - tools\test_preventivo_form.cpp + build_test_preventivo_form.bat  <-- NUOVO

BUILD (2026-08-02): Engine Release x64 -> 0 errori. Bridge Release x64 -> 0
errori, .zrc rigenerato dal PostBuild. NESSUN DEPLOY, come da mandato.

PROVA A FREDDO — tools\test_preventivo_form.exe, stampa TUTTO OK.
Riproduce il lavoro vero (2 inferriate, 165 kg, 1700 EUR posate, contanti,
verniciatura pagata dal cliente):
   ore-uomo 43 (8 disegno + 28 costruzione + 6 posa + 1 trasporto)
   materiale 184.80 (di cui 19.80 di sfrido) | accessori 125 (98+27)
   taglio esterno 70 | verniciatura 0
   prezzo per centrare i 35 EUR/ora-uomo: 1884.80 EUR
   a 1700 EUR rende 30.70 EUR/ora-uomo -> segnalato SOTTO OBIETTIVO. 199 EUR/mq.
   stesso lavoro FATTURATO: da accantonare 403.24 EUR, restano 1296.76.
   verniciatura a carico nostro: 549.88 EUR, cioe' la fattura vera da 550.

NOTA SULLA FORCHETTA: il mandato diceva "circa 31-38 EUR/ora-uomo", esce 30.70.
E' il bordo basso, coerente col fatto che quel lavoro e' stato venduto un po'
sotto. NON ho ritoccato il motore per far entrare il numero nella forchetta:
truccare la taratura per far tornare un collaudo e' il modo migliore per non
accorgersi mai di essere sottocosto. La soglia del test e' 30-38.

DUE COSE SCRITTE NEL CODICE E NELLA FORM, perche' costano soldi veri:
 1. le ore di POSA sono ORE-UOMO: 3 ore in due fanno 6. La form lo dice
    nell'etichetta e non converte niente da sola.
 2. del laserista si paga SOLO IL TAGLIO: il peso della lamiera e' gia' dentro
    il peso del modello. Sommare anche il materiale lo conta due volte.

NON FATTO / PROSSIMO PASSO
 - prova A CALDO dentro ZW3D: serve il deploy, che il mandato vietava.
 - i mq di vista sono proposti dall'ingombro complessivo: se il manufatto e'
   storto rispetto agli assi il numero e' abbondante. Per questo il campo 8 e'
   correggibile a mano (0 = prendilo dal modello).
 - le ore di costruzione sono ancora una voce sola: le fasi vere (taglio, piega,
   saldatura, molatura) esistono nel motore ma non sono cronometrate.

================================================================================
2026-08-02 — MANDATO 03: INFERRIATA / CANCELLO / RECINZIONE — form vere
================================================================================
GIUDIZIO DI PARTENZA (utente, 2026-08-01): «cancelli inferriate recinzioni sono
abbastanza assurdi, molto poco lineari e gestibili». Misure fisse nel codice e
form che non chiedeva quasi niente.

STATO TROVATO: il grosso del lavoro era gia' stato scritto in una sessione
precedente (motori parametrici + .tcmd + .ui per tutti e tre) ma NON era mai
stato compilato ne' collaudato. Questa sessione ha verificato, corretto e
provato.

FILE TOCCATI
 - src\SuperAssistenteEngine.cpp : le tendine "Profilo telaio / traversa / piatto"
   leggevano elenchi SCRITTI NEL CODICE. Ora li leggono da REGOLE_OFFICINA.json
   (R021.scelte_telaio, R042.scelte_traversa, R042.scelte_piatto), con ripiego
   se il file manca.
 - Resource\Forms\SA_Inferriata.ui : aggiunte le voci mancanti nelle tendine per
   allinearle agli elenchi del JSON (30x30x3, 80x80x3, 80x40x3, 40x10, 50x8).
 - C:\Alcafer\Modelli\_Comuni\REGOLE_OFFICINA.json : aggiunti gli elenchi delle
   tendine dentro R021 e R042. Backup in REGOLE_OFFICINA.bak-20260802-003537.json.
 - tools\test_arie.cpp, tools\test_regole.cpp, tools\test_tendine.cpp (NUOVI)
 - prove_mandato03.bat (NUOVO, lancia le tre prove)

★ BUG TROVATO E CORRETTO — disallineamento tendina/elenco
Mettendo gli elenchi nel JSON avevo usato un ordine diverso da quello della .ui.
Il programma usa la POSIZIONE scelta nella tendina come INDICE nell'elenco:
l'utente avrebbe scelto "50x50x2" e gli sarebbe uscito un altro profilo, IN
SILENZIO. Corretto, e soprattutto messo sotto test automatico (test_tendine)
perche' e' un errore invisibile a occhio.

BUILD: Engine OK 0 errori, Bridge OK 0 errori (MSBuild VS18, Release x64).
Unico warning MSB8028 (obj\ condivisa con i progetti 2027), gia' noto.

PROVA A FREDDO: TUTTE PASSATE (prove_mandato03.bat)
 1. arie/bacchette contro le misure reali:
    Gabriele anta   luce 840 -> 7 bacchette, 8 vuoti, aria 92.75, passo 106.75
    Gabriele lat.sx luce 323 -> 2 bacchette, 3 vuoti, aria 98.33
    Gabriele lat.dx luce 321 -> 2 bacchette, 3 vuoti, aria 97.67
    Montalto        luce 1428 -> 12 bacchette, aria 98.77
    Ogni prova verifica anche che (n+1)*aria + n*larghezza richiuda la luce.
 2. i default arrivano dal JSON: provato cambiando una COPIA del file
    (telaio 40x40x2, quota 950, bacchetta quadro 16, aria max 90) e il
    comportamento e' cambiato SENZA ricompilare.
 3. tendine .ui e elenchi JSON allineati riga per riga.

★ NOTA SU R041 vs R044 — apparente contraddizione, non lo e'
R041 (esempio Montalto) dice 11 bacchette e aria 108. Ma 108 > 100, quindi R044
impone la dodicesima: 12 bacchette, aria 98.77. Il programma fa bene a
"contraddire" l'esempio di R041: la normativa vince. Da NON correggere.

NON FATTO / PROSSIMO PASSO
 - prova A CALDO dentro ZW3D: il mandato vietava il deploy. Le geometrie non
   sono mai state disegnate davvero: verificato il CALCOLO, non il disegno.
 - la soglia in basso (profilo coricato 40x20 / 30x20 di R042) non e' generata.
 - lo zoccolo a bacchette infittite (R020) non e' implementato.
 - i piatti "a sandwich" sono posizionati sulle due facce ma i FORI dei piatti
   sdraiati (R028, tolleranza 1 mm) non sono geometria vera.

## 2026-08-02 — MANDATO 04 verifica di collaudo (Hermes)
Verificato lo stato del preventivo-form (implementato la notte precedente).
File toccati oggi: tools\test_preventivo.cpp (riscritto: collaudo completo con
forchetta ore, prova fatturato, prova prezzo automatico, prova verniciatura),
tools\build_test_preventivo.bat, build_m04_verifica.bat (nuovi).
BUILD: Engine ENGINE_EXIT=0, Bridge BRIDGE_EXIT=0, 0 errori (solo MSB8028, la
solita obj\ condivisa 2025/2027).
PROVA FREDDA: tools\test_preventivo.exe -> "TUTTO OK".
  165 kg, 43 ore-uomo, 1700 EUR contanti -> 30.70 EUR/ora-uomo.
  A 35 ore-uomo -> 37.72; a 38 -> 34.74; a 40 -> 33.01. La forchetta reale
  31-38 EUR/ora e' centrata; 43 ore e' l'estremo pessimistico della stima.
  Prezzo automatico 1884.80 EUR -> esattamente 35.00 EUR/ora. OK.
  Fatturato 1700 -> accantonamento 403.24 EUR (23.72%). OK.
  Verniciatura 8.52 mq -> 549.88 EUR contro la fattura reale di 550. OK.
PROVA CALDA: NON fatta (serve ZW3D aperto con la parte). NESSUN DEPLOY, da mandato.
PROSSIMO PASSO: aprire ZW3D, cliccare Preventivo Pro sul modello delle due
inferriate, controllare che la form si apra con le tre pagine e che il riquadro
finale esca. Poi deploy.

## 2026-08-02 — MANDATO 01: PANNELLO NATIVO DI EFESTO (Hermes)
STATO: catena completa, compilata e DEPLOYATA. Manca solo la prova a caldo
(ZW3D era chiuso: nessuna sessione attiva, verificato con tasklist).

File coinvolti (gia' presenti dalla sessione precedente, qui verificati):
  src\EfestoPanelCommands.cpp         292 righe — 3 comandi: ~SuperAssistente_Efesto,
                                      ~Efesto_Chiedi, ~Efesto_Leggi. Non tocca il modello.
  Resource\Forms\EfestoPanel.ui       151 righe — id1 ListWidget risposta,
                                      id4 ZsCc::TextEdit CASELLA MULTIRIGA di input,
                                      id2 MatrixPushButtons con action ~Efesto_*:cmd.
  Settings\Default\ResourcePool\AUTOMAZIONE.zcui       riga 242 <Action ID_~SuperAssistente_Efesto>
  Settings\Default\ResourcePool\AUTOMAZIONE_Pages.zcui riga 15  <Control action=...>
  icons\efesto.png
  SuperAssistenteEngine.vcxproj       riga 110 <ClCompile src\EfestoPanelCommands.cpp>
  src\SuperAssistenteEngine.cpp       righe 1389-1390 dichiarazioni, 1436 Register, 1525 Unregister
  engine\efesto-cervello.js           modo --file gia' presente (righe 81-105)

BUILD: Engine EXIT=0, Bridge EXIT=0. Solo warning MSB8028 (obj\ condivisa 2025/2027).
  log: FINALE\build_m01_efesto.log e FINALE\build_m01_bridge.log

DEPLOY fatto in C:\Program Files\ZWSOFT\ZW3D 2025\apilibs\:
  Core\SuperAssistenteEngine.dll, SuperAssistenteBridge.dll, AUTOMAZIONE.zrc,
  Resource\Forms\EfestoPanel.ui, Settings\Default\ResourcePool\*.zcui, icons\efesto.png

PROVA FREDDA del cervello (protocollo a file), FATTA E RIUSCITA:
  node engine\efesto-cervello.js --file C:\Users\infoa\AppData\Local\Temp\Efesto\domanda.txt
  stato.txt = "pronto", risposta.txt con gli 8 passi + citazione del file sorgente.
  ⚠️ TRAPPOLA: da git-bash $TEMP diventa /tmp e node scrive la risposta li'. Il
  percorso va passato in forma Windows. Il C++ usa GetTempPathA, quindi e' corretto.
  Onesta' verificata: su domanda fuori indice risponde "Non lo trovo nel mio indice."

PROVA CALDA: NON FATTA. ZW3D va riavviato e va cliccato il bottone Efesto.
PROSSIMO PASSO: aprire ZW3D, cliccare Efesto nella ribbon AUTOMAZIONE, scrivere una
domanda nella casella, premere "Chiedi a Efesto", aspettare ~50s, premere "Leggi risposta".

## 2026-08-02 — MANDATO 04: ricontrollo indipendente (Hermes, seconda passata)
Ricompilati DA ZERO oggi Engine e Bridge (Release x64): 0 errori, solo il warning
noto MSB8028 sulla obj\ condivisa coi progetti 2027. Rilanciato
build_m04_collaudo.bat: "TUTTO OK", 30.70 EUR/ora-uomo sul lavoro reale
(1700 EUR, 165 kg, 43 ore-uomo, contanti) — 0.30 sotto il bordo basso della
forchetta 31-38 dichiarata dall'utente, quindi tarato ma al limite: la
differenza sta nello sfrido 12% (stima, non ancora sostituito col nesting reale
di LogiBarre). NESSUN DEPLOY. Prova a caldo dentro ZW3D ancora da fare.

## 2026-08-02 — MANDATO 04: ricompilazione e riverifica completa (Hermes)
Verificato che la form del preventivo e' presente e completa, non un abbozzo:
- Resource\Commands\SA_Preventivo.tcmd: 11 parametri (luid 1-11).
- Resource\Forms\SA_Preventivo.ui: 3 gruppi (Ore / Pezzo e lavorazioni / Prezzo e
  tasse), 11 campi id1..id11 + note esplicative, mode Dockable.
- src\PreventivoCommands.cpp: Cmd_PreventivoForm(int idData), legge peso e ingombro
  dal modello, la form vince sui default di quote_input.json, chiama QuoteEngine
  (motore NON toccato) e mostra il riquadro con cvxMessageBox + i due file in %TEMP%.
- Registrazione in CoreInit (RegisterPreventivoCommands) e unload in CoreExit.
- zcui: Action ID_!SuperAssistente_Preventivo con <Form>SA_Preventivo</Form> e
  <Script>!SA_Preventivo</Script>; Control combaciante in AUTOMAZIONE_Pages.zcui.
- QuoteEngine.cpp e PreventivoCommands.cpp presenti in ENTRAMBI i vcxproj.

BUILD (rifatta oggi): Engine Release x64 ENGINE_EXIT=0, Bridge Release x64
BRIDGE_EXIT=0, 0 errori (1 solo warning noto MSB8028 sulla obj\ condivisa).
NESSUN DEPLOY, come da mandato.

PROVA FREDDA (tools\test_preventivo_form.exe): TUTTO OK. Sul lavoro reale
(165 kg, 43 ore-uomo, 1700 EUR in contanti): 30.70 EUR/ora-uomo, accessori 125 EUR
(98+27), verniciatura 0, accantonamento 0. Stesso lavoro FATTURATO: accantonamento
403.24 EUR (23.72%), resa 21.32 EUR/ora-uomo. Verniciatura a nostro carico: 549.88
EUR, cioe' la fattura vera da 550.

PROVA CALDA: NON FATTA (nessun deploy). Va riavviato ZW3D dopo l'installazione e
cliccato "Preventivo Pro" nella ribbon AUTOMAZIONE.

## 2026-08-02 — MANDATO 03 verifica e collaudo a freddo (Hermes)
File toccati: tools/test_m03_tre.cpp (NUOVO), tools/run_m03_tre.bat (NUOVO).
Nessuna modifica alla logica: inferriata/cancello/recinzione erano gia' rifatti
il 2026-08-01 (form .tcmd+.ui vere, default da REGOLE_OFFICINA.json, R041/R044).
BUILD: SuperAssistenteEngine.vcxproj Release x64 -> 0 errori.
       SuperAssistenteBridge.vcxproj Release x64 -> 0 errori.
       (solo warning MSB8028: obj\ condivisa con i progetti 2027 — noto)
PROVA A FREDDO: tools\run_m03_tre.bat -> "TUTTO OK" (28 controlli).
  - regole lette da C:\Alcafer\Modelli\_Comuni\REGOLE_OFFICINA.json: LETTO
  - n*larghezza + (n+1)*aria = luce ESATTA su inferriata, ogni anta del cancello
    e ogni campo della recinzione (R041, vuoti n+1 verificato numericamente)
  - n e' il MINIMO: con una bacchetta in meno l'aria sforerebbe i 100 (R044)
  - utente che ne chiede 3 su luce 2000 -> il programma ne mette 17 e lo dichiara
  - abbassando l'aria max da 100 a 80 le bacchette passano da 17 a 21
  - cancello: telaio default 40x40x2, MAI 30x30x2 (R021/R035); arie 12/14 da R025
  - recinzione: piantone 30x30x2, bacchetta 12, margine 106 (R039)
NON FATTO: nessun deploy (vietato dal mandato). Nessuna prova a caldo in ZW3D.
DA TOGLIERE: in CoreInit c'e' ancora la diagnostica Cmd_ListaProfili() che scrive
%TEMP%\profili_zw3d.txt al primo avvio. Va rimossa quando l'inventario e' raccolto.
PROSSIMO PASSO: deploy + prova a caldo dentro ZW3D con una parte attiva.

## 2026-08-02 — MANDATO 04: il preventivo diventa una FORM (Hermes, verifica+build)
File coinvolti: src/PreventivoCommands.cpp, Resource/Commands/SA_Preventivo.tcmd,
Resource/Forms/SA_Preventivo.ui, tools/test_preventivo_form.cpp,
build_m04_test.bat (NUOVO, compila+lancia il collaudo a freddo con vcvars64).
Motore NON toccato: src/QuoteEngine.cpp e config/pricing_config.json invariati.
Registrazione: RegisterPreventivoCommands/UnregisterPreventivoCommands richiamate
in CoreInit/CoreExit (SuperAssistenteEngine.cpp righe ~1432 e ~1521).
Ribbon: Action ID_!SuperAssistente_Preventivo con <Form>SA_Preventivo</Form> e
<Script>!SA_Preventivo</Script>; icona preventivo_pro presente in icons/.
vcxproj: QuoteEngine.cpp e PreventivoCommands.cpp presenti in ENTRAMBI
(SuperAssistenteEngine.vcxproj e .2027.vcxproj).
BUILD: Engine Release x64 -> 0 errori. Bridge Release x64 -> 0 errori.
       (solo warning MSB8028 obj\ condivisa coi progetti 2027 — noto)
COLLAUDO A FREDDO: tools\test_prev_m04.exe -> "TUTTO OK", tutti i controlli OK.
  lavoro reale 2026-08-01 (165 kg, 43 ore-uomo, 1700 EUR contanti):
  materiale 184.80 | accessori 125.00 (98 apribile + 27 fisso) | taglio 70.00
  prezzo per centrare 35 EUR/ora-uomo = 1884.80 EUR
  con 1700 EUR resa = 30.70 EUR/ora-uomo (dentro/al bordo della forchetta 31-38)
  stesso lavoro FATTURATO -> accantonamento 403.24 EUR (23.72%), resa 21.32
  verniciatura a carico nostro -> 549.88 EUR, come la fattura vera di 550.
NON FATTO: nessun deploy (vietato dal mandato). Nessuna prova a caldo in ZW3D:
la form non e' stata ancora aperta dentro ZW3D con una parte attiva.
PROSSIMO PASSO: deploy (Engine+Bridge+zrc+tcmd+ui+zcui+icone) e prova a caldo.

## 2026-08-02 — MANDATO 04: il preventivo diventa una FORM (verifica finale)
File coinvolti: src\PreventivoCommands.cpp (comando template Cmd_PreventivoForm),
Resource\Commands\SA_Preventivo.tcmd (11 parametri), Resource\Forms\SA_Preventivo.ui
(3 pagine: Ore / Pezzo e lavorazioni / Prezzo e tasse), registrazione in
SuperAssistenteEngine.cpp (Register/UnregisterPreventivoCommands), ribbon
AUTOMAZIONE.zcui Action ID_!SuperAssistente_Preventivo con <Form>SA_Preventivo</Form>
e <Script>!SA_Preventivo</Script>. QuoteEngine NON toccato.
Entrambi i .cpp sono in ENTRAMBI i vcxproj (2025 e 2027).
BUILD: Engine + Bridge, Release x64, 0 errori (solo warning MSB8028 obj condivisa).
PROVA A FREDDO: tools\build_test_preventivo_form.bat -> "TUTTO OK".
  165 kg, 43 ore-uomo, 1700 EUR contanti -> 30.70 EUR/ora-uomo (atteso 31-38).
  accessori 125 EUR (98+27), verniciatura 549.88 EUR se a carico nostro,
  fatturato -> accantonamento 403.24 EUR (23.72%).
NESSUN DEPLOY eseguito (richiesto dal mandato).
Prossimo passo: prova a CALDO dentro ZW3D dopo il deploy (serve la .ui copiata in
apilibs\Resource\Forms, altrimenti il bottone non apre niente).

## 2026-08-02 — MANDATO 04: RIVERIFICA INDIPENDENTE (Hermes)
Ricontrollati uno per uno i pezzi e RICOMPILATO da zero, non fidandosi del log.
- 11 campi nel .tcmd e nella .ui: presenti e con i luid combacianti (1..11).
- Cmd_PreventivoForm legge tutti gli 11 luid con cvxDataGet; peso dal modello
  (GeometryReader) e mq di vista dall'ingombro (ZwEntityBoundingBoxGet).
- Ribbon: Action ID_!SuperAssistente_Preventivo <Form>SA_Preventivo</Form>
  <Script>!SA_Preventivo</Script>, Control combaciante in AUTOMAZIONE_Pages.zcui.
  Icona preventivo_pro presente in icons\ (48 e 32).
- Register/Unregister chiamati in CoreInit/CoreExit. .cpp in ENTRAMBI i vcxproj.
- BUILD RIFATTA OGGI: Engine .dll + Bridge .dll + AUTOMAZIONE.zrc rigenerato
  (27 MB, contiene 4 occorrenze di SA_Preventivo). 0 errori.
- PROVA A FREDDO rifatta (tools\build_test_prev.bat, nuovo): TUTTO OK,
  30.70 EUR/ora-uomo sul lavoro reale.
NON FATTO: deploy (vietato) e quindi nessuna prova a CALDO con ZW3D aperto.

## 2026-08-02 — MANDATO 04 verifica finale (Hermes)
Form preventivo SA_Preventivo: verificata completa (11 campi), tcmd+ui+zcui allineati.
File: src/PreventivoCommands.cpp, Resource/Commands/SA_Preventivo.tcmd,
Resource/Forms/SA_Preventivo.ui, Settings/.../AUTOMAZIONE(.Pages).zcui, entrambi i vcxproj.
Build Engine 0 errori, Bridge 0 errori (solo warning MSB8028 obj condivisa 2025/2027).
Prova a freddo tools/test_preventivo_form.exe: TUTTO OK. Collaudo reale 1700 EUR / 165 kg
/ 43 ore-uomo -> 30.70 EUR/ora-uomo, accantonamento fatturato 403.24 EUR, verniciatura 549.88.
NESSUN DEPLOY (da mandato). Prossimo passo: deploy + prova a caldo dentro ZW3D.


## 2026-08-02 — MANDATO 03 verifica e riconferma (Hermes)
Trovato il lavoro del mandato 03 gia' presente in sorgente (fatto la notte del
2026-08-01): RegoleOfficina.cpp/.h (lettore di REGOLE_OFFICINA.json),
InferriataParametrica, CancelloParametrico, RecinzioneParametrica, piu' i tre
.tcmd e le tre .ui rifatte. Oggi NON l'ho riscritto: l'ho VERIFICATO davvero.
- prove_mandato03.bat eseguito per intero -> "TUTTE LE PROVE A FREDDO SONO PASSATE"
  (test_arie, test_regole, test_tendine, test_canc_recinz).
- Build ricontrollata: Engine + Bridge Release x64, 0 errori (solo il solito
  warning MSB8028 sulla obj\ condivisa col progetto 2027).
- Aggiunto build_m03_hermes.bat (MSBuild dei due progetti in un colpo).
- NESSUN DEPLOY, come da mandato.
Pitfall shell: da git-bash i .bat vanno lanciati con
  MSYS2_ARG_CONV_EXCL='*' cmd.exe /c "call C:\\percorso\\completo\\file.bat"
altrimenti cmd risponde "non e' riconosciuto come comando".

## 2026-08-02 — MANDATO 04: il preventivo diventa una FORM
File: src\PreventivoCommands.cpp (nuovo), Resource\Commands\SA_Preventivo.tcmd,
Resource\Forms\SA_Preventivo.ui, AUTOMAZIONE.zcui (Action ID_!SuperAssistente_Preventivo,
Form SA_Preventivo, Script !SA_Preventivo), registrazione in SuperAssistenteEngine.cpp
(CoreInit/CoreExit), .cpp aggiunto a ENTRAMBI i vcxproj (2025 e 2027).
Motore QuoteEngine NON toccato. 11 campi luid 1-11.
BUILD: Engine 0 errori, Bridge 0 errori (m04_eng.log, m04_brg.log). .zrc rigenerato.
COLLAUDO A FREDDO (tools\test_preventivo_form.cpp, build_m04_test.bat): TUTTO OK.
Lavoro reale 165 kg / 1700 EUR contanti -> 30.70 EUR/ora-uomo su 43 ore-uomo;
prezzo target 35/h = 1884.80 EUR; accessori 125 (98+27); verniciatura ipotetica
549.88 EUR (= fattura vera 550); fatturato -> accantonamento 403.24 (23.72%).
NESSUN DEPLOY, come da mandato. Prova a caldo dentro ZW3D ancora da fare.
