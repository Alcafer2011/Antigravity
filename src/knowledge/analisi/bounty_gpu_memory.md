# bountyHunter.js + gpuPlatforms.js + learningMemory.js — ANALISI RIGA PER RIGA

## bountyHunter.js (323 righe)
"Cacciatore di taglie" VERO: va a caccia di provider LLM gratuiti e propone SOLO le novità.
- `SOURCES` (30-58): 3 fonti — cheahjs/free-llm-api-resources (README), mnfst/awesome-free-llm-apis (README), OpenRouter /api/v1/models (JSON, formato json-or). Cache 24h (CACHE_TTL).
- `UNC_RE` (61): regex nomi/alias modelli senza filtri (abliterated/dolphin/magnum/rok/-ice-/gryphe/kunoichi/nyxn/erot/roleplay...).
- `knownAliases` (66-83): mappa alias normalizzati → id registro (per riconoscere doppioni e provider già in providerRegistry). Alias manuali (google→gemini, hf→huggingface, ecc.).
- `norm` (84-87): normalizza (lowercase, togli apostrofi/punteggiatura).
- `_getText` (99-120): HTTPS GET con 1 redirect, timeout 15s.
- `_parseList` (129-180): parser README — sezioni "## Free Providers"/"## Provider APIs" = buoni; "## Trial credits" = scartati; "### [Nome](url)" = provider; tabelle HTML <tr><td> = modelli+limiti.
- `_parseOrModels` (187-209): parser JSON OpenRouter — modelli con pricing.prompt=="0" && completion=="0" = free; marca uncensored per nome (UNC_RE).
- `hunt` (217-261): usa cache se < 24h; altrimenti scarica tutte le fonti, FUSIONE per nome (byName: conta quante fonti citano, tiene record più ricco, "free" vince su "trial"), salva cache, chiama _decorate. Se rete giù → cache vecchia (stale).
- `_isUnc` (268-274): riconosce uncensored da nome o id noto (venice/arliai/featherless/hf/nvidia/kaggle/ollama...).
- `_decorate` (284-320): divide in `nuovi` (non configurati, kind!=trial) / `gia` (configurati) / `trial` (esclusi di default). `o.uncensored` → SOLO senza filtri. `confermato` = ≥2 fonti. Ordina: confermati + con modelli prima. `includeTrial` aggiunge i trial.
- ⚠️ Dipende da GITHUB_TOKEN? NO (legge raw.githubusercontent.com pubblico). Ma OpenRouter /api/v1/models è pubblico. Nessuna chiave richiesta.

## gpuPlatforms.js (246 righe)
Catalogo di confronto piattaforme GPU (tipo Kaggle) per ospitare i TUOI modelli abliterated.
- `PLATFORMS` (24-224): kaggle, colab, modal, runpod, huggingface, lightning, paperspace, vastai, salad. Campi: id, name, kind(free|paid|freemium), freeGpu, alwaysOn, uncensoredOk, remote, costo, pros[], cons[], howto, note.
- ⚠️ Solo Kaggle ha `remote:true` (kaggleWaker accende/spegne). Le ALTRE (modal/runpod/vast/salad/lightning/paperspace) sono `remote:false` — "da cablare" con token nel .env (NON ancora implementato).
- `uncensoredOk`:false per colab/huggingface (termini vietano abliterated); true per kaggle/modal/runpod/vast/salad/lightning/paperspace (tuoi container).
- `summary` (230-244): stato Kaggle (riusa kaggleWaker: host/up/quota) + metadati altre piattaforme.

## learningMemory.js (80 righe)
Memoria EVOLUTIVA: accumula lezioni apprese, le reinietta nel prompt.
- `DIR` = ~/.antigravity, `FILE` = learning.json. `MAX` = 300 lezioni.
- `remember` (37-54): salva lezione {text, tags, scope, at, uses}. Deduplica per testo simile; se esiste incrementa uses; se >MAX butta le meno usate/vecchie.
- `recall` (61-75): richiama lezioni rilevanti per il contesto (scope/tag nel prompt). Global +5, scope match +50, tag match +20. Ordina per score, ritorna testo ("• ...").
- `all`/`clear` (77-78): tutte / svuota.
- ⚠️ Storage in ~/.antigravity/learning.json (indipendente dal progetto). Memoria NON critica: se non salva, prosegue.

## Dipendenze
- bountyHunter: https, fs, path, providerRegistry.
- gpuPlatforms: nessuna (dati statici + kaggleWaker per summary).
- learningMemory: fs, os, path.

## Rischi / note
- bountyHunter: cache su disco (bounty-hunt.json in cwd di chi lo chiama). Le fonti GitHub possono cambiare markup → parser fragile (ma ha 3 fonti + fallback cache).
- gpuPlatforms: SOLO Kaggle è cablato (remote). Le altre sono informative, NON funzionanti (manca token).
- learningMemory: file in home, NON in src\. Se cancelli ~/.antigravity, perdi la memoria evolutiva.
