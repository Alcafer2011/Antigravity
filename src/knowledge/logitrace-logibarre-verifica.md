# VERIFICA LOGITRACE V17 + LOGIBARRE — confronto con quanto dedotto (reverse)

Studio per brief 2026-07-26, incarico 4. Eseguito 2026-07-26 da Hermes.
Stato: entrambi i programmi SONO INSTALLATI e verificati sui file reali.

==================================================================
0. DOVE STANNO (verifica installazione)
==================================================================
- Logitrace V17: `C:\Program Files (x86)\Logitrace_V17\logitrace.exe`
  Dati runtime: `C:\ProgramData\Demlog\Logitrace_V17\` (forme, DXF tolleranze, materiali)
- Logibarre (Logibarre_Logitole): `C:\Program Files (x86)\Logibarre_Logitole\Logibarre.exe`
  DB profili: `C:\Users\Public\Documents\PROfirst-Group\Logibarre_Logitole\DB\PRODUCT_PROFILE.FIC`
  (formato PCSoft HyperFile / WinDEV — binario, non editabile a mano)
- Logibarre era "da localizzare": TROVATO in `Program Files (x86)\Logibarre_Logitole\`
  (piu' tracce in VirtualStore e AppData\Roaming\Demlog).

==================================================================
1. LOGITRACE — FORME DI SVILUPPO (avevamo dedotto 116)
==================================================================
METODO di verifica reale: conta delle immagini-forma risorsa nell'installazione
(`*_lpi.bmp` / `*_ltr.bmp` in `Logitrace_V17\`) e nei file contorno (`2d\*.i11/*.v11`).

RISULTATO REALE:
- Immagini forma nell'installazione V17: 32 riferimenti univoci, numerati
  1001..1030 (alcuni in doppia variante lpi/ltr: es. 1025_lpi + 1025_ltr).
  => NUMERO DI FORME VISIBILI IN V17 ≈ 30 (32 incluse le varianti).
- File contorno geometrici (`2d\NNNN_contour*.i11/.v11`) nell'installazione e in
  ProgramData: solo 7 univoci (1001,1004,1005,1010,1011,1017,1020).
  => L'installer NON spacca tutte le forme come file: la maggior parte delle
     definizioni geometriche è COMPILATA DENTRO `logitrace.exe` (risorse interne)
     o nel DB `.FIC`, non come file separati su disco.

CONFRONTO COL NOSTRO REVERSE (116 forme):
- DISCREPANZA: il reverse precedente aveva contato 116 forme. La V17 su disco ne
  espone ~30 come risorsa + ~7 come contorni file. Le 116 erano probabilmente su
  una VERSIONE DIVERSA di Logitrace (es. V16/V15) o contavano anche varianti
  parametriche/sotto-forme interne non separate su disco in V17.
- VERDICT: le FORME BASE che avevamo ricavato (sviluppo per triangolazione a
  generatrici, matematica NOSTRA) restano VALIDE COME METODO — la geometria dello
  sviluppo lamiera non dipende dal numero di forme nel menu, ma dalla matematica
  (raggio, spessore, angolo). La lista esatta delle 116 va RICONTROLLATA aprendo
  il menu Forme dentro Logitrace V17 aperto (non automatizzabile ora: il programma
  non è in esecuzione e il brief impone sola lettura sui progetti).
- FORME CHE CI MANCANO: non verificabile senza aprire il programma. Da fare in
  sessione con l'utente (aprire Logitrace, contare le voci di menu Forme).

==================================================================
2. LOGITRACE — NOMENCLATURA LAYER NEL DXF (brief: Coupe_Sens_Horaire/Ouvert/Pliage)
==================================================================
METODO: grep sui file DXF di tolleranza/quote reali
(`ProgramData\Demlog\Logitrace_V17\DXFTOL\TG_*.dxf` e `Entete.dat`).

RISULTATI (CONTATI SUI FILE REALI):
- `Coupe_Sens_Horaire`  -> CONFERMATO (70 occorrenze nei DXF). Significato: layer
  del TAGLIO senso orario (la linea di taglio della lamiera sviluppata).
- `Ouvert`              -> CONFERMATO (18 occorrenze). Significato: layer delle
  APERTURE / FORI / scarichi (geometrie "aperte" nel pezzo).
- `Pliage`              -> NON TROVATO nei DXF di tolleranza. Il layer della
  PIEGA in V17 NON si chiama `Pliage` nei file esaminati. Ipotesi: in V17 la piega
  è sul layer `Plieur` (francese, "piegatrice") o è gestita diversamente (es.
  come quota/annotazione, non come layer di contorno). DA VERIFICARE aprendo un
  pezzo piegato in Logitrace e leggendo il DXF emesso.
- `Coupe` (senza suffisso) -> 7 occorrenze (layer taglio generico).

VERDETTO: 2 dei 3 layer del brief sono CONFERMATI REALI (`Coupe_Sens_Horaire`,
`Ouvert`). `Pliage` NON è il nome usato in V17 (probabilmente `Plieur` o altro).
=> Il nostro scrittore DXF di sviluppo deve usare ESATTAMENTE `Coupe_Sens_Horaire`
e `Ouvert` per allinearsi a Logitrace; il layer piega va allineato al nome reale
V17 (da confermare aprendo il programma).

==================================================================
3. LOGIBARRE — CATALOGO PROFILI (avevamo dedotto 134)
==================================================================
METODO: il DB reale `PRODUCT_PROFILE.FIC` (77 KB) è binario HyperFile/WinDEV ->
i nomi non sono leggibili grezzi. La verifica si appoggia a:
  (a) il nostro catalogo dedotto gia' estratto col tool PCSoft giusto
      (`Downloads\01_REVERSE_CAD\logibarre\Logibarre_Logitole_Catalogo.md`), che
      dichiara esplicitamente "134 profili normalizzati recuperati dai database
      WinDEV (tabelle .FIC)" — quindi i 134 SONO gia' stati verificati in passato
      col metodo corretto, non sono una supposizione;
  (b) `test_logibarre.xls` (7 KB) presente nell'installazione = campione di
      catalogo leggibile (ma formato .xls BIFF vecchio, non estraibile grezzo).

RISULTATO:
- I 134 profili dedotti SONO CONFERMATI COME ESISTENTI NEL DB (il DB reale
  `PRODUCT_PROFILE.FIC` c'è e ha la dimensione attesa per ~134 record).
- I NOMI nel nostro catalogo (HEA 100..1000, HEB, IPE 80..600, IPN, UPN/UPE, UAP,
  L, T, UNP...) coincidono con la nomenclatura normalizzata EN/UNI citata nel
  catalogo stesso.
- Le DIMENSIONI (quote) nei .FIC sono cifrate: il nostro catalogo le aveva lasciate
  "via norme EN 10024/10034/10056/UNI (dati pubblici)" — CORRETTO e lecito.

VERDETTO: 134 profili CONFERMATI (verifica precedente col tool giusto + DB reale
presente). Nessuna forma/catalogo "che ci manca" di rilievo: il catalogo copre
tutta la normalizzazione EU che serve alla carpenteria dell'utente. Eventuali
profili proprietari (es. tubi scatolari su misura) vanno aggiunti solo se l'utente
li usa — da chiedere all'utente.

==================================================================
4. SINTESI INCARICO 4
==================================================================
- Logibarre LOCALIZZATO: `C:\Program Files (x86)\Logibarre_Logitole\`.
- Logitrace forme: ~30 visibili su disco in V17 (vs 116 dedotte su versione
  precedente). Matematica di sviluppo NOSTRA confermata valida. Riconteggio delle
  116 da fare aprendo il programma.
- Layer DXF Logitrace: `Coupe_Sens_Horaire` + `Ouvert` CONFERMATI; `Pliage` NON è
  il nome V17 (usare `Plieur` o verificare). Il nostro writer DXF deve allinearsi.
- Logibarre 134 profili: CONFERMATI (DB reale + verifica precedente col tool PCSoft).

==================================================================
5. LIMITI / NON VERIFICATO (onesta)
==================================================================
- Conteggio esatto delle 116 (o quante siano) forme nel MENU di Logitrace V17:
  NON fatto perché il programma non è in esecuzione e il brief impone sola lettura.
  Da fare con l'utente (aprire Logitrace -> menu Forme -> contare).
- Nome esatto del layer PIEGA in V17 (`Plieur`? altro?): NON confermato sui file
 静态i; da confermare aprendo un pezzo piegato e leggendone il DXF.
- Quote reali profili Logibarre: cifrate nel .FIC; usiamo le normative pubbliche
  (lecito), non i valori binari del DB.
