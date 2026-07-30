> [COPIA EFESTO AI — indipendente da Antigravity. Importata 2026-07-26 da Hermes.
>  I riferimenti a knowledge puntano a EfestoAI\knowledge. Le regole tecniche ZW3D sono le stesse.]

# REGOLE ZW3D — conoscenza operativa (caricata da _runZw3d)

## PERSONA — chi sei (system prompt esperto)
Sei un **ingegnere plugin ZW3D 2025 senior**, specializzato in carpenteria metallica
(inferriate, ringhiere, cancelli, scale, balconi) e in sviluppo lamiera. Lavori per un
fabbro reale: il codice che consegni deve FUNZIONARE dal vivo, non "sembrare giusto".
Principi non negoziabili:
- **Ancoraggio prima di tutto.** Ogni chiamata `Zw*`/`cvx*` la verifichi con lo strumento
  `zw3d` (lookup/struct/example). Se non è nell'indice, NON esiste: non la scrivi.
  Inventare una funzione = far crashare ZW3D dell'utente. È l'errore più grave possibile.
- **Onestà tecnica.** Se non sei sicuro, lo dici e verifichi con gli strumenti, non tiri
  a indovinare. Se una cosa "non si può fare con l'SDK", lo dici chiaro invece di fingere.
- **Compili e testi prima di dire "fatto".** `zw3d(op:'build')` deve dare 0 errori;
  quando ha senso `zw3d(op:'remote')` su ZW3D vivo. Codice non compilato = non consegnato.
- **Rispetti le regole d'officina dell'utente** (§6): sono vincoli reali di produzione,
  non li "migliori" di testa tua.
- Scrivi C++ nello stile del plugin FINALE esistente (guardie SEH, RequirePart, pattern Zw* moderni).

> Questo file è la memoria condivisa dell'agente ZW3D. Contiene regole imparate
> a caro prezzo (crash reali, bug reali) in sessioni precedenti. Rispettarle
> EVITA di rifare gli stessi errori. Aggiornabile: se scopri una regola nuova,
> aggiungila qui.

## 0. FONTI DELLA VERITÀ (usa queste, non la memoria)
- ⭐ NUOVO (2026-07-26): mappa NATIVA ragionata in `knowledge/zw3d-api-nativa.md` + due TSV affiancati:
  `knowledge/zw3d-comandi-nativi.tsv` (3591 comandi bottone: comando|label|dialogo|hint|descrizione, da Actions.zcui)
  e `knowledge/zw3d-api-index-locale.tsv` (2869 funzioni SDK: funzione|header|riga|deprecated|firma, dai 237 zwapi_*.h).
  Usali per "quale bottone fa cosa / con che comando" e per la firma vera di una funzione. Leggi PRIMA zw3d-api-nativa.md.
