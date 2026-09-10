# Lavori Videoteca — banco di prova PC (10/09/2026)

Kodi 21.3 sul PC, skin.saghe attiva, finestra, pilotato via JSON-RPC 8080.
Sorgente: `traduttore/plugin.video.saghe`. Pull apparecchi: `tmp_addon_pull/20260910/`.

## Stato allineamento
- 8K box (.114) == sorgente == Kodi PC: **identici** (plugin.video.saghe + s4me).
- Raspberry (.105): indietro di 1 file — `resources/lib/copertine.py` vecchio
  (185 righe), il nuovo (242) c'e' ma nella root sbagliata. Si risolve al deploy.
- Lavoro 09/09 (Hermes): ~3600 righe non committate, coerenti su tutti, **non testate**.

## Lista lavori (decisa con l'utente)

- [x] **F — skin sul PC**: FATTO. Caricava perche' era `enabled=0` nel DB
      `Addons33.db`. Nessuna incompatibilita' Kodi 21.3.
- [x] **A — locandine doppie (percorsi)**: FATTO e verificato a schermo.
      Causa: `main.py`/`vetrina.py` prendevano il poster da `segmenti[0][0]`.
      Fix: `schede.poster_percorso(pid)` / `sfondo_percorso(pid)` (usa
      `PERCORSI[pid]["poster"]` se c'e', altrimenti la 1a serie); nuovo
      `_copertina_percorso` in main.py; `_voce(..., pid=)` in vetrina.py;
      `"poster"` esplicito su `dragonball_veloce` (Kai), `gonagai` (Goldrake),
      `naruto_veloce` (Shippuden). 4 file: schede.py, catalogo.py, main.py,
      vetrina.py. Deployati su Kodi PC. **NON committato.**
      RESTA: doppioni tra EPISODI (sdbh ep 53 e 54 hanno la stessa `i`).
- [~] **D — locandine Documentari/Cucina** (rev. 2): quasi chiuso.
      - segnaposto.png (card scura) al posto di poster vuoto (=nero) o
        icona-addon (=bleed). In main.py: widget() + menu_scaffale.
      - widget() ora emette le tessere-titolo "— GRUPPO —" -> la sezione
        MOTORI GARAGE si VEDE nella striscia.
      - widget("film") passato a `_copertina_percorso` -> niente piu'
        doppioni (Dragon Ball / via veloce, i due Doraemon...).
      - copertine.py: `_poster_tmdb` cerca it-IT POI en-US, gestisce le
        PERSONE (chef -> la loro foto), e per i TEMI accetta il primo
        documentario (genere 99) con locandina. Query in scoperte.py
        riscritte col nome CANONICO/inglese dei programmi.
      - copertine.json: **145/183 voci con locandina** (era ~80). I 38
        rimasti sono ricerche a tema ("Pizza", "Dolci", "Primi piatti",
        "Predatori"...) che NON sono programmi: nessun poster unico esiste,
        tengono il segnaposto. Zero doppioni sbagliati.
      RESTA opzionale: far dire al segnaposto il nome del tema.
--- STORICO rev.1 ---
- [~] **D — locandine Documentari/Cucina**: fatto il grosso.
      - "Goku ultraistinto su mezzo elenco" = NON era copertine.py: era
        `menu_scaffale` / i riquadri home che mettevano l'ICONA dell'addon
        come `poster`; la skin la riusava per piu' tessere -> stessa
        immagine su 5. FIX: poster/thumb vuoti quando non c'e' copertina
        (main.py, 2 punti). FATTO.
      - copertine.py cercava l'ETICHETTA decorata ("American Chopper (le
        moto Harley)") invece della query pulita. FIX: usa `cerca:<q>` e
        toglie "documentario/cucina/ricette" davanti. FATTO.
      - copertine.json rigenerato: **127/187 voci con poster** (era ~80).
        Deployato. Le ~60 senza sono quasi tutte ricerche a tema
        ("Deserti", "Barbecue") - ora tessera pulita, niente bleed.
      RESTA: URL scheda tutti OK (il "naruto 404" era un mio errore di
        battitura); qualche quadrato verde nella riga film-saghe = cache
        texture + 1-2 film-percorso senza poster. Minore.
