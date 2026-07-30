# ZW3D 2025 — FUNZIONI NATIVE REALI (API + comandi bottone) — mappa per l'agente

> **Salvato: 2026-07-26 01:09 — Firma: Hermes (agente Nous Research), per conto dell'utente infoa/Alcafer2011.**
> **Cosa contiene:** l'inventario COMPLETO e VERIFICATO delle funzioni native di ZW3D 2025
> ricavato scandagliando l'installazione reale in `C:\Program Files\ZWSOFT\ZW3D 2025\`:
> ogni bottone/comando dell'interfaccia (cosa fa + con che comando parte + quale dialogo apre)
> e ogni funzione dell'SDK C++ (firma vera + header + riga + flag @deprecated).
> **Perché:** dare a QUALSIASI modello che usa questo agente le fonti di verità pronte, così
> NON inventa funzioni (=crash di ZW3D, §1 di zw3d-rules.md) e sa quale bottone/API usare.
> **Regola d'uso:** questo file è l'INDICE ragionato; i dati grezzi (tutte le righe) sono nei
> due TSV affiancati — apri quelli con lo strumento `search`/read per la firma ESATTA:
>  - `zw3d-comandi-nativi.tsv`  = 3591 comandi bottone (comando | label | dialogo | hint | descrizione)
>  - `zw3d-api-index-locale.tsv` = 2868 funzioni SDK (funzione | header | riga | deprecated | firma VERA)

---

## 0. NUMERI (fotografia reale dell'installazione, 2026-07-26)
- **3591 comandi/azioni bottone** definiti in `Settings\ResourcePool\Actions.zcui` (1.1 MB).
  Ognuno ha: nome comando (`!CdXxx`/`~Xxx`/`$Xxx`), label Ribbon, dialogo (`Form`), icona, hint, descrizione, script.
- **1042 comandi `!Cd*` unici** referenziati nelle pagine ribbon (`Settings\ResourcePool\*.zcui`).
- **2869 funzioni SDK C++ uniche** (`Zw*`/`cvx*`/`Vx*`) nei 237 header `api\inc\zwapi_*.h`.
  - **840 `Zw*` (moderne, PREFERITE)** + **2028 `cvx*` (legacy, molte @deprecated)** + 1 `Vx*`.
  - Solo 8 marcate `@deprecated` *sulla riga della firma*; ma l'indice esterno `ZW3D-INDEX 1\API-FUNZIONI-*.md`
    (~5385 voci con doc) marca molte più `cvx*` come deprecate → **preferisci sempre `Zw*`**.
- **458 file `.tcmd`** (definizioni dialogo/parametri comando) negli esempi API + risorse.

## 1. COME È FATTO UN COMANDO/BOTTONE (la catena reale)
Cliccare un bottone in ZW3D scatena questa catena, tutta su file di TESTO leggibili:
1. **`RibbonPages.zcui`** (o `ToolBars.zcui`, `PopupMenus.zcui`): la pagina/gruppo del ribbon elenca
   `<Control action="ID_!CdXxx" .../>` = QUALE bottone sta dove.
2. **`Actions.zcui`**: per ogni `ID_!CdXxx` c'è `<Action name="ID_!CdXxx" type="button">` con:
   - `<Form>CdXxx</Form>` = il dialogo che si apre (definito in un `.tcmd` omonimo)
   - `<Ribbon>Etichetta</Ribbon>` = il testo sul bottone (es. "Structural Member")
   - `<Hint>...</Hint>` / `<Desc>...</Desc>` = tooltip e descrizione operativa
   - `<Script>!CdXxx</Script>` = il comando effettivo eseguito
3. **`.tcmd`** (XML): definisce i PARAMETRI del dialogo (`<parameter>` con tipo entity/distance/point…),
   la `function` C++ interna e le opzioni di picking. Es. reale `ExTrudewithPreview.tcmd`:
   parametri `Profile P` (entity), `start/end distance`, `Direction` (point) → è la "forma" del comando.
> Quindi per sapere "cosa fa un bottone e con che comando parte": cerca la label in `zw3d-comandi-nativi.tsv`,
> leggi `comando` (lo `!Cd…`) e `form_dialogo` (il `.tcmd` con i campi). Per pilotarlo via macro vedi §4.