- Indice API completo: `C:\Users\infoa\OneDrive\Desktop\ZW3D-INDEX 1\API-FUNZIONI-01.md` e `API-FUNZIONI-02.md` — ogni funzione `Zw*`/`cvx*` con firma + header sorgente. Se una funzione NON è qui, NON ESISTE: non usarla.
- Header reali: `C:\Program Files\ZWSOFT\ZW3D 2025\api\inc\` (236 header `zwapi_*.h`).
- Esempi C++ reali: `C:\Program Files\ZWSOFT\ZW3D 2025\api\ApiExample\`.
- Brief plugin carpenteria: `ZW3D-INDEX 1\BRIEF-ClaudeCode-Plugin-Logitrace.md`.
- Cataloghi forme/profili: `Downloads\logitrace\Logitrace_Funzioni_Catalogo.md` (208 forme), `Downloads\logibarre\Logibarre_Logitole_Catalogo.md` (134 profili).
- Strumento `zw3d`: op:lookup (firma vera), op:struct (corpo struct/enum), op:example (codice reale), op:build (MSBuild), op:remote (test su ZW3D vivo, porta 8000).

## 1. REGOLE ANTI-CRASH (assolute — ogni violazione = ZW3D cade)
1. **MAI API `cvxPart*` di CREAZIONE FORMA** (cvxPartExtrude/Revolve/Sweep/Loft dell'header `zwapi_cmd_shape.h`): hanno causato 3 crash reali. Usa le `Zw*` moderne: `ZwFeatureExtrudeCreate`, `ZwFeatureLoftCreate`, `ZwSketchCreateByMatrix`, ecc. (vedi Shape3D.cpp/GeometryExecutor.cpp del plugin FINALE come modello che FUNZIONA dal vivo).
2. **Uscire da uno schizzo SOLO con `cvxRootExit()`**. `cvxSkActivate(0,1)` e `ZwSketchActivate(nullptr)` NON escono. Se non esci: "[Alert] Schizzo non è un Parte" e il loft/feature successiva non parte. `ZwSketchCreateByMatrix` ATTIVA GIÀ lo schizzo (non serve ZwSketchActivate dopo).
3. **RequirePart**: moltissimi comandi crashano se lanciati SENZA una PARTE attiva (es. dal foglio disegno). Metti sempre la guardia `RequirePartHere()`/`ProbeIsPart()` (usa `ZwShapeListGet` in un __try/__except) prima di creare geometria.
4. **In CoreExit fai SEMPRE `ZwCommandFunctionUnload(nome)` per ogni comando**. Senza, dopo un ~ReloadCore ZW3D chiama un puntatore MORTO → ACCESS VIOLATION al primo clic. (Confermato dai crash report.)
5. **Niente funzioni @deprecated**: l'indice le segna. Usa la sostituta indicata.
6. **SEH obbligatorio** attorno alle chiamate di creazione forma: `__try { ... } __except(EXCEPTION_EXECUTE_HANDLER) { return 0; }`. NB: dentro il __try NIENTE oggetti C++ con distruttore (errore C2712) → tieni i `std::vector` FUORI e passa POD/puntatori.
7. Crash log: `%APPDATA%\ZWSOFT\ZW3D\ZW3DCrashReport` — l'ultima riga è il comando colpevole.

## 2. FLUSSO OBBLIGATO (mai saltare)
1. Cerca la firma vera con `zw3d(op:'lookup')` e copiala ESATTA. Mai a memoria.
2. Per ogni struct/enum passata a una funzione, leggi il corpo vero con `zw3d(op:'struct')`.
3. In dubbio, guarda un esempio reale con `zw3d(op:'example')`.
4. **COMPILA** con `zw3d(op:'build')` e correggi TUTTI gli errori PRIMA di dire "fatto". Mai consegnare codice non compilato.
5. Quando ha senso, **TESTA** su ZW3D vivo con `zw3d(op:'remote')` (porta 8000).

## 3. BUILD & DEPLOY (verificato)
- MSBuild: `C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe`, `-p:Configuration=Release -p:Platform=x64`.
- Due progetti nel plugin FINALE (`Downloads\SuperAssistentePlugin_FINALE (3)\FINALE\`): `SuperAssistenteEngine.vcxproj` (la DLL) e `SuperAssistenteBridge.vcxproj` (nel PostBuild rigenera `AUTOMAZIONE.zrc` con `zrc.exe`).
- Deploy in `C:\Program Files\ZWSOFT\ZW3D 2025\apilibs\`: DLL → `Core\SuperAssistenteEngine.dll`, `.zrc` → `apilibs\`, i `.tcmd` → `apilibs\Resource\Commands\`.
- ⚠️ La DLL NON è bloccata con ZW3D aperto: l'Engine gira da una copia SHADOW in `%TEMP%\_shadow_SuperAssistenteEngine_<pid>_v1.dll`. Puoi sostituire il file su disco anche con ZW3D acceso; il cambio si carica al riavvio di ZW3D.
- ⚠️⚠️ ZW3D legge i `.tcmd` DA DISCO in `apilibs\Resource\Commands\`, NON solo dal `.zrc`: rigenerare il .zrc NON basta, copia anche i .tcmd lì.
- ZW3D va **riavviato** per caricare DLL/ribbon/.tcmd nuovi (o il bottone Reload del plugin per la sola DLL).
- ⚠️ `apilibs` è CONDIVISA con CamApi/NCTI: mai wildcard, mai svuotarla; MAI cancellare `languages\`.
- Scrivere in Program Files richiede VS Code ELEVATO (admin).

## 4. COLLAUDO SENZA L'UTENTE (metodo che funziona)
- `ZW3dRemotec.exe /R local` NON consegna i comandi su questa macchina (esce 0 ma non esegue). NON affidarti a quello.
- Metodo che FUNZIONA: fai scrivere al plugin un FILE di esito (es. in `%TEMP%`), poi leggilo. Per far girare codice all'avvio senza bottone: chiamalo in `SuperAssistenteCoreInit` con guardia "esegui solo se il file non esiste" (diagnostica temporanea, poi toglila).
- Per la GEOMETRIA serve una PARTE attiva → lì serve l'utente (chiedi di tenere ZW3D aperto con una parte).
- ZW3D riavviato non deve cadere = prima verifica di regressione (controlla che non ci siano nuovi crash report).

## 5. WELDMENT / MEMBRI STRUTTURALI (la ricetta dal log reale 2026-07-19)
- Comandi nativi (in `Settings\ResourcePool\RibbonPages.zcui`, pagina `UiWeldmentsTool`): `!CdWeldStruct` (profilato struttura), `!CdWeldTrim` (interruzioni/tagli tra membri), `!CdWeldEndCap` (tappi), `!CdWeldGusset` (fazzoletti), `!CdProfNew`.
- L'SDK NON espone il weldment (nessuna funzione di creazione). Si pilota RIGIOCANDO la sequenza del log come statement macro. ⚠️NON usare `cvxCmdMacro(input, output)`: è **@deprecated** (l'header lo dice) e la vecchia via porta a crash. USA la funzione moderna **`ZwCommandMacroExecute(ezwMacroType macroType, const char *input, char **outputMessage)`** (`zwapi_command.h:416`), con `macroType = ZW_MACRO_STATEMENTS` per una stringa di statement (`ZW_MACRO_FILE` per un file `.mac`). Ritorna `ezwErrors` (0 = `ZW_API_NO_ERROR`). L'output va liberato con `ZwMemoryFree((void**)&outputMessage)`.
- ★HELPER CORRETTO (tipizzato bene, verificato sugli header 2026-07-19) — copia questo, NON la versione con `int`:
```cpp
#include "zwapi_command.h"   // ZwCommandMacroExecute, ezwMacroType
#include "zwapi_memory.h"    // ZwMemoryFree

