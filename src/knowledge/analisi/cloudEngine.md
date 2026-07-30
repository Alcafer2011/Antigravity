# cloudEngine.js — ANALISI RIGA PER RIGA

MOTORE CLOUD multi-provider (tutti OpenAI-compat). Canali: `uncensored` (senza
filtri via OpenRouter :free, hermes-3, venice) e `normal` (HF, Groq, OpenRouter...).
Classe `CloudEngine`, esportata. Costruttore (37-74): carica env (rootDir = home),
budget da `HF_MONTHLY_BUDGET_USD` (default 0.10), costo per Mtoken 0.20$, costruisce
provider attivi (quelli con chiave in .env), legge usage/catalog/rate/cooldown.

## Provider attivi (76-105)
`_buildProviders()`: per ogni def del registro, se `env[def.env]` esiste → provider
ATTIVO. Se `needsEnv` (es. Cloudflare: ACCOUNT nell'URL) manca → provider NON attivato
(log). Così basta incollare una chiave nel .env: host/endpoint già nel registro.

## Gestione chiavi (113-152)
- `listKnownProviders()` / `freeSuggestions()`: per UI cacciatore.
- `detectKey(key)`: riconosce provider dal prefisso della chiave.
- `saveKey(key, providerId)`: SCRIVE nel `.env` (rootDir/.env = `C:\Users\infoa\.env`!)
  e ricarica i provider a caldo. ⚠️ Scrive su `C:\Users\infoa\.env`, NON src\.env.

## Catalogo dinamico (176-353)
`discover(force)`: unisce i modelli di tutti i provider attivi (TTL 10 min).
Discovery per provider: `_discoverHF`, `_discoverOpenRouter`, `_discoverGroq`,
`_discoverGoogle`, `_discoverCloudflare`, `_discoverGeneric` (cerebras/nvidia/sambanova/
mistral/github). Filtra embedding/tts/vision. `UNCENSORED_RX` riconosce modelli senza
filtri dal nome. `isFreeModel` (396-403): UNICA fonte di verità gratis/a-pagamento
(OpenRouter solo :free; Nous sempre free; HF/a-consumo = pagamento).

## Inferenza (436-517)
- `chat(value, messages, {stream})`: `value = "provider::modelId"`. Streaming SSE se
  onToken. Header Bearer. OpenRouter: HTTP-Referer/X-Title. Kaggle: ngrok-skip.
- `chatTools(value, messages, tools)`: tool-calling OpenAI (non streaming).

## Barra utilizzo (529-580)
`_record`/`getUsage`: token/request per mese, costo stimato SOLO per provider a consumo
(HF). `exhausted()` se budget superato. `isQuotaError` riconosce 402/429/quota.

## Rate-limit anti-fantasma (587-665)
`_noteRate` legge header `x-ratelimit-*` della risposta (Cerebras 5/min). `_providerBusy`
/`_busyForMs`: se il provider è saturo al minuto → pausa ~60s, NON cooldown 30 min.
Così una raffica di tool-call non "spegne" una corsia sana.

## Failover intelligente (806-1150) — LA POTENZA DI FUOCO
- `SEED_MODELS()` (816-852): modelli-seme gratuiti grossi (≥32B) con tool-calling,
  rete di sicurezza se la discovery non ha girato. ★ Kaggle abliterated 14B/32B (corsia
  prioritaria utente), Cerebras gpt-oss-120b, Cloudflare gpt-oss-120b, GitHub gpt-4.1-mini,
  Groq llama-3.3-70b, SambaNova DeepSeek-V3.2 (671B uncensored!).
- `resilientCandidates(o)` (906-1006): lista ordinata per failover. Set FREE = provider
  gratuiti (kaggle/groq/google/nvidia/sambanova/cerebras/mistral/alibaba/cloudflare/
  github/...). OpenRouter/Hyperbolic FUORI se non abilitati (OPENROUTER_ENABLE=1).
  `provRank`: affidabilità (kaggle 20, groq 10, cerebras 9, sambanova 8, cloudflare 7,
  github 6... nvidia/google 1). Score: cooldown -1000, reasoning -60, preferred(qwen/
  deepseek/hermes)+45, uncensored +40, coder +40, taglia con tetto /4, provRank ×10.
  Filtro taglia ≥ minB (default 32) ECCETTO Kaggle (14B resta default veloce).
- `_classifyAndCooldown` (1022-1065): distingue 429-al-minuto (pausa 60s, NON quota!)
  da credito/quota finita (45 min) da auth morta (6h, salta tutto il provider) da
  modello invalido (rimosso dal catalogo, 6h) da saturo/busy (20 min) da errore/timeout (3 min).
- `chatToolsResilient` / `chatResilient` (1071-1150): 3 passi — (1) corsie sane non
  saturate, (2) ignora cooldown ma non i saturi-al-minuto, (3) ANTI "restare a piedi":
  aspetta il primo che si libera (max 70s) e riprova. Poi auto-azzeramento cooldown transitori.

## Dipendenze
- providerRegistry (registro provider), fs/path/https nativi.

## Rischi / note
- `saveKey` scrive su `C:\Users\infoa\.env` (rootDir=home). Corretto: è il .env che conta.
- I provider a consumo (HF/OpenAI/DeepSeek) sono esclusi dal failover gratuito.
- OpenRouter/Hyperbolic disattivati di default (passati a pagamento/credito zero).
- La "potenza di fuoco" gratuita reale = groq/cerebras/nvidia/sambanova/google/mistral/
  cloudflare/github/kaggle(abliterated) + venice(uncensored) + nous(:free).
- Kaggle abliterated è la corsia uncensored principale (GPU). Venice = uncensored cloud.
- I modelli-seme vanno aggiornati se ritirati (la discovery live copre, ma i semi restano
  come rete di sicurezza).