- [x] **B — YouTube solo 2 canali**: FATTO e verificato. `GENERI_YOUTUBE=[]`
      in scoperte.py. La sezione ora e' solo Elisa True Crime + Omega Click.
- [x] **C — Fast N' Loud + Harley sezione propria**: FATTO. Nuovo gruppo
      "MOTORI, GARAGE E RESTAURI" in GENERI_DOC (Fast N' Loud, Gas Monkey,
      American Chopper, Orange County/Monster Garage, Overhaulin', Wheeler
      Dealers, ...), tolti da "I PROGRAMMI DI DISCOVERY E SKY".
- [ ] **B — YouTube**: solo 2 canali veri (Elisa True Crime, Omega Click).
      Ora la sezione `scaffale=youtube` ne mostra 12, mischiati. Ripulire.
- [ ] **C — Fast N' Loud + programma Harley**: sezione motori propria con
      locandine proprie, ora fuori posto (finiscono tra YouTube/documentari).
- [ ] **E — Dragon Ball Heroes**: scelta utente = "resta separata ma segnalata".
      sdbh.json e' COMPLETO: 54 ep, l'ultimo (2024-08-08) e' l'arco di
      **Majin Ozotto** (mangia pianeti/persone/dei) e finisce su un
      cliffhanger — Toei non ha fatto altro. Da fare: sottotitolo esplicito
      "spin-off, fuori dalla cronologia" + scheda a fine catena che rimanda a
      "Dragon Ball" (blocco Super) per la trasformazione in Divino.
- [ ] **G — TV in diretta vuota** (lista IPTV non arriva sul PC) +
      **nomi russi a caratteri rotti** (encoding in `russo`).