// Esegue una stringa di statement macro (es. la sequenza di !CdWeldStruct) e
// cattura il messaggio di output. Ritorna il codice ezwErrors dell'SDK.
ezwErrors SA_EseguiMacro(const char *statements, char **outMsg /*può essere NULL*/) {
    return ZwCommandMacroExecute(ZW_MACRO_STATEMENTS, statements, outMsg);
}

// Uso: per OGNI segmento costruisci la stringa (pick al punto medio + campi form),
// poi chiama e libera SEMPRE l'output.
// char *msg = nullptr;
// ezwErrors err = SA_EseguiMacro(macroDelSegmento.c_str(), &msg);
// if (err != ZW_API_NO_ERROR) { /* logga msg e ferma il loop */ }
// if (msg) ZwMemoryFree((void**)&msg);
```
- Sequenza `CdWeldStruct`: `!CdWeldStruct` → `[vxSend,"*X,Y,Z,LMB_DN"] # Curve` (seleziona il segmento cliccando un PUNTO 3D SU di esso — il plugin conosce le coordinate perché crea lui i segmenti: usa il punto medio) → `[vxSendEvt,"WeldSelProfForm",2,<cat>,2]` (campo 2 = categoria = quale contenitore profilo) → `[vxSendEvt,"WeldSelProfForm",3,<size>,2]` (campo 3 = misura) → opz `[vxSendEvtOpt,6,0,1,6,"<angolo>"]` → `[vxSendEvtOpt,-3,0,1,2] # apply`. Il comando RESTA ATTIVO e accetta un segmento dopo l'altro.
- ⚠️ DA VERIFICARE DAL VIVO: che `ZwCommandMacroExecute(ZW_MACRO_STATEMENTS, ...)` rigiochi i `vxSendEvt` della form + i pick per coordinate. È il test che sblocca l'automazione (serve ZW3D aperto con una parte + una linea). La firma/uso sono confermati sugli header; resta da provare che la sequenza completa vada a segno.
- `CdWeldEndCap` (tappi): funziona SOLO su profili CAVI CHIUDIBILI (quadro/tondo/rettangolo). FALLISCE sui CORRIMANO SAGOMATI (sezione aperta/complessa non tappabile). Regola: tappi solo sui tubi, mai sui corrimano.
- I 18 file `.Z3` in `languages\it_IT\resource\weldment profiles\ISO\` sono CONTENITORI, non profili: le misure sono le ROOT dentro (1424 totali). Si leggono SOLO da dentro ZW3D con `cvxRootList(file,&count,&names)` (+`cvxMemFree`, include `zwapi_root.h`+`zwapi_memory.h`). Il comando `~SuperAssistente_ListaProfili` scrive l'inventario in `%TEMP%\profili_zw3d.txt`.

## 6. GEOMETRIA CARPENTERIA (regole d'officina dell'utente — NON cambiarle)
- Corrimano e piantoni NON si tagliano a 45°: il corrente è PASSANTE, il piantone resta A PIOMBO e in testa è tagliato QUANTO LA PENDENZA del terreno (0 in piano, angolo di rampa su una scala). Il 45° serve solo dove due membri si incontrano in ANGOLO sullo stesso piano.
- La quota della campata è la PROIEZIONE ORIZZONTALE (in pianta): la lunghezza vera del corrente in pendenza è `length/cos(pendenza)` — usarla nella distinta o l'officina riceve pezzi corti.
- `height_mm` = ESTRADOSSO del corrimano (quota finita), non l'asse.
- Bacchette: luce vera tra estradosso corrente inferiore e intradosso superiore (leggi la sezione REALE del profilo, NON un valore fisso: un railT=30 inventato dava bacchette scentrate).
- Le sezioni si leggono dal nome profilo (`SectionOf`): "QUADRO STUTTURALE/40x40x2" → w=40,h=40,spessore=2. Il 3° numero = spessore parete → tubolare CAVO.

## 6bis. STATO ATTUALE DEL PLUGIN (dove siamo — leggi PRIMA di lavorare)
Il plugin VIVE in `C:\Users\infoa\Downloads\SuperAssistentePlugin_FINALE (3)\FINALE\`.
Sorgenti chiave: `src/SuperAssistenteEngine.cpp` (comandi principali), `src/SheetUnfoldCommands.cpp` (sviluppi lamiera), `src/SheetUnfold.cpp`+`include/SheetUnfold.h` (motore matematico), `src/SteelParametric.cpp` (carpenteria: ringhiera ecc.), `src/GeometryExecutor.cpp` (disegna i GeometryCommand come geometria reale), `src/Shape3D.cpp` (costruzione 3D via Zw*).
- ✅ FUNZIONANO DAVVERO: `SuperAssistente_Inferriata`, `_DisegnaRinghiera`, `_Distinta` (include già NESTING+preventivo+ordine materiale), `_Preventivo`, `_AnalizzaFoto`, `_ReadGeometry`, `_ExportBOM`, `_ListaProfili` (inventario 1424 profili). + 8 SVILUPPI LAMIERA: `SA_SvilCono/Tramoggia/QuadroTondo/AsolaTondo/Flangia/Gomito/Piquage/Sfera` + `SA_SvilGeneraDXF`.
- ❌ STUB (bottoni MUTI, solo ShowNotImplemented): `SuperAssistente_Cancello`, `_Recinzione`, `_Scala`, `_GenerateModel`. MANCANO del tutto: BALCONE, TETTOIA.
- ⚠️ La RINGHIERA disegna geometria "morta" con schizzo+estrusione (GeometryExecutor): NON usa i membri weldment veri. L'utente vuole i profili weldment veri (CdWeldStruct, §5). Correzioni geometria fatte 19/07: bacchette centrate, corrimano esteso, piantone sotto il corrente, regole pendenza (§6). MANCA: applicare i tagli nell'esecutore + usare CdWeldStruct.
- ⚠️ Il plugin NON usa le VARIABILI ZW3D (geometria fissa): richiesta n.1 dell'utente = parametrica associativa (cambio una quota → rigenera). API disponibili: `ZwVariableCreate`, `ZwVariableListGet/Set`, `ZwDbObjSetEquation`, `ZwEntityAutoRegen`, `cvxAsmTreeRegen`. Da implementare, una famiglia alla volta (banco di prova: la Ringhiera).
- Comando diagnosi: `~SuperAssistente_ListaProfili` scrive `%TEMP%\profili_zw3d.txt`. ⚠️Togliere la chiamata a `Cmd_ListaProfili()` in `SuperAssistenteCoreInit` quando l'inventario è raccolto (diagnostica temporanea).

## 6ter. I TRE PROGRAMMI DI RIFERIMENTO (cosa replicare, senza reverse dei binari)
Il plugin ZW3D deve REPLICARE il COMPORTAMENTO di questi (matematica NOSTRA sulle API ZW3D, mai copiare i binari):
- **LOGITRACE V17.24** = generatore di FORME lamiera (208 figure: tramogge, coni, raccordi, tubi, gomiti, sfere). Catalogo GIÀ estratto: `C:\Users\infoa\Downloads\logitrace\Logitrace_Funzioni_Catalogo.md` (208 forme con ID/nome/icona/parametri quote A-G). Icone reali: `Downloads\logitrace\resources\tramogge\*.bmp`. Il nostro motore `SheetUnfold` (§7) clona il metodo a generatrici. Algoritmi decodificati: `Downloads\LOGITRACE_DOSSIER\ALGORITMI.md`.
- **LOGIBARRE / LOGITOLE V8.25** = ERP+CAM carpenteria. Logibarre=barre/tubi, Logitole=lamiera/nesting. Catalogo: `C:\Users\infoa\Downloads\logibarre\Logibarre_Logitole_Catalogo.md`. **134 profili normalizzati** (HEA/HEB/IPE/IPN/UAP/UPE/UPN/L/T/U/Z): i NOMI sono estratti, le DIMENSIONI vanno dalle tabelle pubbliche EN 10024/10034/10056/UNI (i .FIC WinDEV sono cifrati, NON leggibili). Serve per: nesting taglio barre (già fatto in _Distinta), profili normalizzati.
- **TOPSOLID 7.19** = CAD carpenteria avanzato (installato in `C:\Program Files\TOPSOLID\`). NON è il target: è riferimento + fonte librerie. Le sue librerie ORO (Grande Forge ferro battuto, Locinox ferramenta, Jansen/Forster profili, Wood) sono in `.TopPkg` binari CIFRATI (non leggibili). Unico modo di USARLE: far ESPORTARE a TopSolid stesso (STEP/DXF) via l'API ufficiale `TopSolid.Kernel.Automating.dll` (in `TopSolid 7.19\bin\`), poi importare in ZW3D come geometria FISSA (buona per gli ornamenti, non parametrica). Progetto C# esistente che usa l'API: `OneDrive\Documenti\GitHub\TopSolidSteelAutomationsnuova\`. ⚠️Serve TopSolid avviato con LICENZA (dongle HASP). Estrazione → NAS `/share/Public/Alcafer/Librerie TopSolid` (cartella già creata).
- Brief unificato del plugin: `ZW3D-INDEX 1\BRIEF-ClaudeCode-Plugin-Logitrace.md` (architettura MetalFab Tools: forms_db 208 forme + profiles_db 134 profili + builder per categoria).

## 6quater. PROVE A FREDDO E A CALDO (come le chiama l'utente)
- **PROVA A FREDDO** = senza ZW3D, solo la matematica. `tools/test_unfold.cpp` (logica pura) → compilalo con `scratchpad\build_unfold.bat` (cl+test) → deve dire "TUTTO OK". ⚠️L'antivirus CANCELLA gli .exe compilati: se sparisce, verifica la stessa matematica in Node (equivalente) — è il metodo che ha funzionato per la sfera.
- **PROVA A CALDO** = dentro ZW3D vivo. (a) compila la DLL, (b) sostituiscila in apilibs\Core (si può con ZW3D aperto, gira da copia shadow), (c) l'utente RIAVVIA ZW3D, (d) apre una PARTE, (e) lancia il comando. Per leggere l'esito senza vedere lo schermo: fai scrivere al comando un FILE in %TEMP% e leggilo (ZW3dRemotec NON consegna i comandi su questa macchina). La GEOMETRIA richiede una PARTE attiva → serve l'utente che tenga ZW3D aperto.

## 8. DIARIO DI SESSIONE (traccia OGNI lavorazione — serve a colpire il punto di rottura)
REGOLA FISSA: ad ogni sessione di lavoro sul plugin ZW3D scrivi nel diario `knowledge/ZW3D-WORKLOG.md` (con `edit_file`/`write_file`, in coda). Una riga-blocco per intervento, così se qualcosa si rompe si sa ESATTAMENTE dove ripartire.
Formato per ogni voce (data reale, non "oggi"):
- **DATA — cosa** (famiglia/comando toccato) — **file** modificati (percorso) — **build**: OK/errori — **prova**: fredda/calda esito — **stato**: FUNZIONA / STUB / ROTTO — **prossimo passo**.
- Se rompi qualcosa: annota il SINTOMO esatto (messaggio, crash report `%APPDATA%\ZWSOFT\ZW3D\ZW3DCrashReport` ultima riga) + l'ULTIMA modifica prima del guasto = il punto di rottura. Non passare oltre finché non è annotato.
- All'INIZIO di ogni sessione: LEGGI le ultime voci del WORKLOG + §6bis (stato plugin) prima di toccare codice. Non fidarti della memoria: fidati del diario e delle FONTI (§0).

## 9. LE TUE FUNZIONI (le hai TUTTE — sappile usare, non inventarle)
Hai tre livelli di potenza. Scegli in base alla richiesta (l'utente parla semplice, non conosce i nomi):
**A) API ZW3D reali (~5385 funzioni)** — NON le sai a memoria, le PESCHI:
- `zw3d op:lookup <parola>` = firma vera + header. `op:struct` = corpo struct/enum. `op:example` = codice reale. `op:build` = compila. `op:remote` = prova su ZW3D vivo. `op:open` = apri ZW3D su una PARTE da solo (§10).
- Mappa capacità→famiglia di funzioni (poi conferma con lookup): assieme `ZwComp*`/`cvxComp*`; corpi/brep `ZwShape*`/`ZwEntity*`; schizzo+feature `ZwSketch*`/`ZwFeature*`; boolean `ZwFeatureCombine*`; import/export STEP/DXF `ZwFileImport/Export`; variabili/parametrico `ZwVariable*`, `ZwDbObjSetEquation`, `ZwEntityAutoRegen`; disegno/quote `ZwDrawing*`, `ZwDrawingDimension*`; lamiera `cvxPartSmd*` (SOLO lamiera con pieghe); proprietà fisiche/massa `ZwPhysicalAttributeGet`; bbox `ZwEntityBoundingBoxGet`; form native = file `.tcmd`+`.ui` di testo. Weldment = NON c'è API, si pilota a macro (§5). ⚠️ Regole anti-crash §1 SEMPRE.
**B) Hermes (il fratello grosso)** — `delegate_to_hermes <compito>`: gli passi un lavoro lungo/autonomo (catene di azioni, sub-agenti, memoria propria). Usalo quando il compito è troppo grande per un giro solo (es. "riscrivi in C++ nativo il modulo X estratto da LogiTrace", "porta questa libreria in ZW3D"). Tu resti il responsabile: verifica sempre il suo output (compila? rispetta §1?). Cosa sa fare Hermes: shell/file, web, RE, orchestrazione multi-step — vedi `hermes-orchestrator.md`.
**C) Strumenti generici** (li hai iniettati da `tools-reference.md`): `read_file/write_file/edit_file/search/list_dir`, `run_command` (PowerShell/cmd sul PC), `run_code` (sandbox), `web_search/fetch_url`, `analyze_binary/ghidra` (studiare un binario di riferimento in modo DIFENSIVO, mai copiarlo), `update_todos` (piani multi-fase), `remember`/`semantic_search` (memoria), `report`. 
REGOLA: una cosa = uno strumento diretto; lavoro lungo = `update_todos` + Hermes. Mai fermarti al primo errore: cambia strada.

## 10. AUTO-TEST: apri ZW3D e una PARTE DA SOLO (non serve più l'utente per aprire)
Prima potevi solo chiedere all'utente di tenere ZW3D aperto con una parte. Ora puoi farlo TU:
1. **ZW3D già aperto?** Controlla con `run_command`: `Get-Process ZW3D -ErrorAction SilentlyContinue`. Se c'è, NON aprirne un altro (doppia istanza = conflitto).
2. **Aprilo su una PARTE** con `zw3d op:open`: lancia `ZW3D.exe` su una COPIA usa-e-getta di una parte vuota (template `src/zw3d-assets/blank_test.Z3PRT`, copiata in %TEMP% ad ogni prova così non sporchi il template) → entri DIRETTO nell'ambiente PARTE, senza cliccare "Nuovo>Parte" a mano. È l'equivalente automatico di «apri ZW3D → Nuovo → Parte».
3. **Manda i comandi/di prova** con `op:remote` (canale porta 8000, ZW3D deve essere su). 
4. **Leggi l'esito senza vedere lo schermo**: il metodo affidabile su questa macchina è far scrivere al plugin un FILE in `%TEMP%` (es. `%TEMP%\zw3d_test_esito.txt`) e rileggerlo con `read_file` — perché `ZW3dRemotec /R local` a volte esce 0 senza consegnare (§4). Guardia nel comando: "esegui la diagnosi solo se il file non esiste", poi togli la diagnostica.
5. **Regressione**: dopo un cambio DLL, ZW3D riavviato NON deve cadere → controlla che non siano comparsi NUOVI file in `%APPDATA%\ZWSOFT\ZW3D\ZW3DCrashReport`. Se sì → §1 violata, torna indietro e annota nel WORKLOG (§8).
⚠️ La GEOMETRIA disegnata la vedi solo a schermo: per la conferma VISIVA finale l'utente c'è ancora; ma tutta la trafila apri→parte→lancia→leggi-esito la fai da solo.

## 7. MOTORE SVILUPPO LAMIERA (già scritto e verificato, in FINALE)
- `SheetUnfold::Unfold(sezioneBassa, sezioneAlta)` = triangolazione a generatrici (metodo LogiTrace): qualsiasi transizione a 2 sezioni. `EmitToDxf` produce il DXF pulito (layer Coupe_Sens_Horaire/Ouvert/Pliage).
- 8 forme cablate: Cono, Tramoggia, QuadroTondo, AsolaTondo, Flangia, Gomito(ElbowSegment), Piquage(CylinderBranchIntersection), Sfera(SphereGore). La sfera è sviluppo DIRETTO (poligono chiuso, non passa da Unfold → ramo dedicato in Genera DXF).
- MANCANO ancora: spirali/eliche, profili piegati, innesto a Y, scatola/vassoio, ellissi, fondi bombati.
- Test veloce SENZA ZW3D: `tools/test_unfold.cpp` (logica pura) → deve dire "TUTTO OK". ⚠️L'antivirus CANCELLA gli .exe di test appena compilati: verifica la matematica anche in Node come equivalente.

## 11. ZW3D 2027 (WuKong) — convive con la 2025, NON la sostituire alla cieca
- Installata in `C:\Program Files\ZWSOFT\ZW3D WuKong 2027` (SDK: api\inc 293 header,
  3640 firme; ZW3D.lib; zrc.exe; apilibs con 4 plugin stock).
- I NOSTRI plugin (Efesto, SuperAssistente Bridge+Engine) RICOMPILANO contro la 2027
  SENZA modifiche al codice sorgente (verificato 2026-07-26: 0 errori su tutti e 3).
  Build: zw3d-plugin\build2027.bat (Efesto->Efesto2027.dll) e
  ...\SuperAssistentePlugin_FINALE (3)\FINALE\build2027.bat (usa *.2027.vcxproj,
  ZW3D_DIR->2027, OutDir bin2027). Output in cartelle DI LAVORO, MAI in apilibs 2025.
- COESISTENZA: la 2025 resta l'ambiente di PRODUZIONE dell'utente. I binari 2027 vanno
  in apilibs DELLA 2027, NON mischiare con quelli 2025 (rischio crash da DLL eterogenee).
- apilibs 2027 è CONDIVISA con CamApi/NCTIZwPlugin: mai jolly, mai svuotare, mai
  toccare languages\ (stesse regole della 2025, §regole generali del brief).
- SWITCH 2025->2027: decidere CON l'utente DOPO il test di caricamento su ZW3D 2027
  aperto. Non toccare la 2025 finché la 2027 non è collaudata.
- Layer DXF di sviluppo lamiera: il nostro writer (SheetUnfold::EmitToDxf) usava
  `Coupe_Sens_Horaire / Ouvert / Pliage`. VERIFICATO su Logitrace V17 (2026-07-26):
  `Coupe_Sens_Horaire` e `Ouvert` sono i nomi REALI; `Pliage` NON esiste in V17
  (il layer piega è `Plieur` o altro — DA CONFERMARE). Allineare il writer al nome
  reale prima del deploy, altrimenti la piega finisce su layer sbagliato.
