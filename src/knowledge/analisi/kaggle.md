# Gruppo Kaggle — ANALISI RIGA PER RIGA

Tre file per i modelli abliterated su GPU Kaggle via ngrok.

## kaggleWaker.js (190 righe)
Accende il notebook Kaggle ON-DEMAND (non tenerlo sempre acceso = spreco quota 30h/sett).
- `KAGGLE_HOST` (26-27): ngrok fisso `paving-preschool-facelift.ngrok-free.dev` (da
  providerRegistry id "kaggle"). `NB_SLUG` = alcafer2011/notebook39aa15083b. Due notebook:
  14B (Qwen2.5-Coder-14B) e 30B (Qwen3-Coder-30B-MoE).
- `isUp` (46-55): probe /v1/models (header ngrok-skip).
- `envVar`/`token` (57-66): legge KAGGLE_API_TOKEN da `../.env` (home) o env. ⚠️ .env
  HOME, non src\.env.
- `pushKernel` (69-81): `kaggle kernels push` (avvia run). `ensureUp` (89-119): se già up
  → ok; altrimenti push + aspetta maxWaitMs (default 15min) che l'endpoint risponda.
  Guardia `_waking` (una sola accensione alla volta). `shutdown` (132-150): via
  KAGGLE_SHUTDOWN_URL (worker Cloudflare) o link manuale. `quota` (155-188): ore GPU usate/
  rimanenti via `kaggle quota_view` (cache 5min).
- ⚠️ Regola 2026-07-26 (hermesClient): Kaggle NON si accende più da solo, SOLO se il
  modello è kaggle::. Prima partiva sempre → sprecava quota.

## kaggleEngine.js (101 righe)
Motore inferenza OpenAI-compat verso Kaggle (ngrok). Usato come anello failover
(localOrchestrator catena: modello scelto → cloud → kaggle::30b → locale).
- `MODELS` (19-22): 14b = Qwen2.5-Coder-14B abliterated, 30b = Qwen3-Coder-30B-A3B
  abliterated. Override da .env (KAGGLE_MODEL_14B/30B).
- `chatTools`/`chat` (66-96): POST /v1/chat/completions (timeout 180s). NESSUNA chiave
  (notebook privato). Se notebook spento → fallisce veloce → failover passa oltre.
- ⚠️ NESSUN auto-accensione: se spento, l'inferenza fallisce e basta (l'accensione resta
  solo per scelta esplicita kaggle:: nel canale cloud).

## kaggleToolProxy.js (171 righe)
Proxy OpenAI-compat DAVANTI a Kaggle (porta 8791) che traduce le tool-call TESTUALI
dei modelli abliterated nel formato `tool_calls` nativo che Hermes si aspetta.
- `extractToolCall` (36-65): riconosce ```json / <tools> e forme {name,args}/{action}/
  {tool}/{function:{…}}. Restituisce {name, args}.
- `translate` (68-87): se msg.tool_calls assente ma la tool-call è nel content → la
  sposta in tool_calls nativi, content=null, finish_reason=tool_calls.
- `forward` (105-148): rimanda a ngrok, con tool forza non-stream upstream (serve risposta
  completa per tradurre), poi risponde al client (SSE se stream, JSON altrimenti).
- `ensureRunning` (154-169): avvia server su 127.0.0.1:8791 (idempotente; se porta occupata
  assume già attivo). Hermes punta a :8791 invece che a ngrok.
- ⚠️ Serve SOLO con Hermes (che è un pacchetto chiuso). nativeAgent ha già il fix lato client.

## Dipendenze
- kaggleWaker: https, child_process, fs, path, providerRegistry.
- kaggleEngine: https, kaggleWaker.
- kaggleToolProxy: http, https.

## Rischi / note
- Kaggle richiede KAGGLE_API_TOKEN nel .env (home) per accendere il notebook.
- Notebook su ngrok dominio fisso: se il dominio cambia, aggiorna providerRegistry + kaggleWaker.
- kaggleToolProxy porta 8791: se occupata da altro, il proxy non parte (assume già attivo).
- Non accendere Kaggle a caso: brucia quota GPU (30h/sett).
