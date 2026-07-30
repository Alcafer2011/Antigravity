# ZW3D 2027 vs 2025 — DIFFEREZE E COMPATIBILITA' DEI NOSTRI PLUGIN

Studio per brief 2026-07-26, 2b. Aggiornato 2026-07-26.

==================================================================
0. STATO REALE SUL PC (verificato oggi)
==================================================================
- ZW3D 2025: INSTALLATO in C:\Program Files\ZWSOFT\ZW3D 2025
    (api\inc con 237 header zwapi_*.h; ZW3D.lib nella radice; apilibs con i nostri plugin)
- ZW3D 2027: NON ANCORA INSTALLATA (cercata in Program Files, ProgramData, radice
    ZWSOFT: assente). Il brief dice "sta installando": quando c'e' sara' in
    C:\Program Files\ZWSOFT\ZW3D 2027.
=> NON posso fare oggi il confronto header 2025↔2027 (non c'e' la 2027). Qui sotto
   metto (A) cosa e' GIA' verificato sulla 2025 e (B) la procedura esatta da fare
   APPENA la 2027 e' installata, coi comandi copia-incolla.

==================================================================
A. COSA ABBIAMO VERIFICATO SULLA 2025 (prove reali, non brochure)
==================================================================
A.1 Convenzione di caricamento plugin — CONFERMATA IDENTICA a quanto ci serve:
    - I nostri plugin stanno in apilibs\<Nome>.dll e devono esportare <Nome>Init / <Nome>Exit.
    - Efesto.dll   esporta: EfestoInit, EfestoExit (+ EfestoPanelCb, Efesto_Apri, Efesto_Chiedi)
    - SuperAssistenteBridge.dll esporta: SuperAssistenteBridgeInit, SuperAssistenteBridgeExit
    => La convenzione `apilibs\<Nome>.dll` + export `<Nome>Init/<Nome>Exit` è QUELLA USATA.