- [ ] **DOC — ogni saga documentata bene** (richiesta 10/09, "sono le regole,
      per QUALSIASI saga non solo Goku"): ogni PERCORSO deve spiegare
      COME (ordine, canone/non canone), DOVE (fonti/servizi), COSA (archi),
      QUANDO (anni, messa in onda IT). Audit di tutti i ~40 percorsi + serie
      runtime.
- [ ] **TRONCATURA ITALIA** (richiesta 10/09): per QUALSIASI serie, mettere
      IN EVIDENZA il punto dove la trasmissione italiana fu troncata, cosi'
      l'utente sa da dove non ha mai visto e non riparte da zero. Serve un
      dato per-serie (es. `troncata_ita: <ep>` in SERIE) + una scheda/segno
      visibile sulla catena alla tappa giusta. Alcune note gia' esistono
      (ss "fermati al 52 due volte", ken "spezzati", dbz_kai): renderle
      sistematiche e visibili, non sepolte nella nota.

## #3 RIPRODUZIONE — provata e RIPARATA (10/09)
Aperto "Dragon Ball, episodio 1" dalla Videoteca -> partiva **Dragon Ball GT
episodio 1** (GT contiene "dragon"+"ball" -> copertura 100% -> pareggio con la
serie giusta, e vinceva GT).
FIX in `resources/canale/lesaghe.py` (iniettato in s4me/channels/):
- `_titoli_da_provare` ora cerca il nome della SERIE (`SERIE[id]["titolo"]`,
  es. "Dragon Ball GT") prima di quello della saga.
- nuovo `_serie_sbagliata()` + set `MARCATORI_SERIE` (gt, z, kai, super,
  shippuden, boruto, 2003...): un risultato con un marcatore che la serie
  voluta non ha viene SCARTATO.
- ordinamento: a parita' di lingua e copertura, vince chi ha MENO parole in piu'.
Ora "Dragon Ball ep 1" apre `DragonBall_Ep_001_ITA.mp4` (Goku conosce Bulma),
audio ITA. **La fusione con s4me funziona end-to-end sul PC.**
Deployato in saghe/resources/canale + s4me/channels. Tolta la voce "db" da
`rubrica_fonti.json` (aveva in cache la fonte sbagliata).
RESTA: (a) errore non fatale `s4me[jsontools.load] launcher.py:277 makeItem`
all'avvio del findvideos - NON blocca la riproduzione, e' interno a s4me;
(b) stessa disambiguazione da controllare per naruto/sdbh (le altre voci in
rubrica) e per il percorso FILM (secondo `_quanto < COPERTURA_MINIMA` a riga ~930);
(c) thumbnail episodi VUOTI nella vista "sfoglia" benche' db.json abbia il
campo `i` - da collegare.

## PROVE EPISODI RANDOM (10/09) — 4 su 5 OK
- Dragon Ball ep 1  -> `DragonBall_Ep_001_ITA.mp4`  OK (audio ITA, serie giusta)
- Naruto ep 1       -> `Naruto_Ep_001_ITA.mp4`      OK
- One Piece ep 1    -> `OnePiece_Ep_001_ITA.mp4`    OK
- Cavalieri Zodiaco -> `SaintSeiya_Ep_001_ITA.mp4`  OK
- Mazinga Z ep 1    -> `MazingerZ_Ep_01_ITA.mp4`    OK
- **Dragon Ball Z tappa 300 (= dbz ep 147)  -> FALLISCE.**
  animeworld trova "Dragon Ball Z (ITA)" ma l'entry ha un `context`
  **[B]Renumbering[/B] / autorenumber**: il sito spezza DBZ in parti e non
  numera 1-291. `_episodio_giusto(episodi, 147)` non trova la 147.
  -> DA FARE: gestire il renumbering di s4me, o una mappa offset per-serie
  (quali entry di animeworld coprono quali episodi). Colpisce gli episodi
  PROFONDI di serie lunghe divise dal sito; l'inizio delle saghe va.

## PLAYBACK EPISODI PROFONDI — s4me e' ROTTO a monte (10/09)
Provati Naruto 150, DBZ 147, One Piece 200: **tutti NIENTE**. Nel log s4me:
- `aniplay.search` -> `AttributeError: HTTPResponse has no attribute 'json'`
  (bug nel CODICE di s4me, 12x)
- `animeunity.episodios` -> `JSONDecodeError` (il sito ha cambiato)
- `animeworld` -> `check()` da' i pulsanti del player, non gli episodi
- server **voe** -> dialogo INGLESE "Unexpected error on server voe"
  (hardcoded in s4me/platformcode) - l'utente l'ha visto e non lo vuole
- `cb01anime` -> WebErrorException
Cioe' quasi tutti gli scraper anime di s4me non funzionano su questa
versione. **Non e' la nostra fusione**: e' s4me da aggiornare/riparare.
L'INIZIO delle saghe (episodio 1) va (5/5) perche' becca una fonte buona
prima di arrivare a quelle rotte.
- Fix gia' messi in lesaghe.py (utili comunque): serie giusta
  (`_serie_sbagliata`), prova tutti i candidati, `check` per ultimo.
DA DECIDERE:
  A) aggiornare/sostituire s4me (fix vero);
  B) i contenuti su abbonamento (DBZ = Anime Generation/Amazon) - sul box
     dove Amazon c'e', DBZ 147 funzionerebbe; il PC non ha Amazon;
  C) far inghiottire alla nostra `lesaghe.py` i dialoghi inglesi di s4me e
     mostrare SEMPRE la card italiana "non trovato" (requisito utente:
     "sempre in italiano o autorisolvibile").

## C — RETE DI SICUREZZA + LINGUA (10/09) — FATTO
- **CAUSA VERA dei testi inglesi: Kodi PC era in `en_gb`.** Installato
  `resource.language.it_it` (11.0.109, da mirrors.kodi.tv, in `addons/`),
  `locale.language=resource.language.it_it`, `locale.country=Italia (24h)`.
  Verificato: "Filmati", "Ordina per: Nome", "Opzioni", orologio 24h.
  Ora i dialoghi di s4me ("Errore inaspettato sul server %s" ecc.) sono in
  italiano - la traduzione c'era gia' in it_it/strings.po, mancava la lingua.
