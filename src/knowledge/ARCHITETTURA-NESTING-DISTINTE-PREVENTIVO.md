# ARCHITETTURA — NESTING, DISTINTE DI TAGLIO, PREVENTIVO

Decisione dell'utente, 2026-08-01, parole sue:

> «Ovviamente lì dobbiamo sfruttare le funzioni estratte di Advance Steel e
> LogiBarre. LogiBarre l'ho fatto copiare per intero perche' lui utilizza una
> pre-pagina da compilare a mano per poi generare il nesting. Noi la pre-pagina
> possiamo farla funzionare dietro le quinte, nascosta, che viene compilata e rende
> il nesting delle barre automatico, perche' il nesting e' ottimo il suo. Le distinte
> dei tagli e lavorazioni sono ottime quelle di Advance Steel. Manca un
> preventivatore reale.»

Principio: **non riscriviamo cio' che funziona gia' bene.** Si prende il meglio di
ognuno e lo si automatizza. Quello che manca lo costruiamo noi.

---

## 1. IL NESTING DELLE BARRE — LOGIBARRE

### ★ LA SCOPERTA CHE SBLOCCA TUTTO (2026-08-01)
La "pre-pagina" che l'utente compila a mano NON e' un formato chiuso: e' un
**semplice CSV di testo**, il file `.bar`.

Esempio reale, da `out_logibarre\userdocs\test.bar`:
```
P_Angle01,15,2200,45,90,1
P_Angle02,15,2800,60,90,1
P_Angle04,13,1200,120,135,1
```
Sei campi, separati da virgola, righe terminate CRLF:

| campo | significato |
|---|---|
| 1 | nome/marca del pezzo |
| 2 | codice del profilo (numerico, catalogo LogiBarre) |
| 3 | lunghezza in mm |
| 4 | angolo di taglio a sinistra (gradi) |
| 5 | angolo di taglio a destra (gradi) |
| 6 | quantita' |

**CONSEGUENZA**: la pre-pagina la scriviamo NOI. Il flusso diventa:
```
modello ZW3D -> distinta (profili, lunghezze, angoli, quantita') -> file .bar
             -> LogiBarre nesta -> risultato letto e riportato sul foglio ZW3D
```
L'utente non vede piu' la pre-pagina. Il nesting resta il loro, che e' ottimo.

I due angoli per pezzo si legano DIRETTAMENTE al lavoro sui tagli d'angolo del
weldment (`CdWeldTrim` e "Gestisci estremita'" di `!CdWeldStruct`): l'angolo che il
comando nativo calcola e' lo stesso che va scritto nel `.bar`.

### COSA RESTA DA FARE
- ricavare la corrispondenza **codice numerico -> profilo reale** (nel `.bar` compaiono
  15, 13, 16). Il catalogo sta dentro `out_logibarre\app` (file .REP e archivi
  D/E/F/I.zip). Da mappare sul nostro catalogo profili.
- decidere come lanciare LogiBarre e rileggere il risultato del nesting.

### MOTORE
`out_logibarre\sys\optimal1dx.dll` (ottimizzatore 1D, barre) e `optimal2dx.dll`
(2D, lamiere). **NON li tocchiamo e non li richiamiamo direttamente**: si dialoga
per file, che e' interoperabilita' pulita.

---

## 2. LE DISTINTE DI TAGLIO E LAVORAZIONE — ADVANCE STEEL
Materiale gia' estratto in
`Downloads\02_CODICE_PRODOTTO\codice-cpp-da-advance-steel`:
- `cutting_list.cpp` / `.h`   ← la logica delle distinte di taglio e lavorazione
- `messa_in_tavola.cpp` / `.h` ← la logica della messa in tavola
- `parametrico.cpp`, `ferro_battuto.cpp`, cataloghi Eurofer

Vanno portati al livello DISEGNO di ZW3D (`Environment-4-Sheet`), dove oggi il
nostro plugin non compare affatto, appoggiandosi alle tabelle native:
`!CdBomTblCrt` (distinta), `!CdAutoBalloon` (palloncini), `!CdAnntTblCrt`,
`!CdHoleTblMk2`.

---

## 3. IL PREVENTIVATORE — QUESTO VA COSTRUITO DA ZERO
E' l'unico pezzo che nessuno dei programmi copiati fa bene. Parole dell'utente:
«manca un preventivatore reale».

"Reale" significa che deve partire dal disegno e arrivare a un prezzo che l'utente
firmerebbe. Quindi non basta il peso per il prezzo al chilo: servono i tempi.

### COSA IL PROGRAMMA SA GIA' RICAVARE DA SOLO
- peso per profilo e totale (dalla geometria: profilo x lunghezza x peso lineare)
- numero di TAGLI, e per ognuno se e' dritto o in angolo (dal .bar: i due angoli)
- numero di GIUNTI SALDATI (dai nodi fra membri)
- numero di FORI (facce cilindriche nello spessore, R036)
- metri quadri di superficie da trattare (per zincatura e verniciatura)
- sfrido reale della barra (dal nesting di LogiBarre)

### COSA SERVE DALL'UTENTE — SENZA QUESTI NUMERI IL PREVENTIVO E' FINTO
Da chiedere, e da tenere in un file modificabile come le regole d'officina:
1. prezzo al kg per tipo di materiale e profilo (e se cambia per quantita')
2. costo orario dell'officina
3. minuti per: un taglio dritto, un taglio in angolo, un foro, un giunto saldato,
   un metro di saldatura continua
4. costo di zincatura e verniciatura (al kg o al metro quadro)
5. accessori a prezzo fisso: cardini, serrature, motori, piastre
6. trasporto e posa in opera
7. margine, e se cambia fra privato e impresa
8. come si tratta lo SFRIDO: si fa pagare o si assorbe? (lega a R019, soglia 1 m)

⚠️ Come per le regole d'officina, questi valori sono DEFAULT MODIFICABILI: si
scrivono in `C:\Alcafer\Modelli\_Comuni\PREZZI_OFFICINA.json`, non nel codice.

---

## ORDINE DI LAVORO PROPOSTO
1. pagina AUTOMAZIONE nel livello Disegno (`Environment-4-Sheet`) — oggi manca
2. distinta sul foglio con tabella nativa e cartiglio compilato
3. esportazione `.bar` e nesting automatico
4. distinte di taglio da Advance Steel
5. preventivatore, appena l'utente fornisce i numeri del punto 3 qui sopra
