# COME SI CREA E SI POTENZIA IL PLUGIN — ricetta completa
_Scritta da Claude il 2026-08-01. Serve a chi vuole aggiungere qualcosa al plugin
ZW3D quando chi l'ha scritto non c'e' piu': Efesto, Hermes, o un altro agente.
Ogni passo qui e' stato PAGATO con un errore reale. Saltarne uno = il comando non
funziona, e il sintomo non dice mai dove hai sbagliato._

## 0. DOVE SONO LE COSE
```
SORGENTE  C:\Users\infoa\Downloads\03_PLUGIN_ZW3D\SuperAssistentePlugin_FINALE_3\FINALE\
INSTALLATO C:\Program Files\ZWSOFT\ZW3D 2025\apilibs\
SDK        C:\Program Files\ZWSOFT\ZW3D 2025\api\inc\   (237 header)
ESEMPI     C:\Program Files\ZWSOFT\ZW3D 2025\api\ApiExample\
REGOLE     C:\Users\infoa\Antigravity\src\knowledge\zw3d-rules.md
DIARIO     C:\Users\infoa\Antigravity\src\knowledge\ZW3D-WORKLOG.md
OFFICINA   C:\Alcafer\Modelli\_Comuni\REGOLE_OFFICINA.json
MODELLI    C:\Alcafer\Modelli\<Tipologia>\*.json
```

## 1. AGGIUNGERE UN COMANDO NUOVO — gli 8 passi, nessuno saltabile

**(1) La funzione C++.**
In `src\SuperAssistenteEngine.cpp` (o un .cpp tuo). Due firme possibili:
- comando diretto:   `void Cmd_Xxx()`
- comando TEMPLATE (con pannello quote): `int Cmd_Xxx(int idData)`
Usa il template se l'utente deve inserire misure. Modello che funziona: `SA_SvilCono`.

**(2) Registrarlo in CoreInit.**
Comando diretto: aggiungilo alla tabella `kCommands` (nome -> funzione).
Comando template: serve ANCHE `cvxCmdTemplate(percorso_del_tcmd)`, altrimenti il
bottone parte ma non apre nulla e la funzione non viene mai chiamata.
```cpp
ZwCommandFunctionUnload("SA_Xxx");   // prima scarica: se una Engine precedente e'
ZwCommandFunctionLoad("SA_Xxx", (zwFunctionPointer)Cmd_Xxx, ZW_LICENSE_CODE_GENERAL);
cvxCmdTemplateUnload(tcmd); cvxCmdTemplate(tcmd);   // solo per i template
```

**(3) Scaricarlo in CoreExit — OBBLIGATORIO.**
`ZwCommandFunctionUnload("SA_Xxx");` per OGNI comando, piu' `cvxCmdTemplateUnload`.
Senza, dopo un ReloadCore ZW3D chiama un puntatore MORTO -> ACCESS VIOLATION al
primo clic. Confermato da crash reali.

**(4) Il file `.tcmd`** in `Resource\Commands\SA_Xxx.tcmd` — descrive i parametri.
Copia la struttura di `SA_SvilCono.tcmd`, non inventarla.

**(5) Il file `.ui`** in `Resource\Forms\SA_Xxx.ui` — e' la finestra.
★ SENZA QUESTO IL COMANDO SEMBRA ROTTO: si registra, il template si carica, e
cliccando NON SUCCEDE NIENTE. Costato una serata il 2026-07-31.

**(6) La voce nella ribbon**, due file:
`Settings\Default\ResourcePool\AUTOMAZIONE.zcui` -> blocco `<Action>`
`Settings\Default\ResourcePool\AUTOMAZIONE_Pages.zcui` -> `<Control>`
Convenzione dei nomi, da rispettare:
- `ID_!Nome` se il comando ha una form (`<Form>Nome</Form>`, `<Script>!Nome</Script>`)
- `ID_~Nome` se e' diretto (`<Form/>` vuoto, `<Script>~Nome</Script>`)
Il `name` dell'Action e l'`action` del Control devono COMBACIARE.

**(7) L'icona.** PNG in `icons\`, riferita SENZA estensione: `<Icon>nome</Icon>`.
★ Salvala con i SOLI chunk essenziali (IHDR/IDAT/IEND). `System.Drawing` aggiunge
sRGB/gAMA/pHYs e ZW3D puo' non caricarla. Se non hai un'icona, lascia `<Icon></Icon>`
vuoto: MAI puntare a un file inesistente.

**(8) Il progetto.** Se hai creato un .cpp nuovo, aggiungilo a ENTRAMBI i vcxproj
(`SuperAssistenteEngine.vcxproj` e `...2027.vcxproj`). Metterlo in uno solo =
"simbolo esterno non risolto". E' successo davvero: la build 2025 e' rimasta rotta
per settimane perche' i file dei ferri erano solo nel progetto 2027.