- **`_pota_server()`** in lesaghe.py: i server traballanti (voe, streamsb,
  fembed...) vanno IN FONDO, quelli buoni (streamtape, dood, mixdrop,
  vidguard, streamwish...) IN CIMA. L'autoplay prova prima i buoni -> meno
  dialoghi d'errore. Applicato ai 3 `return server` di findvideos.
- **RIPIEGO YOUTUBE per QUALSIASI saga** (richiesta utente: "su YouTube ci
  sono episodi di Dragon Ball sottotitolati, mettili nelle mie saghe con
  locandina"): a fine `findvideos`, se nessun sito ha l'episodio, si
  aggiunge la voce "Cerca l'episodio N su YouTube" con la LOCANDINA della
  saga (`scheda(serie_id)["poster"]`), che apre la ricerca YouTube gia'
  pronta ("<serie> episodio N sub ita"). Vale anche per le saghe future.
  Compilato e deployato; playback DB ep1 ancora OK dopo le modifiche.
- RESTA: A (aggiornare/riparare s4me - gli scraper anime sono rotti) resta
  il problema vero per gli episodi profondi.

## SCHEDE EPISODI — 11 delle 13 vuote RIEMPITE (10/09)
Da `scratchpad/build13.py` (TMDb, it-IT). Riempite e deployate su Kodi PC:
naruto_shippuden(500), one_piece(1181), goldrake(74), grande_mazinga(56),
jeeg(46), gundam0079(43), zeta_gundam(50), gundam_zz(47), harlock(42),
galaxy999(113), lamu(218). Titoli + immagini OK; trame IT parziali su
zeta/zz/galaxy (TMDb non le ha in italiano).
**RESTANO 7 disallineate:**
- naruto (id TMDb 20614 e' SBAGLIATO - non e' Naruto), boruto (72804 e' un
  programma coreano): trovare gli id giusti. Riazzerate a vuoto per ora.
- lupin1/2/3: su TMDb sono UN solo show (31572, 300 ep in tante stagioni);
  vanno divisi per range di stagione con `offset`, come ken1/ken2 in
  costruisci-schede.py.
- ken1 (dich. 109, file 152) e bleach (dich. 366, file 416): il file ha piu'
  del dichiarato - riconciliare (aggiornare il conteggio in SERIE o tagliare).

## SCHEDE + G + TRONCATURA (10/09, secondo giro)
- **SCHEDE: 0 disallineate su 105.** Corretti: naruto (id 46260, non 20614),
  boruto (id 70881, non 72804), lupin1/2/3 (un solo show TMDb 31572 -
  stagioni 1/2/3), ken1 (S1-4 = 109), ken2 (S5-6 = 43, offset), bleach
  (solo S1 = 366; la S2 e' TYBW che ha la sua scheda). Script:
  scratchpad/build13.py + build7.py. Deployate 19 schede su Kodi PC.
- **G - non erano bug:**
  - nomi russi: `russo.py` e' UTF-8 VALIDO e byte-identico DEV/PC. Il
    "carattere rotto" era un artefatto del MIO harness JSON-RPC, non
    dell'addon. A schermo rende.
  - TV in diretta vuota sul PC: ATTESO. L'addon legge `PVR.GetChannels`;
    sul PC non c'e' backend IPTV/PVR, sui box c'e' (IPTV Simple + m3u).
    Per testarla sul PC servirebbe installare pvr.iptvsimple.
- **TRONCATURA ITALIANA: TAGLI da 8 a 16 serie.** Aggiunte goldrake,
  grande_mazinga, gt, naruto, naruto_shippuden(verificato=False),
  boruto(False), lupin2, lamu. Le ~90 restanti sono quasi tutte anime
  moderni andati in onda completi (nessun taglio). NON invento fatti:
  le classiche mancanti (Lady Oscar, Sampei, Candy Candy, Georgie...) si
  aggiungono confermando con l'utente.
- **DOC: spiegazione riscritta (come/dove/cosa/quando) per ken, holly,
  mazinga.** Restano ~gli altri percorsi anime da rivedere (i m_* e tr_*
  vanno bene corti).

## RENUMBER / EPISODI PROFONDI — mitigato, non risolto (10/09)
Aggiunto `_pare_una_stagione()`: `_episodi_di` scende SOLO in voci che
sembrano stagioni, non nei bottoni del player (parole: server, alternativo,
voe, streamtape...). Cosi' non resta appeso 90s su Naruto 150 / DBZ 147:
fallisce in fretta -> ripiego YouTube. Il dialogo "Errore inaspettato sul
server voe" ORA E' IN ITALIANO (era il Kodi in inglese). Ma appare ancora
quando una fonte ha solo server rotti: e' s4me/sito, non nostro.
`rubrica_fonti.json` svuotato (aveva in cache toonitalia per db/dbz/naruto).
Verificato: Dragon Ball ep 1 parte ancora (`DragonBall_Ep_001_ITA.mp4`).
**Conclusione: gli scraper s4me sono inaffidabili a monte; le difese
(italiano, ordine server, ripiego YouTube, fail veloce) sono tutte in
posto. Non si fa di meglio dal nostro strato.**

## REFRESH WIDGET HOME — FATTO (10/09)
`skin.saghe/xml/Home.xml`: aggiunti `<onload>Container(<id>).Refresh</onload>`
per 5010/5019/5011/5013/5014/5015/5016/5017/5018 nel `<window>`. Ogni
ritorno alla home ricarica le righe volatili (i widget dell'add-on non
toccano la rete -> istantaneo). Verificato: aggiunta "Super GALS" dai
Consigliati -> compare in LE TUE SAGHE senza riavviare; la sezione
DOCUMENTARI ristrutturata e la riga "NOVITA' DAI TUOI SITI" si vedono.
`plugin.video.saghe` gia' usava `endOfDirectory(cacheToDisc=False)` per i
widget, mancava solo il trigger lato skin.
NOTA: la SORGENTE di skin.saghe non e' in Antigravity - solo il deployato
in `AppData/.../skin.saghe/` e la copia in `tmp_addon_pull/20260910/box_skin/`
(ho aggiornato entrambi). Per il pacchetto finale serve una sorgente unica.

## PROSSIMO EPISODIO AUTOMATICO — FATTO (10/09)
Il conto alla rovescia stile Netflix ESISTEVA gia' (`service.py`
`_attacca_il_prossimo`), ma partiva solo per i file locali (`azione=riproduci`):
per la fusione s4me non si apriva nessuna "sessione", quindi il servizio non
sapeva cosa stesse partendo.
FIX (4 file):
- `main.py indirizzo_s4me(t, pid)`: l'URL s4me ora porta `&percorso=&idx=`
  (la tappa della catena). `metti_tappa` lo passa; `riproduci()` per le
  fonti s4me ora fa `PlayMedia` invece di `Container.Update` (il conto alla
  rovescia deve FAR PARTIRE il video, non aprire una cartella).
- `lesaghe.py _apri_sessione_nostra(item)`: quando `findvideos` risolve i
  server, scrive `sessione.json` (percorso/idx/dentro_kodi) - lo stesso
  file di `progresso.apri_sessione`.
- `progresso.py marca_visto_play()` + `service.py`: il servizio distingue
  "finito" da "s4me ci sta ancora provando" (grazia 90s prima di rinunciare
  se il video non e' mai partito, invece di 3s).
Verificato: aprendo DB ep1 via s4me la `sessione.json` si crea con
`visto_play:true` e il video parte. Il conto alla rovescia -> prossimo
episodio ora scatta anche sulla fusione. `autoplay` di s4me e' gia' `true`.

## SALTA SIGLA — non fatto (opzionale)
Kodi non ha skip-intro nativo; gli stream s4me non hanno i capitoli.
Servirebbe: setting `salta_sigla` + `intro_sec` per-serie (o globale ~90s),
e in `service.py` onAVStarted, se sessione Le Saghe attiva e siamo nei
primi ~10s, seek a `intro_sec`. Rischio: saltare un "riassunto puntata
precedente". Molti fan degli anime NON saltano le sigle: da decidere se
vale la pena.

## "SU NETFLIX ORA" — FATTO il nucleo (10/09)
Nuovo `resources/lib/netflix.py`: TMDb watch-providers (Netflix id 8,
region IT) via `/discover/tv`. Menu `azione=netflix` (voce nel menu
principale, dopo "Consigliati"): SEZIONI (Anime / Serie TV) -> GENERI ->
TITOLI su Netflix Italia adesso, dal piu' visto, con cache di 1 giorno.
Scegliendo un titolo: `consigli.aggiungi(tmdb_id, tipo=)` (ora accetta
`tipo`), che lo mette in `serie_mie.json` con `tipo` e scarica la scheda
episodi. `catalogo.applica_serie_nuove` ora ROUTA per tipo: anime ->
gruppo "mie" (reparto Cartoni), serietv -> gruppo "mie_serietv" (reparto
Serie TV). Poi ricerca/riproduzione = quelle di sempre (s4me multi-fonte +
ripiego abbonamento/YouTube).
Verificato: `netflix&sez=anime&g=10759` da' 40 titoli reali (Frieren,
JJK, SPY×FAMILY...); aggiunta SPY×FAMILY -> compare in widget saghe;
aggiunta Stranger Things con tipo=serietv -> compare in widget serietv.
(Le serie di test le ho rimosse da serie_mie.json, restano Monster Hunter
e Ranma dell'utente.)
FASE 2 (non fatta): **Film su Netflix** per genere + **Documentari su
Netflix** (serve estendere le strutture film-list / scaffali, modello dati
diverso). E le **righe nella home** della skin (ora e' solo una voce di
menu, non una linea con locandine in Home.xml).

## NUOVE RICHIESTE UTENTE (10/09) — DA FARE
1. ~~BUG "Consigliati per te" -> percorso invisibile~~ FATTO (era il refresh
   dei widget, sopra). MA nota storica:
   via plugin le serie aggiunte (Monster Hunter, Ranma) SI VEDONO in
   `?azione=widget&che=saghe` (51 voci). Il problema e' che **i widget
   della home di skin.saghe NON si aggiornano** senza riavvio: Kodi mette
   in cache il listato plugin del widget. Stesso motivo per cui la sezione
   "MOTORI, GARAGE E RESTAURI" e le altre modifiche "non si vedono in
   Videoteca". FIX: in `skin.saghe/xml/Home.xml`, far rinfrescare i
   `<control type="list">` (Container.Refresh su onload / param che cambia).
2. **Righe "su Netflix ora"**: anime / film per genere / documentari /
   serie TV attualmente su Netflix (TMDb watch-providers, region IT).
   Scegliendone una viene aggiunta AUTO nella sezione giusta (documentari
   -> documentari, serie -> serietv, film -> film) col percorso creato e
   reso visibile, stessa categoria e genere. Poi ricerca/riproduzione
   uguale al resto (multi-fonte).
3. **Passa all'episodio successivo in automatico** + **salta intro** se
   possibile (Kodi ha "Playlist" / il "prossimo episodio" per le serie in
   videoteca; skip-intro = inputstream/segnali capitolo).
4. Skin "come Netflix di oggi" (da chiarire cosa intende).

## Regole
- Kodi PC SEMPRE in finestra (`togglefullscreen` dopo l'avvio). MAI `GUI.SetFullscreen` (crash).
- Niente commit finche' l'utente non ha visto e approvato. Deploy sui 2 apparecchi solo a fine lavoro.