A.2 Link / ABI — verificato:
    - Entrambi i nostri plugin importano le funzioni DA `ZW3D.dll` a runtime
      (Import DLL: ZW3D.dll → cvxMsgDisp, cvxFormCreate, ZwCommandSend,
       ZwCommandFunctionLoad, ZwCommandCallbackLoad, ZwCommandFunctionUnload, ...).
    - NON linkano ZW3D.lib in fase di build? In realta' ZW3D.lib ESISTE in
      C:\Program Files\ZWSOFT\ZW3D 2025\ZW3D.lib (serve per il link dei simboli).
      I nostri .dll la usano indirettamente tramite gli header; il fatto che a runtime
      risolvano da ZW3D.dll e' normale (ZW3D.lib e' un import lib verso ZW3D.dll).
    - Compilati con MSVC 19.5x / VS2026, 64-bit (Machine 0x8664). ABI Windows x64
      stabile: finche' ZW3D 2027 e' 64-bit (lo e') l'ABI di chiamata non cambia.

A.3 File .zrc / .zcui / .tcmd:
    - Efesto.zrc presente in apilibs (risorsa ribbon/commands). I .tcmd stanno in
      apilibs\Resource\Commands\ (vedi zw3d-rules.md §3: ZW3D legge i .tcmd DA DISCO).
    - Questi formati sono stabili tra major version (ZW3D non li ha cambiati di norma).

==================================================================
B. PROCEDURA DIFF 2025↔2027 (da eseguire APPENA la 2027 e' installata)
==================================================================
B.1 Confronto header API (il metodo affidabile del brief):
    diff -rq "C:\Program Files\ZWSOFT\ZW3D 2025\api\inc" "C:\Program Files\ZWSOFT\ZW3D 2027\api\inc"
    # elenca solo gli header cambiati/rimossi/nuovi. Poi per ogni header diverso:
    diff "C:\Program Files\ZWSOFT\ZW3D 2025\api\inc\zwapi_xxx.h" "C:\Program Files\ZWSOFT\ZW3D 2027\api\inc\zwapi_xxx.h"

B.2 Verifica firme che USIAMO (le nostre dipendenze reali, da Efesto/SuperAssistenteBridge):
    Cerca queste in api\inc 2027 e controlla che la FIRMA sia identica:
      cvxMsgDisp, cvxFormCreate, cvxFormShow, cvxFormInsertTo, cvxItemAdd, cvxItemDel,
      cvxPathApiLib, cvxPathAdd, cvxDataGetText,
      ZwCommandSend, ZwCommandFunctionLoad, ZwCommandCallbackLoad, ZwCommandFunctionUnload,
      ZwCommandMacroExecute  (usata nei weldment, zw3d-rules.md §5)
    Se tutte ci sono con la stessa firma → i nostri plugin compilano contro la 2027.

B.3 Verifica ZW3D.lib 2027:
    ls "C:\Program Files\ZWSOFT\ZW3D 2027\ZW3D.lib"   # deve esserci per il link
    Se c'e' → ricompili i plugin puntando l'include e la lib alla 2027 e fai zw3d(op:'build').

B.4 Verifica .zrc/.zcui/.tcmd: copia quelli 2025 in 2027\apilibs\ e prova il caricamento.

==================================================================
C. "I NOSTRI PLUGIN CI ENTRANO?" — RISPOSTA NETTA
==================================================================
RISPOSTA OGGI (2025 verificata, 2027 non ancora presente):
  **MOLTO PROBABILMENTE SÌ, con ricompilazione contro la 2027.**
  Prove a favore (tutte verificate sulla 2025):
    1. La convenzione di caricamento (apilibs\<Nome>.dll + <Nome>Init/<Nome>Exit) è
       esattamente quella che i nostri plugin già rispettano → NON dobbiamo cambiare
       il modo in cui ZW3D ci carica.
    2. Le API che importiamo (cvx*/Zw* da ZW3D.dll) sono API pubbliche stabili; l'ABI
       x64 non cambia tra major version. Se la 2027 le mantiene (quasi certo), i binari
       continuano a funzionare o si ricompilano senza toccare il codice.
    3. ZW3D.lib esiste sia in 2025 che (ci sara') in 2027 → il link e' possibile.
  Cosa serve COMUNQUE fare (prudenza, non certezze):
    - Ricompilare i plugin contro ZW3D 2027\api\inc e ZW3D.lib 2027 (non riusare i .obj 2025).
    - Eseguire B.1–B.4 e controllare che le firme usate non siano state rimosse/rinominate.
  Cosa NON fare (regole d'officina, dal brief):
    - NON installare la 2027 SOPRA la 2025 finche' non e' chiaro: l'utente lavora con la
      2025 e i plugin (SuperAssistente + Efesto) sono installati li'. Se le due coesistono
      (installazione in cartella separate ZW3D 2027), DILLO esplicitamente e tieni la 2025
      come ambiente di produzione finche' la 2027 non e' collaudata.
    - apilibs e' CONDIVISA con CamApi/NCTI: mai jolly, mai svuotarla, mai toccare
      languages\ (profili weldment e cartigli DI ZW3D).

CONFERMA DEFINITIVA: la si da SOLO dopo B.1–B.4 sulla 2027 installata. Fino ad allora
la risposta e' "probabile SÌ, da confermare col diff header appena la 2027 c'e'".

==================================================================
D. COESISTENZA 2025 + 2027 (se l'utente le tiene entrambe)
==================================================================
- ZW3D installa per major version in cartelle separate (ZW3D 2025 / ZW3D 2027) → i
  plugin vanno deployati NELLA apilibs della versione che vuoi usare.
- I nostri plugin oggi stanno in ZW3D 2025\apilibs. Per usarli in 2027, copia Efesto.dll/
  .zrc e SuperAssistenteBridge.dll nella 2027\apilibs DOPO la ricompilazione 2027.
- NON condividere la stessa cartella apilibs tra le due versioni: tienile separate per
  evitare che una DLL compilata per 2025 venga caricata dalla 2027 (rischio crash).