## 2. LE FAMIGLIE DI COMANDI (prefisso `!Cd…` → dominio) — le più grosse
Cv=74 (curve/wireframe), Tbl=71 (tabelle), Cns=64 (vincoli assieme), Part=53 (parte/feature),
Mtl=49 (materiali/rendering), Ftr=42 (feature), Lyr=36 (layer), Cfg=36 (configurazioni/famiglie),
Smd=35 (LAMIERA), Root=32 (file/root), View=32, Pnt=30 (punti), Reuse=29 (libreria riutilizzo),
Dwg=25 (disegno), Eqn=25 (equazioni/variabili = PARAMETRICO), Md=24 (stampi), Inq=22 (interrogazioni),
Prf=20 (schizzo/profilo), Block=19, Sym=18 (simboli), Sf=16 (superfici), Drawing=14.
> `Reuse*` (29 comandi) + `Cfg*` (36, famiglie/tabelle configurazioni) + `Eqn*` (25, equazioni) sono la
> strada NATIVA per il parametrico e le librerie — utile per il target "parametrico associativo" (§6bis rules).

## 3. CARPENTERIA / WELDMENT — comandi bottone REALI (verificati in Actions.zcui)
| Comando | Bottone | Cosa fa |
|---|---|---|
| `!CdWeldStruct` | Structural Member | membro strutturale (profilato su percorso) — dialogo `CdWeldStruct` |
| `!CdWeldStrctCrt` | **Profile Swept Rod** | **crea aste col profilo scelto lungo curve selezionate** (variante utile!) |
| `!CdWeldTrim` | Trim | taglia/estende i membri tra loro (interruzioni) |
| `!CdWeldEndCap` | End Cap | tappi di chiusura (solo profili cavi chiudibili, §5 rules) |
| `!CdWeldGusset` | Gusset | fazzoletti d'angolo |
| `!CdWeldBeads` | Weld Bead | cordoni di saldatura |
| `!CdProfNew` / `!CdShtProf` / `!CdCosProfNew` | Sketch/Cosmetic | nuovo schizzo/profilo |
| `!CdSymWeldCrt`/`!CdPMISymWeldCrt` | Weld | simbolo di saldatura (annotazione) |
| `!CdWeldTblCrt` | Weld Table | tabella saldature dal disegno |
| `!Wd…` (`WdFilletWeld`,`WdGrooveWeld`,`WdSpotWeld`,`WdPlugWeldMulti`) | saldature ECAD/PMI |
| `~CmFrame…`/`~CmFramesPop…` | gestione FRAME (telai/strutture nel browser) |

## 4. ⚠️ WELDMENT via SDK: NON ESISTE — si pilota a MACRO (confermato di nuovo 2026-07-26)
Ho ricontrollato TUTTI i 237 header: **nessuna funzione SDK crea membri weldment.**
Le uniche funzioni con "Weld" sono per il DISEGNO/annotazione:
`ZwDrawingSymbolWeldCreate/DataGet/DataSet/Free/Init`, `cvxDwgSymWeld*`, `cvxSymWeldFree` — SIMBOLI, non geometria.
E `cvxPartShapeStructGet` è solo un GET di struttura, non crea nulla.
→ **Conferma la regola §5 di zw3d-rules.md:** il weldment (`!CdWeldStruct`/`!CdWeldStrctCrt`) si RIGIOCA come
sequenza di statement con **`ZwCommandMacroExecute(ZW_MACRO_STATEMENTS, input, &out)`** (`zwapi_command.h`),
liberando l'output con `ZwMemoryFree`. Vedi l'helper corretto e la sequenza `CdWeldStruct` in rules §5.

## 5. API SDK per CAPACITÀ (mappa capacità→funzioni, poi conferma la FIRMA nel TSV/lookup)
- **Schizzo (46 fn `ZwSketch*`)**: `ZwSketchCreateByMatrix` (crea E attiva lo schizzo), `ZwSketchArcCreateByThreePoints`,
  `ZwSketchCircleCreateByRadius`, `ZwSketchConstraintSolve`, `ZwSketchActivate`/`ZwSketchCancel`.
  ⚠️ Si ESCE dallo schizzo SOLO con `cvxRootExit()` (rules §1.2).
- **Feature 3D (47 fn `ZwFeature*`)**: `ZwFeatureExtrudeCreate`(+`Init`), `ZwFeatureLoftCreate`(+`DataInit`),
  `ZwFeatureBoxCreateByCenter`, `ZwFeatureAddShapeCreate`, boolean `ZwFeatureCombine*`.
  ⚠️ NON usare `cvxPartExtrude/Loft/Sweep/Revolve` (header `zwapi_cmd_shape.h`, 142 fn legacy): 3 crash reali (rules §1.1).
- **Lamiera (70 fn `zwapi_cmd_sheetmetal.h` + 63 `cvxPartSmd*`)**: `cvxPartSmdExtrudeFlange`, `cvxPartSmdExtrudeTab`,
  `cvxPartSmdBendTaper`, `cvxPartSmdChangeBend`, attributi `cvxPartSmdAtGet/Set`. Bottoni `!CdSmd*` (35).
