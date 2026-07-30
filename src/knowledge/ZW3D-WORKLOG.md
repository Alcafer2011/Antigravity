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
  C:\Users\infoa\src\knowledge\api\ (prima li aveva solo Efesto: l'agente di Antigravity non
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
        output in ...\SuperAssistentePlugin_FINALE (3)\FINALE\bin2027\x64\Release\
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
