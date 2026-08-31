# MANDATO — EFESTO RISCRIVE LA STORIA DEL DISEGNO

Richiesta dell'utente, 2026-08-01, parole sue:

> «Efesto deve saper riconoscere anche la storia, perche' io molte volte non conosco
> i comandi e faccio paciughi per ottenere il risultato. Lui, analizzando il risultato
> e i comandi lunghi elaborati per arrivarci magari con errori, dovrebbe riscrivere in
> modo corretto con i comandi giusti il disegno mantenendo il risultato da me
> raggiunto, oltre correggere le varie regole.»

Questo documento e' la specifica. Non e' una proposta: e' cosa va costruito.

---

## IL PRINCIPIO CHE NON SI NEGOZIA

**Il risultato dell'utente e' sacro.** Efesto non decide che una forma e' brutta o
sbagliata: decide che il MODO di ottenerla era contorto. La forma finale deve
restare quella, al millimetro.

Da cui la regola di sicurezza, che viene prima di tutto il resto:

> La riscrittura NON modifica mai il file dell'utente. Genera una parte NUOVA,
> a fianco, e poi DIMOSTRA che coincide. Se non coincide, non si sostituisce nulla
> e si dice perche'.

Una riscrittura che "crede" di aver mantenuto il risultato e' inutile e pericolosa.
La prova geometrica e' cio' che rende la funzione usabile.

---

## LA CATENA, IN CINQUE PASSI

### 1. LEGGERE COME E' STATO FATTO
Due sorgenti, complementari:
- **la storia della parte**: `ZwHistoryListGet` da dentro ZW3D — le feature con i
  loro parametri, in ordine, comprese quelle rotte (`cvxPartFtrIsMissRef`)
- **il log di ZW3D**: `%APPDATA%\ZWSOFT\ZW3D\ZW3D 2025\output\logs\*.log` — ogni
  comando eseguito, con i commenti esplicativi. Qui si vedono anche i tentativi
  ABBANDONATI, che nella storia non compaiono: sono la traccia piu' onesta del
  "paciugo".

La storia dice COSA e' rimasto. Il log dice COSA HAI PROVATO. Servono entrambi.

### 2. CAPIRE COSA E' VENUTO FUORI
Indipendentemente da come e' stato fatto: leggere il solido finale e riconoscerlo.
E' esattamente cio' che facciamo gia' sui file STEP — profili dalle facce (R036),
spessori dai raggi d'angolo (R038), arie e posizioni (R041/R044).
Questa e' l'unica descrizione affidabile dell'INTENZIONE, perche' e' il risultato
che l'utente ha approvato.

### 3. RICONOSCERE I PACIUGHI
Catalogo dei modi contorti, da ampliare man mano. Quelli gia' visti sui disegni veri:

| paciugo | comando giusto |
|---|---|
| schizzo 2D + estrusione per fare un membro strutturale | `SttMemberLyt` / `!CdWeldStruct` (Structure Member) |
| tagli d'angolo calcolati e fatti a mano | `CdWeldTrim` (Trim), o "Gestisci estremita'" di `!CdWeldStruct` |
| linee disegnate come archi con raggio enorme | linee vere (R047) |
| feature cancellate che lasciano riferimenti orfani | ricostruire il riferimento o rimuovere la dipendenza |
| molte operazioni booleane piccole al posto di una sola | l'operazione unica corrispondente |

Il criterio per aggiungere una riga: deve venire da un disegno REALE, non da una
supposizione. Ogni riga cita il disegno e il corpo dove e' stata vista.

La fonte per "quale sarebbe il comando giusto" e'
`C:\Users\infoa\EfestoAI\knowledge\STUDIO\INDICE_COMANDI.json`, che lega i 3591
comandi alle pagine di documentazione ufficiale decompilate dai .chm.

### 4. RISCRIVERE
Emettere una nuova sequenza di feature, pulita, con i comandi nativi giusti, e
parametrica dove ha senso: quote come formule e non come millimetri fissi
(metodo TopSolid), cosi' che il disegno riscritto sia anche MODIFICABILE, non solo
piu' pulito.

Durante la riscrittura si applicano anche le regole d'officina
(`C:\Alcafer\Modelli\_Comuni\REGOLE_OFFICINA.json`, 47 regole).
⚠️ Ma con una distinzione netta:
- **difetti di COSTRUZIONE** (paciughi, archi finti, riferimenti orfani) → si
  correggono, perche' non cambiano la forma
- **violazioni di REGOLA** (arie disuguali R041, aria fuori norma R044) → **cambiano
  la forma**. Si SEGNALANO e si propongono, con i numeri corretti. Si applicano solo
  se l'utente dice di si', una per una.

### 5. DIMOSTRARE CHE E' LO STESSO PEZZO
Confronto geometrico fra il solido originale e quello riscritto:
- volume e massa (tolleranza stretta)
- ingombro
- numero e tipo di facce
- per ogni corpo: profilo riconosciuto e lunghezza

Se tutto coincide → si propone la sostituzione, **con conferma dell'utente**.
Se qualcosa non coincide → si tiene la parte nuova a fianco come proposta, e si
dice ESATTAMENTE cosa differisce. Mai spacciare per riuscita una riscrittura che
non lo e'. Questo e' il punto su cui la funzione vive o muore.

---

## COSA C'E' GIA' E COSA MANCA

**C'e':**
- il log di ZW3D che registra tutto (verificato: e' cosi' che abbiamo ricavato la
  sequenza macro del weldment)
- `INDICE_COMANDI.json` — 3591 comandi legati alla documentazione ufficiale
- il riconoscimento del solido dalle facce — funziona, provato su cinque disegni
- 47 regole d'officina, misurate su disegni reali
- tre controlli di diagnosi gia' definiti: R041 (arie), R043/R047 (corpi anomali e
  archi finti), R044 (normativa)

**Manca:**
- il comando del plugin che estrae la storia (`ZwHistoryListGet`) e la scrive fuori
- il catalogo dei paciughi, che va riempito guardando i disegni dell'utente
- la generazione della sequenza pulita
- il confronto geometrico finale

**PRIMO PASSO CONCRETO**: il comando che dumpa la storia di una parte aperta.
Senza quello non si vede nulla; con quello si puo' gia' oggi analizzare a mano i
disegni dell'utente e riempire il catalogo dei paciughi con casi veri.

---

## ONESTA' OBBLIGATORIA

Efesto deve poter dire: «questa storia non l'ho capita, non la tocco».
Un disegno lasciato com'e' non fa danno. Un disegno riscritto male si': l'utente si
fida del risultato e non se ne accorge finche' non e' in officina col ferro tagliato.
