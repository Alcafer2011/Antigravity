# FORM NATIVE ZW3D — pannelli agganciati, non finestre volanti

## 0. ★★★ AGGIORNAMENTO 2026-08-01: IL PANNELLO NATIVO SI PUO' FARE
Il §16 diceva "strada abbandonata" perche' i callback dei campi restavano muti.
La strada e' stata ripresa e il pannello nativo di Efesto COMPILA e si installa
(`EfestoAI\zw3d-plugin\`, vedi `EfestoAI\EFESTO-NUCLEO.md`). Cosa e' cambiato:
non ci si affida PIU' ai soli callback. Si mettono ENTRAMBE le strade insieme:
 (a) `ZwCommandCallbackLoad` + `cvxFormCallback` (§14), e
 (b) il RIPIEGO a polling gia' descritto in fondo al §16: il timer Win32 legge
     `cvxItemSelected` e deseleziona con `cvxItemSelect(form, campo, -1)`.
Con (b) presente, se (a) e' muto il pannello funziona lo stesso. Era questo il
pezzo che mancava per non abbandonare la strada.

★ TRAPPOLA NUOVA (costata una compilazione): `cvxItemAdd` prende **TRE**
argomenti — `void cvxItemAdd(char *Form, int idField, const char *Text)`
(zwapi_ui_form.h:922). Non ha il parametro `idItem` finale che verrebbe da
supporre per simmetria con `cvxItemSet`/`cvxItemDel`. Conferma la regola del
progetto: **le firme non si sanno a memoria, si PESCANO dall'indice.**

★ TRAPPOLA NUOVA 2: il `.zcui` chiamava `~Efesto_Apri` mentre la funzione
registrata era `EfestoApri`. Bottone che non fa niente, nessun errore visibile.
Da allora c'e' una prova automatica (`engine\collaudo.js`) che confronta il nome
nello `<Script>` con quello passato a `ZwCommandFunctionLoad`.

*(scoperto e verificato il 2026-07-26 costruendo il pannello di Efesto. Regola dell'utente:
ogni lavoro su ZW3D va scritto qui, perché l'agente lo ritrovi da solo la volta dopo.)*

## 1. IL DIFETTO DA NON RIFARE
Un pannello che **vaga per lo schermo** invece di stare agganciato dentro ZW3D non è un
problema di posizione: è la form dichiarata con il **`persistent`/`mode` sbagliato**.

```xml
<!-- SBAGLIATO: finestra libera, si stacca e vaga -->
<property name="persistent"><enum>ZsCc::Form::Temporary</enum></property>

<!-- GIUSTO: si aggancia dentro ZW3D -->
<property name="mode"><enum>ZsCc::Form::Dockable</enum></property>
<property name="persistent"><enum>ZsCc::Form::Persistent</enum></property>
```
`Dockable` è quello che usano sia le form dei comandi di serie sia il plugin
SuperAssistente (`apilibs\Resource\Forms\SA_Svil*.ui`). Modello da copiare: quelli.

## 2. PAGINA NELLA BARRA LATERALE (UI Manager)
Per far comparire la propria form fra Assembly/History, con icona ed etichetta:

```c
cvxFormCreate((char*)"NomeForm", 0);
svxFormInfo info;  memset(&info, 0, sizeof(info));
strcpy_s(info.Formname,  sizeof(info.Formname),  "NomeForm");
strcpy_s(info.Iconame,   sizeof(info.Iconame),   "miaicona");  // miaicona.png in apilibs\icons
strcpy_s(info.Labelname, sizeof(info.Labelname), "Etichetta");
strcpy_s(info.Tooltips,  sizeof(info.Tooltips),  "Descrizione");
cvxFormInsertTo(&info, 3, VX_UI_MANAGER);   // 3 = posizione nella barra
```
Firme vere (dall'indice locale, non a memoria):
- `ZW_API_C evxErrors cvxFormInsertTo(const svxFormInfo *FormInfo, int Index, evxFormAddTo AddTo);`
- `ZW_API_C void cvxFormAddTo(const char *Form, evxFormAddTo addTo);`
- `evxFormAddTo` = `{ VX_FILE_BROWSER, VX_UI_MANAGER }` (zwapi_ui_data.h:33)
- `svxFormInfo` = `{ vxLongName Formname; vxLongName Iconame; vxLongName Labelname; vxPath Tooltips; }`

## 3. INTERCETTARE I CLIC IN UNA FORM SEMPLICE
Sul CAMPO (non sulla form) si mette la proprietà `callback` col nome di una funzione C:

```xml
<widget class="ZsCc::ListWidget" name="id1">
  <property name="id" stdset="0"><number>1</number></property>
  <property name="callback" stdset="0"><string>MioCallback</string></property>
</widget>
```
```c
ZwCommandCallbackLoad("MioCallback", (zwFunctionPointer)MioCallback);
int MioCallback(char *form, int idField, int idItem);   // idItem = riga cliccata
```
Una `ZsCc::ListWidget` con righe cliccabili è il modo più semplice e **provato** di
avere dei "pulsanti" in una form non-template (lo fa `SA_TramoggeGalleria.ui`).

## 4. QUALI WIDGET SI POSSONO USARE
Dai 30 `.ui` dell'SDK: `QLabel`, `QWidget`, `QGroupBox`, `QDialogButtonBox` e i
`ZsCc::` — `Form, ListWidget, TableWidget, ComboBox, DrawbackBoxGroup, RealNumberEdit,
Number, String, Point, Distance, Entity, EntityList, EntityTable, Color, OptionCheckBox,
OptionComboBox, MatrixPushButtons, FormProxy`.
⚠️ I `ZsCc::` della sottocartella `Template/` (String, Number, Distance, Point, Entity…)
sono i controlli dei **template command**: vivono legati a un parametro del `.tcmd`.
Per un input di testo, quindi, si passa da un template command — non da una form libera.

## 5. INPUT DI TESTO = TEMPLATE COMMAND
```xml
<!-- commands\MioCmd.tcmd -->
<template name="MioCmd">
    <property name="function">MioCmd</property>
    <parameters>
        <parameter description="Domanda" luid="1" name="id1" type="string"/>
    </parameters>
</templates>
```
Lato C: `int MioCmd(int idData)` e si legge con
`ZW_API_C evxErrors cvxDataGetText(int idData, int idField, int NumBytes, char *Text);`
ZW3D disegna da sé la casella e i pulsanti OK/Applica/Annulla; con **Applica** il comando
resta aperto (come `CdWeldStruct`). Tipi disponibili nei 459 `.tcmd` installati:
option(1122), entity(792), distance(643), point(489), continue(413), form(328),
number(279), **string(196)**, command(119), angle(81), number_unit, custom_input, optgroup, dir.

## 6. ★ REGOLA DEI THREAD (vale per qualsiasi plugin che chiami la rete)
L'API ZW3D **non è thread-safe** e il thread della GUI non va bloccato. Schema corretto:
1. il thread di lavoro fa il lavoro lento (HTTP, file) e **non chiama MAI `Zw…`/`cvx…`**;
2. deposita i risultati in una coda protetta da `std::mutex`;
3. un timer Win32 — `SetTimer(NULL, 0, ms, proc)`, che l'event loop di ZW3D smista —
   svuota la coda **sul thread principale** e solo lì tocca l'API.
Non esiste un'API timer/idle in ZW3D (cercato: nessun `cvxTimer`/`cvxIdle`), quindi il
timer Win32 è la strada.

## 7. IMPACCHETTARE E INSTALLARE
- `zrc.exe "<cartella progetto>." -o Nome.zrc` raccoglie da solo `forms\`, `commands\`,
  i `.png` sciolti (li mette in `icons/`) e i `.zcui` (in `Settings/Default/`).
  Il `.zrc` va **accanto alla DLL** in `apilibs\` — è la convenzione di tutti i plugin.
- Icone: `<nome>.png` 48×48 e `<nome>_32.png` 32×32 (come le stock in `apilibs\icons`).
- In questa installazione funzionano ANCHE le copie sciolte: `apilibs\Resource\Forms\*.ui`
  e `apilibs\Commands\*.tcmd` (è la strada del SuperAssistente). Metterle in entrambi i
  posti costa nulla ed evita di dipendere da un solo meccanismo.
- `cvxPathApiLib("Nome", buf); cvxPathAdd(buf);` in Init fa trovare le risorse accanto alla DLL.
- ⚠️ `apilibs` è CONDIVISA (CamApi/NCTI/SuperAssistente): mai jolly, mai svuotare, mai
  toccare `languages\`. Cancellare solo file nominati uno per uno.

## 8. TRAPPOLE PRESE OGGI
- In un commento C++ la sequenza `Zw*/cvx*` **chiude il commento** (`*/`): scrivere
  `Zw… o cvx…`. Costa una compilazione persa.
- Un `.bat` con caratteri non-ASCII (box-drawing) fa fallire `cmd`. REM solo in ASCII.
- Compilare con `/utf-8` se i commenti/messaggi sono in italiano con accenti.
- Un `Commands\<Nome>_Apri.tcmd` lasciato lì da una versione precedente fa interpretare
  il comando come template command: rimuoverlo quando il comando diventa semplice.

## 9. ★★ TERZA CAUSA DI CRASH ZW3D: TOCCARE LA UI DENTRO `<Nome>Init`
*(crash reale del 2026-07-26, 11:07 — costato un avvio di ZW3D)*

**Sintomo:** ZW3D crasha **all'avvio**, appena carica i plugin. Rapporto in
`%APPDATA%\ZWSOFT\ZW3D\ZW3DCrashReport\BugReport\...UserInterface.dll_c0000005_....zip`.
Nel `TraceStack.txt`:

```
#1..#2  UserInterface.dll        <- dove esplode (access violation c0000005)
#3      ZW3D_Gui.dll
#4      ZW3D.dll
#5      apilibs\Efesto.dll       <- IL COLPEVOLE: il nostro plugin
#6..#11 ZW3D_CAD.dll             <- il caricatore dei plugin, in fase di avvio
#12..   ZW3D_ModuleEntry.dll, zw3d.exe
```
★ Regola di lettura: **il primo frame che nomina una DLL di `apilibs` è il colpevole**;
sopra di lui ci sono solo le funzioni ZW3D che ha chiamato lui.

**Causa:** quando ZW3D carica le DLL di `apilibs` e chiama `<Nome>Init`, la sua
**interfaccia non è ancora costruita**. Qualunque chiamata che scriva nella UI da lì
—`cvxFormCreate`, `cvxFormInsertTo`, `cvxFormShow`, `cvxItemAdd`, `cvxItemDel`— lavora su
strutture non inizializzate e fa access violation.

**REGOLA:** in `<Nome>Init` si REGISTRA soltanto:
`cvxPathApiLib`+`cvxPathAdd`, `ZwCommandFunctionLoad`, `ZwCommandCallbackLoad`.
Tutto ciò che tocca l'interfaccia (creare la form, agganciarla al UI Manager, riempirla,
avviare timer che ci scrivono) va fatto **al PRIMO USO**, dentro la funzione del comando,
quando la GUI esiste di sicuro. Schema:

```c
static bool g_pronto = false;
static void assicuraPannello() {
    if (g_pronto) return;
    if (cvxFormCreate((char*)FORM, 0) != ZW_API_NO_ERROR) return;
    cvxFormInsertTo(&info, 3, VX_UI_MANAGER);
    riempi();
    g_timer = SetTimer(NULL, 0, 400, timerProc);
    g_pronto = true;
}
int MioComando(int idData) { assicuraPannello(); cvxFormShow((char*)FORM); return 0; }
```
Conseguenza accettabile: la pagina nella barra laterale compare dopo il **primo clic** sul
bottone del ribbon; essendo `Persistent`, poi resta.

Le altre due cause storiche di crash restano valide: (1) `~ReloadCore` senza
`ZwCommandFunctionUnload` in `CoreExit` (puntatori morti); (2) comandi lanciati senza
PARTE attiva (guardia RequirePart).

## 10. INPUT DI TESTO IN UNA FORM SEMPLICE: `ZsCc::LineEditEx`
*(2026-07-26 — corregge il §4/§5: NON serve passare da un template command)*

Al §5 avevo scritto che per un campo di testo bisogna usare un template command, perché
i `ZsCc::` della cartella `Template/` sono legati ai parametri del `.tcmd`. **Ma esiste
`ZsCc::LineEditEx`**, che è un campo di testo usabile in una form NORMALE, con `id` e
`callback` propri. Lo usa ZW3D stessa in
`ZWSim\ZWApp\Resource\ZwSimulationPlatform\Forms\ZwUiSimBrowser.ui`:

```xml
<widget class="ZsCc::LineEditEx" name="id2">
  <property name="toolTip"><string>search node... [Enter take effect]</string></property>
  <property name="labelText"><string/></property>
  <property name="text"><string/></property>
  <property name="id" stdset="0"><number>2</number></property>
  <property name="callback" stdset="0"><string>MioCallback</string></property>
</widget>
```
```xml
<customwidget>
  <class>ZsCc::LineEditEx</class><extends>QWidget</extends>
  <header>nui/CommonControls/CcLineEditEx.hpp</header>
</customwidget>
```
Il testo digitato si legge con `cvxItemGet(form, idCampo, 0, buffer)`; il callback scatta
all'Invio. ⇒ Una form agganciata al UI Manager può avere **chat vera**: campo d'ingresso +
`ZsCc::ListWidget` per le risposte, senza aprire nessun comando.
Altro widget utile visto lì: `ZsCc::TreeView` (con `callback` e `id`), per elenchi a albero.

## 11. QtWebEngine C'È, ma non è istanziabile da .ui
ZW3D 2025 distribuisce **Qt5WebEngineCore.dll (65 MB)**, `Qt5WebEngineWidgets.dll`,
`QtWebEngineProcess.exe` e i `.pak`. Tentazione: mettere un `QWebEngineView` nella form e
avere dentro ZW3D l'intera interfaccia web. **Non funziona così**: `plugins\designer`
contiene solo `CommonControlsPlugin.dll` e `QtnRibbonDsgn.dll`, cioè il caricatore di form
sa istanziare i `ZsCc::*` e i widget Qt standard, **non** `QWebEngineView` (manca il suo
plugin designer). Nessuna form di ZW3D usa un web view: l'unico "Browser" è
`ZwUiSimBrowser.ui`, che è un albero, non una pagina web.
⇒ Per portare funzioni dentro ZW3D si usano i widget nativi (lista + campo di testo).
Ciò che è **audio** (radio, Spotify) non può uscire da un ListWidget: quello resta al
browser. Distinzione da tenere presente quando si promette una funzione "dentro ZW3D".

## 12. LA SCHEDA RIBBON SI DICHIARA IN DUE POSTI
Perché una pagina compaia sul ribbon non basta definirla in `<Nome>_Pages.zcui`: va anche
**inserita nel layout dell'ambiente**, in
`apilibs\Settings\Default\Strategy\Environment-<n>-<nome>\LayoutStrategy-4-Expert.zcui`:

```xml
<Insert type="RibbonPage" name="EFESTO_Page" topCollection="Layout_10_Part" leftSibling="#InsertAtLast">
  <property text="EFESTO" visible="true" />
</Insert>
```
Ambienti: `10-Part`, `13-Assembly`, `2-Z3`, `6-Cam`. `topCollection` cambia con l'ambiente
(`Layout_10_Part`, `Layout_13_Asm`, `Layout_2_Z3`).
★ Corollario: un `Insert` che punta a una pagina **non più definita** da nessun `.zcui`
produce una **scheda vuota e senza icona** — è così che era rimasta la scheda "AI".
Per togliere una scheda: rimuovere il blocco `<Insert>` nei file di layout (uno per
ambiente), NON cancellare il file, che contiene anche gli inserimenti degli altri plugin.

## 13. ★★ AUDIO DENTRO ZW3D: SI PUÒ (provato il 2026-07-26)
*(correzione di un errore di ragionamento: avevo scritto che "l'audio non puo' uscire da un
ListWidget di ZW3D". Vero ma irrilevante — l'audio non ha bisogno di NESSUN widget. Il
plugin e' una DLL dentro il processo di ZW3D e puo' suonare da se'.)*

**Tecnica: Media Foundation (MFPlay), Win32/COM puro. Niente Qt, niente finestre, niente
player esterni.** ZW3D NON distribuisce Qt Multimedia, ma il Windows SDK ha tutto:
`mfplay.h`, `mfapi.h`, `mfmediaengine.h` + `mfplay.lib mf.lib mfplat.lib mfuuid.lib` (x64).

Ricetta minima (verificata, stato finale `MFP_MEDIAPLAYER_STATE_PLAYING`):
```c
CoInitializeEx(NULL, COINIT_APARTMENTTHREADED);
MFPCreateMediaPlayer(NULL, FALSE, 0, callback, NULL, &player);   // hwndVideo=NULL -> solo audio
IMFPMediaItem *item = NULL;
player->CreateMediaItemFromURL(url, TRUE, 0, &item);   // ★ sincrono: l'ULTIMO parametro
player->SetMediaItem(item);                            //   NON puo' essere NULL (E_POINTER)
item->Release();
// ★ il Play() va fatto nel CALLBACK, all'evento MFP_EVENT_TYPE_MEDIAITEM_SET:
//   SetMediaItem e' asincrona, chiamare Play prima non suona niente.
```
Gli eventi arrivano al thread che ha creato il player → quel thread deve pompare i messaggi
(dentro ZW3D lo fa già l'event loop, quindi non serve fare nulla).

### Cosa suona e cosa no (misurato)
| Sorgente | Esito |
|---|---|
| `https://icy.unitedradio.it/Virgin.mp3` (MP3 diretto) | **PLAYING** |
| `http://icecast.unitedradio.it/Radio105.mp3` (MP3 diretto) | **PLAYING** |
| anteprima AAC/M4A di iTunes | **PLAYING** |
| `https://stream.rds.radio/.../chunklist.m3u8` (HLS) | **FALLISCE** `0xC00D36C4` = MF_E_UNSUPPORTED_BYTESTREAM_TYPE |
⇒ MFPlay **non** legge HLS. Per le stazioni solo-HLS: cercare un'altra voce su
radio-browser che dia uno stream diretto, oppure scaricare i segmenti del chunklist e
concatenarli (il chunklist e' un file di testo con la lista dei segmenti .aac/.ts).

### CANZONI PER TITOLO, senza chiavi: iTunes Search API
`https://itunes.apple.com/search?term=<testo>&media=music&limit=5&country=IT`
→ JSON con `artistName`, `trackName`, **`previewUrl`** = anteprima di 30 s in AAC/M4A,
**senza DRM e senza nessuna chiave API**. Quella si suona in-process con la ricetta sopra.
Provato: "Vasco Rossi Albachiara" → `mzaf_...plus.aac.p.m4a` → PLAYING.

### Limite VERO di Spotify (non e' di ZW3D né della tecnica)
I brani INTERI del catalogo Spotify sono protetti da DRM: si possono decodificare solo
dall'app Spotify o dal Web Playback SDK nel browser con account Premium. Nessuna API
permette di riprodurli in-process. Quindi, dentro ZW3D:
- **ricerca per titolo + ascolto dell'anteprima 30 s** → SI, nativo (iTunes, keyless);
- **brano intero** → si passa la mano all'app Spotify installata (o al browser).
Da dire chiaramente all'utente invece di promettere il brano intero "dentro ZW3D".

### Programma di prova
`EfestoAI\zw3d-plugin\prova-audio\` (prova_audio.cpp + build.bat): dato un URL prova a
suonarlo e stampa gli HRESULT e lo stato finale. Serve a verificare una sorgente PRIMA di
cablarla nel plugin. Ottima abitudine: provare la tecnica in isolamento, non dentro ZW3D.

## 14. ★★ I CLICK SUI CAMPI DI UNA FORM: SERVE `cvxFormCallback`
*(2026-07-26 — questo è il motivo per cui "il pannello si apre ma non fa niente")*

**Sintomo:** la form compare, i click non producono nulla, e nell'area messaggi di ZW3D
appare **`AVVISO: Symbol [] not found in symbol table`**, una volta per ogni campo che ha
la proprietà `callback=`.

**Causa:** avevo registrato la callback SOLO con `ZwCommandCallbackLoad`, che è la funzione
"nuova". Ma per i **campi di una form** (`<property name="callback"><string>NomeCb</string>`)
la registrazione che conta è ancora quella vecchia:

```c
ZW_API_C void cvxFormCallback(vxName Name, void *Function);
```
La sua documentazione lo dice letteralmente: *"Registers a pointer to a callback function
referenced by name in the definition of a GUI form template field (e.g. "callback=MyCallback")"*.
È marcata `@deprecated` in favore di `ZwCommandCallbackLoad` — **ma per i campi delle form
quella nuova NON basta**. Registrarle entrambe in `<Nome>Init`:

```c
ZwCommandCallbackLoad("MioCb", (zwFunctionPointer)MioCb);   // nuova
vxName n; memset(n,0,sizeof(n)); strcpy_s(n,sizeof(n),"MioCb");
cvxFormCallback(n, (void*)MioCb);                            // ★ questa fa arrivare i click
```
★ **Regola generale che ne esce:** la nota `@deprecated` nell'header dice cosa ZWSOFT
consiglia, **non** che la vecchia sia inerte o sostituibile in ogni contesto. Quando la
funzione nuova "non fa niente" senza errori, provare la vecchia prima di dare la colpa al
resto. (Vale al contrario del §8: là `cvxCmdSend` era deprecata E sostituibile con
`ZwCommandSend`; qui no.)
⚠️ Il messaggio d'errore è muto sul nome (`Symbol []` con parentesi vuote): non aiuta a
capire, quindi vale la pena ricordarselo da qui.

## 15. UN PANNELLO AGGANCIATO NON HA UNA PROPRIA FINESTRA (niente WebView2 dentro il dock)
Domanda ricorrente: "si può mettere una pagina web/HTML dentro il pannello di ZW3D, così
l'interfaccia è quella vera?". Risposta **misurata**, non dedotta.
Enumerando con `EnumWindows`/`EnumChildWindows` tutte le finestre del processo ZW3D **mentre
il pannello era aperto e agganciato**, si trovano solo:
- la finestra principale (`Qt5QWindowIcon`, titolo "ZW3D 2025 … - [file]");
- una pila di finestre dell'**area grafica**, tutte con lo stesso rettangolo;
- le **barre strumenti** ("Strumenti di selezione", "Guida ai comandi", …);
- finestre di servizio (IME, `NVOpenGLPbuffer`).
**Del pannello laterale: nessun HWND.** È un widget Qt figlio, e Qt su Windows crea finestre
native solo per i top-level. Quindi:
- non c'è nessuna maniglia in cui reparentare un controllo browser;
- l'API ZW3D non ne offre una (cercato: **zero** funzioni con HWND/hWnd/WindowHandle;
  esiste solo `cvxDispWindowRectGet`, che dà il rettangolo dell'area grafica);
- `QWebEngineView` non è istanziabile da `.ui` (vedi §11): manca il plugin designer.
⇒ **Dentro il dock si possono usare solo i widget nativi `ZsCc::*`.** Se serve davvero
l'interfaccia HTML, l'unica strada è una finestra **senza bordi, di proprietà della finestra
principale di ZW3D**, incollata a un suo bordo e risincronizzata quando ZW3D si sposta o si
ridimensiona: sembra agganciata ma non entra nel sistema di dock (non si può affiancare a
schede né trascinare). Il runtime **WebView2 è presente** su questa macchina
(`C:\Program Files (x86)\Microsoft\EdgeWebView\Application`, v150), quindi tecnicamente si fa.
Da dire chiaramente prima di prometterlo: non è "dentro il pannello", è "attaccato a ZW3D".

## 16. ★★★ VERDETTO SUL PANNELLO CON WIDGET NATIVI: STRADA ABBANDONATA
*(2026-07-26 sera — dopo tre tentativi, con le misure di ognuno)*

Ho provato a costruire il pannello di Efesto coi widget `ZsCc::*`. **Cosa funziona e cosa no,
misurato**, perché non ci si perda un altro pomeriggio:

FUNZIONA:
- form `Dockable`+`Persistent` agganciata al UI Manager con `cvxFormInsertTo` → la pagina
  compare nella barra laterale. Nel log di ZW3D si vede `[vxSendEvt,"UiManager",1,0,2,"EfestoPanel"]`
  quando l'utente la seleziona.
- `cvxFormCreate` → 0, `cvxFormInsertTo` → 0.
- la **funzione della form** (`functionName` nel .ui + `cvxFormFunc`) viene chiamata:
  azione **-4** (VX_FORM_INIT) e **-6** (non documentata in evxFormAction).
- `cvxItemAdd`/`cvxItemDel` riempiono le liste.

NON FUNZIONA (e non ho trovato il perché):
- **i callback dei CAMPI non arrivano mai.** Provato: `ZwCommandCallbackLoad` da solo;
  `cvxFormCallback` in aggiunta; `functionName` sulla form + `cvxFormFunc` registrata.
  Con tutto questo la funzione della form viene chiamata, ma `EfestoPanelCb(form, campo, riga)`
  **zero volte**, anche cliccando sulle righe. Il messaggio `AVVISO: Symbol [] not found in
  symbol table` sparisce aggiungendo `functionName`, ma i click restano muti.
- ⇒ Probabile: in una form usata come **pagina del UI Manager** gli eventi dei campi seguono
  un'altra strada (forse i template command sono l'unico modo supportato).

RIPIEGO che NON dipende dai callback (se un giorno serve): **polling dal timer**.
`ZW_API_C void cvxItemSelected(char *Form, int idField, int *idItem);` dà la riga selezionata;
dal timer Win32 (350 ms) si rileva il cambio, si esegue l'azione e si deseleziona con
`cvxItemSelect(form, campo, -1)`. Nessuna callback coinvolta.

★★ **CAUSA DI CRASH TROVATA (la stessa di sempre, con un'altra API):**
`cvxFormFunc` e `cvxFormCallback` sono della famiglia **cvx** e si scaricano con
**`cvxCmdFuncUnload(vxName)`**, NON con `ZwCommandFunctionUnload`. Scaricando solo i comandi
Zw*, alla chiusura di ZW3D restavano puntatori nella DLL smappata → access violation con
**`#1 <unknown module>`** nel TraceStack e nel crash.log l'ultima riga utile è
`[vxSendEvt,"UiManager",...]`. Nell'Exit vanno scaricate TUTTE le registrazioni, di entrambe
le famiglie. (È la Causa 1 di `reference_zw3d_crash_cause`, ripetuta perché ho guardato solo
le API nuove.)

**DECISIONE (dell'utente, dopo aver visto il risultato):** il pannello a widget nativi è
"bruttissimo" e non interattivo → si abbandona. La strada scelta è mostrare **la pagina web
vera** (quella che gira sul telefono) in una finestra **senza bordi, figlia della finestra
principale di ZW3D**, incollata a un suo bordo. Essendo una finestra FIGLIA, si muove
automaticamente con ZW3D (le coordinate sono relative al genitore); resta da risincronizzare
solo il ridimensionamento, e per quello il timer c'è già.
Come ottenerla senza SDK aggiuntivi: lanciare Edge/Chrome con `--app=<url>` e
`--user-data-dir` dedicata, trovarne l'HWND per PID, poi `SetParent` sulla finestra
principale di ZW3D e togliere i bordi con `SetWindowLong(GWL_STYLE, ...)`.
Il runtime **WebView2 c'è** (v150) se un domani si vuole fare la cosa pulita col suo SDK.
