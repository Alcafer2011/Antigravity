# nousClient.js + hermesClient.js + hermesAcp.js — ANALISI RIGA PER RIGA

Provider secondari: Nous (modelli :free via Hermes auth), Hermes CLI (lavoratore
autonomo), Hermes ACP (protocollo, disabilitato per lo streaming).

## nousClient.js (315 righe)
Integrazione DIRETTA con Nous Portal (opzione B). Modello SINGLE-WRITER (concordato
con Hermes): NON ruota il refresh_token (altrimenti slogga Hermes), legge access_token
da `auth.json` di Hermes (read-only). Se scaduto → NUDGE a Hermes (esegue la sua
`resolve_nous_runtime_credentials` nel venv Python) che rinnova e persiste. Lock file
cooperativo (AUTH_LOCK) per serializzare con Hermes. FREE_MODELS (44-49): solo :free
verificati (poolside/laguna-*, tencent/hy3, stepfun/step-3.7-flash). chat/chatTools
usano access_token Bearer. Modelli reasoning: content null → usa reasoning come fallback.
⚠️ Se tocchi l'auth di Nous, NON reintrodurre un refresh OAuth diretto: era la causa del
logout di Hermes (commento riga 191-199).

## hermesClient.js (278 righe)
Usa Hermes Agent come LAVORATORE via CLI `hermes.exe -z "task" --continue antigravity`.
NON ACP (streaming inaffidabile per tool-calling Ollama). Sessione fissa "antigravity"
→ Hermes ricorda i lavori. Cwd = HOME hermes. NOUS_FREE (56-61): SOLO i 4 modelli :free
di Nous (regola utente 2026-07-26: niente modelli a pagamento nel menu). getModelChoices
legge config.yaml + provider_models_cache.json (no rete). delegate(task) (194-239):
- NON accende più Kaggle da solo (2026-07-26): solo se il modello è Kaggle.
- 1° tentativo col modello scelto; se muto (stdout vuoto) → ripiego sul default Hermes
  (nous/hy3). Timeout 10 min. AUTO-ALLOW non passato (Hermes con sue conferme).
⚠️ Kaggle si accende SOLO se modelo=kaggle (riga 206). Prima partiva sempre.

## hermesAcp.js (325 righe)
Pilota Hermes via ACP (JSON-RPC 2.0 su stdio). `findHermesAcp` cerca hermes-acp.exe o
python -m acp_adapter. start() → initialize + session/new. prompt(text) → session/prompt.
Gestisce session/update (message/thought/tool/plan) e session/request_permission +
fs/read_text_file + fs/write_text_file (gate scrittura per policy). _decidePermission:
read-only (letture ok, mutazioni negate), auto-allow (sempre), ask-writes (letture auto,
mutazioni chiedono).
⚠️ DISABILITATO in locale: il commento in hermesClient spiega che ACP forza streaming
verso Ollama e il tool-calling in streaming è inaffidabile. Usato solo come riferimento.

## Dipendenze
- nousClient: fs/os/path/https/http/url/child_process. Condivide auth.json con Hermes.
- hermesClient: child_process, path, os, fs, kaggleToolProxy, kaggleWaker.
- hermesAcp: child_process, path, os, fs.

## Rischi / note
- Nous dipende da Hermes loggato (auth.json). Se Hermes non è loggato → Nous non usa.
- hermesClient richiede hermes.exe nel venv (Hermes installato).
- Modelli Hermes nel menu: SOLO :free (no pagamento, regola utente).
- hermesAcp è codice di riferimento, non usato attivamente (streaming issue).
