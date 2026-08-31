# STATO REALE DEL PLUGIN — e come andare avanti senza Claude

Scritto il **2026-08-02**, ultimo giorno utile. È il documento da leggere per
primo. Dice quello che funziona **verificato**, quello che non funziona
**verificato**, e quello che nessuno ha ancora provato.

> **Regola che vale più di tutte le altre.**
> Non fidarti mai di un rapporto: guarda il file sul disco.
> In questo progetto ogni volta che qualcuno ha dichiarato "fatto" senza aprire il
> file, la cosa non era fatta. È successo a Hermes e è successo a Claude.

---

## 1. COSA FUNZIONA — verificato aprendo i file

**Le regole d'officina.** `C:\Alcafer\Modelli\_Comuni\REGOLE_OFFICINA.json`, 48
regole misurate sui disegni veri dell'utente, non dedotte. Le più importanti:
R041 (arie tutte uguali, i vuoti sono n+1), R044 (aria max 100 mm, D.M. 236/89),
R045 (paga l'occhio), R036/R038 (profilo e spessore dalla geometria), R047 (archi
finti). Il lettore C++ è `src\RegoleOfficina.cpp` e funziona.

**Il preventivatore.** `C:\Alcafer\Modelli\_Comuni\PREZZI_OFFICINA.json` +
`config\pricing_config.json`. Tarato su un lavoro vero: due inferriate vendute
1700 € posate. Ferro 1,00 €/kg, verniciatura 32,27 €/m² **su due facce**,
obiettivo 35 €/ora-uomo, accantonamento fiscale 23,72%. Il motore è
`src\QuoteEngine.cpp`.

**La lettura della geometria.** Riconosce profili tondi e quadri, ricava lo
spessore dai raggi d'angolo, distingue i fori dai raggi. Provato su cinque disegni
dell'utente.

**Il censimento dei comandi.** `EfestoAI\knowledge\CENSIMENTO_COMANDI.md`: 19 vivi,
7 abbozzi, 2 rotti, ognuno con il suo limite dichiarato. È onesto — usalo.

**L'indice delle API.** `EfestoAI\knowledge\STUDIO\INDICE_API.jsonl`, 3.031 funzioni
con firma, header e riga. Verificato a campione: 10 firme su 10 identiche.
**Serve a non inventare più nomi di API.** È costato una notte scoprire che
servisse.

**Il cervello di Efesto risponde onestamente.** Alla domanda trabocchetto su una
funzione inesistente ha risposto «Non lo trovo nel mio indice.» Non inventa.

---

## 2. COSA NON FUNZIONA — verificato

**La Diagnosi fa cadere ZW3D.** Il 2026-08-02 alle 11:39:48. Il log di ZW3D si
interrompe di netto. È stata aggiunta una **traccia**: `DiagTraccia()` scrive ogni
fase in `%TEMP%\SuperAssistente\diagnosi_traccia.txt` con flush immediato.
**Al prossimo crash, l'ultima riga di quel file dice dove muore.** Partire da lì.

**Efesto non si apre.** Sei clic, nessuna finestra, nemmeno il messaggio d'errore
che il codice prevede. Il `.tcmd` e la `.ui` ci sono e sono installati. Il sospetto
più forte: `cvxFormShow` non è la via giusta — le form che funzionano si aprono con
`!` e il loro `.tcmd`. **Provare quella strada prima di altre.**

**L'inferriata non usa i weldment profile.** Verificato nel log: nessun
`!CdWeldStruct`. Disegna con estrusioni. `src\WeldmentExecutor.cpp` esiste, ha la
macro giusta, e **nessuno lo chiama**.

**I comandi lavorano ma tacciono.** Nove comandi cliccati, zero errori nel log,
tutti hanno prodotto file in `%TEMP%` — e l'utente non ha visto niente. Non è un
difetto di calcolo: è che il risultato resta nascosto.

**Efesto non sa riparare né installare.** È il requisito espresso dall'utente e
non esiste ancora. Il mandato 02 lo descrive per intero.

---

## 3. LE TRAPPOLE CHE HANNO FATTO PERDERE PIÙ TEMPO

**Un comando ha bisogno di TRE pezzi.** Codice registrato + `.tcmd` + `.ui`, più
`<Action>` e `<Control>` nei `.zcui` e un'icona. Se ne manca uno, il bottone c'è e
**non succede niente, senza messaggi**. Nove comandi erano fermi per la `.ui`
mancante. Efesto era fermo per il `.tcmd` mancante.