- **Assieme (164 fn `ZwComponent*` + 69 `cvxComp*`)**: `ZwComponentActivate`, `ZwComponentFileSet`,
  `ZwComponentConfigGet/Set`, `ZwComponentFolderCreate`.
- **Variabili/PARAMETRICO (13 fn `ZwVariable*` + `Eqn*` bottoni)**: `ZwVariableCreate`, `ZwVariableListGet/Set`,
  `ZwVariableTextRefresh`, `ZwCommandVariableLoad/Unload`. + `ZwDbObjSetEquation`, `ZwEntityAutoRegen` (dai rules).
  → questa è la via per il "parametrico associativo" richiesto dall'utente (rules §6bis).
- **Import/Export (5+4 fn)**: `cvxFileImport`(+`Init`,`Multi`,`Stl`), `cvxFileExport`(+`Init`,`Multi`) — carica i DXF libreria.
- **Disegno/quote (136 fn `ZwDrawing*`)**: `ZwDrawingDimensionAutoCreate`, `ZwDrawingAutoBalloonCreate`,
  `ZwDrawingCrossHatchCreate`, viste in `zwapi_drawing_view.h` (63) + `zwapi_dwg_view.h` (41).
- **Comandi/plugin (`zwapi_command.h`)**: `ZwCommandFunctionLoad/Unload`, `ZwCommandMacroExecute`,
  `ZwCommandReact<...>`. ⚠️ In CoreExit fai SEMPRE `ZwCommandFunctionUnload` per ogni comando (rules §1.4).
- **Interrogazione geom.**: `ZwEntityBoundingBoxGet` (bbox), massa `ZwPhysicalAttributeGet`, `Inq*` (22 bottoni).

## 6. HEADER PIÙ RICCHI (dove cercare per dominio)
zwapi_cmd_shape.h(142, legacy-forma ⚠️), zwapi_general_ent.h(131), zwapi_cmd_wireframe.h(96), zwapi_entity.h(89),
zwapi_file.h(83), zwapi_cmd_dwg_dimension.h(81), zwapi_ui_form.h(75), zwapi_cmd_sheetmetal.h(70),
zwapi_asm_comp.h(69), zwapi_cmd_sk_cmds.h(67), zwapi_global_apply.h(65), zwapi_cmd_assembly.h(64),
zwapi_drawing_view.h(63), zwapi_cmd_freeform.h(61), zwapi_root.h(55), zwapi_cmd_paramdefine_param.h(53).

## 7. FONTI SUL DISCO (dove ho preso questi dati — verificabili)
- Comandi/bottoni: `C:\Program Files\ZWSOFT\ZW3D 2025\Settings\ResourcePool\Actions.zcui` (+ `RibbonPages.zcui`, `ToolBars.zcui`, `PopupMenus.zcui`).
- API header: `C:\Program Files\ZWSOFT\ZW3D 2025\api\inc\*.h` (237 file).
- Esempi C++: `...\api\ApiExample\` (con i `.tcmd` reali).
- Indice API documentato (esterno): `C:\Users\infoa\OneDrive\Desktop\ZW3D-INDEX 1\API-FUNZIONI-01.md` / `-02.md`.
- Estratti generati da me (in questa cartella): `zw3d-comandi-nativi.tsv`, `zw3d-api-index-locale.tsv`.

## 8. COME USARE QUESTO MATERIALE (per l'agente / modello a bordo)
1. L'utente chiede "il bottone X cosa fa / come lo faccio via codice?" → cerca in `zw3d-comandi-nativi.tsv`
   (per label o per comando). Trovi comando `!Cd…`, dialogo `.tcmd`, descrizione.
2. Vuoi scrivere codice C++ → trova la FIRMA ESATTA con `zw3d op:lookup <nome>` o in `zw3d-api-index-locale.tsv`.
   Se non c'è NELL'INDICE, NON esiste: non inventarla (rules §1).
3. Feature-forma → usa `Zw*` moderne (§5), MAI `cvxPart*` legacy. SEH + RequirePart obbligatori (rules §1).
4. Weldment → non c'è API: macro `ZwCommandMacroExecute` che rigioca `!CdWeldStruct`/`!CdWeldStrctCrt` (§4 + rules §5).
5. Parametrico → `ZwVariable*` + `Eqn*`/`Cfg*`/`Reuse*` nativi (§5).
6. Compila (`op:build`) e prova (`op:remote`/`op:open`) PRIMA di dire "fatto" (rules §2).