## 2. COMPILARE
```
MSBuild: "C:\Program Files\Microsoft Visual Studio\18\Community\MSBuild\Current\Bin\MSBuild.exe"
"SuperAssistenteEngine.vcxproj" /p:Configuration=Release /p:Platform=x64
"SuperAssistenteBridge.vcxproj" /p:Configuration=Release /p:Platform=x64
```
Il Bridge nel PostBuild rigenera `AUTOMAZIONE.zrc` con `zrc.exe`: **ogni modifica ai
.zcui o alle .ui richiede di ricompilare il Bridge**, non solo l'Engine.
⚠️ I progetti 2025 e 2027 CONDIVIDONO la cartella `obj\`: prima di cambiare
versione fai Clean, o mescoli oggetti compilati contro SDK diversi.
0 errori o non e' fatto. Codice non compilato = non consegnato.

## 3. INSTALLARE (deploy) — la lista COMPLETA
```
bin\x64\Release\SuperAssistenteEngine.dll  ->  apilibs\Core\
bin\x64\Release\SuperAssistenteBridge.dll  ->  apilibs\
bin\x64\Release\AUTOMAZIONE.zrc            ->  apilibs\
Resource\Commands\*.tcmd  -> apilibs\Resource\Commands\  E  apilibs\Settings\Default\ResourcePool\
Resource\Forms\*.ui       -> apilibs\Resource\Forms\        <-- IL PIU' DIMENTICATO
Settings\Default\ResourcePool\*.zcui -> apilibs\Settings\Default\ResourcePool\
icons\*.png               -> apilibs\icons\
Resource\Panels\gallery\* -> apilibs\Resource\Panels\gallery\
```
- L'**Engine** si puo' sostituire con ZW3D APERTO (gira da copia shadow in %TEMP%).
- Il **Bridge** NO: ZW3D lo tiene bloccato, va chiuso.
- ZW3D va **riavviato** per caricare DLL, ribbon, .tcmd e .ui nuovi.
- ⚠️ `apilibs` e' CONDIVISA con CamApi/NCTI: mai wildcard in cancellazione, mai
  svuotarla, MAI toccare `languages\`.
- ⚠️ Attenzione al maiuscolo/minuscolo copiando in `icons\`: Windows non distingue
  e puoi sovrascrivere un file del fornitore.

## 4. QUANDO "NON FUNZIONA" — diagnosi in ordine
1. **Si carica l'Engine?** Cancella `%TEMP%\profili_zw3d.txt` e riavvia ZW3D: se
   ricompare, CoreInit gira fino in fondo. Il problema NON e' il caricamento.
2. **C'e' un crash?** `%APPDATA%\ZWSOFT\ZW3D\ZW3DCrashReport`: l'ultima riga e' il
   comando colpevole. Nessun file nuovo = non sta crashando.
3. **Il bottone non fa niente?** Manca la `.ui` sul disco (punto 5 sopra), oppure
   `name` dell'Action e `action` del Control non combaciano.
4. **Vedi la ribbon vecchia?** Non hai copiato i .tcmd nelle copie SCIOLTE in
   `ResourcePool\`, oppure non hai ricompilato il Bridge (il .zrc e' vecchio).
5. **L'icona non appare?** Nome del file diverso da quello nel tag `<Icon>`, oppure
   PNG con chunk accessori.

## 5. COLLAUDO
- **A FREDDO** (senza ZW3D): la logica pura si compila e si prova da sola. Vedi
  `tools\test_unfold.cpp`. Deve stampare "TUTTO OK".
  ⚠️ L'antivirus a volte cancella gli .exe di test appena compilati.
- **A CALDO** (dentro ZW3D): serve una PARTE attiva per la geometria.
  `ZW3dRemotec.exe /R local` NON consegna i comandi su questa macchina: esce 0 senza
  eseguire. Il metodo che funziona e' far scrivere al comando un FILE in `%TEMP%`
  e rileggerlo.

## 6. LE REGOLE CHE NON SI VIOLANO (zw3d-rules.md §1)
1. MAI le `cvxPart*` di CREAZIONE FORMA: 3 crash reali. Usa le `Zw*` moderne.
2. Si esce da uno schizzo SOLO con `cvxRootExit()`.
3. `RequirePart` prima di creare geometria: molti comandi crashano senza parte attiva.
4. `ZwCommandFunctionUnload` in CoreExit per ogni comando.
5. SEH (`__try/__except`) attorno alle creazioni forma, con i `std::vector` FUORI dal
   `__try` (errore C2712).
6. Niente funzioni `@deprecated`.
7. **Nessuna funzione inventata.** Se non e' in un header, NON ESISTE. Cercala in
   `knowledge\zw3d-api-index-locale.tsv` (2869 firme) e copiala esatta.
   Inventarne una = far crashare ZW3D di chi ci lavora.

## 7. LE REGOLE D'OFFICINA NON SI SCRIVONO NEL CODICE
Stanno in `C:\Alcafer\Modelli\_Comuni\REGOLE_OFFICINA.json` (34 regole, ognuna con
cosa vale, dove si applica e cosa succede se la sbagli). Il codice le LEGGE da li'.
Se una regola cambia, si cambia SOLO in quel file.
★ R031: nessun valore e' fisso. Tutti i numeri sono valori predefiniti che l'utente
deve poter cambiare: il cantiere impone eccezioni continue.

## 8. IL DIARIO
Ogni intervento va annotato in `knowledge\ZW3D-WORKLOG.md`: data reale, file toccati,
build OK/errori, prova fredda/calda, stato, prossimo passo. Se rompi qualcosa, annota
il SINTOMO esatto e l'ultima modifica prima del guasto.
Serve a non rifare due volte la stessa prova: e' gia' successo di riprovare cose gia'
provate perche' nessuno le aveva scritte.