**Dopo aver toccato i `.zcui` va ricompilato il Bridge**, che rigenera
`AUTOMAZIONE.zrc`. Senza, ZW3D legge il ribbon vecchio.

**I `.cpp` nuovi vanno aggiunti a `SuperAssistenteEngine.vcxproj`.** Dimenticarlo
dà LNK2001 e ha tenuto la build rotta per settimane.

**Le virgolette doppie spezzano l'argomento passato a hermes.exe.** Il mandato
arriva a pezzi, argparse fallisce, e la build passa lo stesso perché non è
cambiato niente. Costato una notte. Il runner ora le sostituisce con apostrofi.

**La build che passa non dimostra che il lavoro sia fatto.** Un comando che
*stampa* la formula invece di applicarla compila benissimo. Il runner ora cerca
"NON IMPLEMENTATO", "TODO", "placeholder" nei file toccati e segnala il sospetto.

**PowerShell 5.1 e 7 non si comportano uguale.** I runner vanno lanciati con
`pwsh` e salvati **con il BOM**, o le lettere accentate rompono il parser.

---

## 4. COME FAR LAVORARE HERMES

    C:\Users\infoa\Downloads\03_PLUGIN_ZW3D\_LAVORO_NOTTURNO\
      coda_finale\*.txt      i mandati, eseguiti in ordine alfabetico
      runner_finale.ps1      un giro: snapshot → hermes → build → anti-abbozzo
      finale.ps1             rilancia il giro all'infinito
      log\_RIEPILOGO.md      l'esito di ogni mandato
      snapshot\              copia di src, include, Resource PRIMA di ogni mandato

Si lancia così:

    & 'C:\Program Files\PowerShell\7\pwsh.exe' -NoProfile -ExecutionPolicy Bypass -File "...\finale.ps1"

**Un mandato buono contiene sempre:** il fatto accertato con data e prova, dove
sta il materiale che esiste già (per non farlo ripartire da zero), le firme delle
API verificate, come si compila, cosa NON toccare, e in fondo il divieto esplicito
di consegnare abbozzi con l'ordine di priorità se non ci sta tutto.

Gli snapshot hanno già salvato il lavoro due volte, una di Hermes e una di Claude.
**Non toglierli.**

---

## 5. IN CHE ORDINE ANDARE AVANTI

1. **Il crash della Diagnosi.** È l'unico difetto che fa perdere il lavoro aperto.
2. **Efesto che si apre.** Senza, tutto il resto della sua storia non esiste.
3. **I risultati visibili.** Nessun comando può finire in silenzio: un riepilogo a
   schermo con i numeri e dove ha scritto. È la differenza fra uno strumento e un
   giocattolo, e costa poco.
4. **Il weldment collegato**, col profilo letto dalle regole per nome — `30x30x2`,
   non un indice — e i tagli d'angolo fatti da "Gestisci estremità".
5. **Efesto che ripara e installa** (mandato 02, parte B).
6. **Efesto che disegna** (mandato 05).

---

## 6. DOVE STA TUTTO

    progetto      C:\Users\infoa\Downloads\03_PLUGIN_ZW3D\SuperAssistentePlugin_FINALE_3\FINALE
    installato    C:\Program Files\ZWSOFT\ZW3D 2025\apilibs\
    regole        C:\Alcafer\Modelli\_Comuni\REGOLE_OFFICINA.json
    prezzi        C:\Alcafer\Modelli\_Comuni\PREZZI_OFFICINA.json
    conoscenza    C:\Users\infoa\EfestoAI\knowledge\
    documenti     C:\Users\infoa\Antigravity\src\knowledge\
                    COME_ESTENDERE_IL_PLUGIN.md        gli 8 passi per un comando
                    zw3d-rules.md                      macro weldment verificate
                    MANDATO-EFESTO-RISCRITTURA-STORIA.md
                    ARCHITETTURA-NESTING-DISTINTE-PREVENTIVO.md
                    questo file

**Il backup prima di ogni installazione** sta in
`apilibs\_BACKUP_SuperAssistente_<data>`. Se una versione rompe tutto, si torna
indietro copiando quei due DLL.

---

## 7. LE DOMANDE ANCORA APERTE ALL'UTENTE

Poche e tutte piccole: quante cerniere per anta; quanto costa l'asta col puntalino
del deviatore singolo; quando si usa il deviatore doppio e quando i due singoli;
la soglia oltre la quale il laserista passa dal prezzo a pezzo a quello a chilo.

E una che non è piccola: **il regime forfettario non si applica alle società**. Se
i due soci sono davvero una società, i conti fiscali del preventivatore vanno
rifatti. Da chiarire col commercialista prima di usarli.
