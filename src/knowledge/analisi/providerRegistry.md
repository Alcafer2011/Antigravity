# providerRegistry.js — ANALISI RIGA PER RIGA

CATALOGO dei provider LLM (OpenAI-compat) con rilevamento automatico dalla forma
della chiave. L'utente incolla SOLO la chiave: endpoint/host/env si auto-compilano.
Esporta `{ PROVIDERS, detectProvider, publicView, byId, byEnv, all, freeSuggestions,
FREE_PROVIDERS, freeProviders }`.

## PROVIDERS (30-92)
Array di voci. Ogni voce: `id, label, env, host, chatPath, modelsPath, detect (regex
chiave), signup (URL chiave), free, billed, keyFmt, note, needsEnv, uncensored`.
- GRATIS attivi: openrouter (free:false, ora a pagamento), groq, cerebras, nvidia,
  sambanova, hf (billed:true), google, mistral, hyperbolic (free:false, credito 0),
  cloudflare (needsEnv CLOUDFLARE_ACCOUNT_ID), github, novita, chutes, glhf,
  ollama-cloud, kaggle (KAGGLE_KEY=ollama fittizia), alibaba, kilo (KILO_KEY=none),
  opencode (OPENCODE_ZEN_KEY=none), venice (AGGIUNTO oggi: uncensored, VENICE_API_KEY),
  arliai (uncensored), deepinfra (billed), featherless (uncensored, billed), cloudrift.
- A PAGAMENTO: openai, deepseek, anthropic, xai, perplexity, fireworks, together.
- NOTA: Venice aggiunto oggi (riga 71) con `uncensored:true` + VENICE_API_KEY nel .env.
  Featherless/ArliAI marcati uncensored ma billed (esclusi dal failover gratuito).

## detectProvider (99-144)
Rileva provider da chiave incollata. STRONG (104-127): prefissi univoci (sk-or-v1→
openrouter, gsk_→groq, csk_→cerebras, nvapi_→nvidia, xai_→xai, pplx_→perplexity, fw_→
fireworks, glhf_→glhf, cpk_→chutes, rc_→featherless, cf(at|ut)_→cloudflare, ghp_/
github_pat_→github, eyJ→hyperbolic, AIza/AQ.→google, hex32.→ollama-cloud).
AMBIGUI (132-143): `sk-` generico → [deepseek, openai, alibaba]; `sk_` → novita;
hex64 → together; hex32 → [mistral, together]. Ritorna `{best, candidates, ambiguous}`.

## FREE_PROVIDERS (174-262) — "Cacciatore di taglie"
Lista CURATA (non discovery) di provider/modelli gratuiti verificati. Ogni voce:
`id, name, keyUrl (dove prendere la chiave, MAI esporre chiavi), freeModels, note,
uncensored`. Inclusi i nuovi gateway free (kilo, opencode), arliai/deepinfra/
featherless/cloudrift (uncensored dove indicato). RIMOSSE (256-261): nous (chiede
soldi), hf-uncensored/ollama-uncensored (non sono API, girano in locale su T1000 4GB).
Cohere/Vercel: suggeriti ma NON nel failover (endpoint non OpenAI-compat standard).

## Funzioni (146-272)
- publicView(p): vista senza regex (per UI).
- byId/byEnv/all/freeSuggestions: lookup.
- freeProviders(type): filtra `uncensored` se type==="uncensored".

## Dipendenze
- Nessuna (solo dati + regex). Usato da cloudEngine e mobileServer.

## Rischi / note
- Venice è nel registro e nel .env (VENICE_API_KEY) → attivo e uncensored (verificato).
- OpenRouter/Hyperbolic disattivati dal failover gratuito (a pagamento/credito 0).
- Cloudflare richiede CLOUDFLARE_ACCOUNT_ID oltre la chiave (needsEnv).
- I provider a consumo (hf billed, openai, deepseek, ecc.) esclusi dal failover free.
- detectProvider è la chiave per l'auto-compilazione: incolli la chiave, l'app sa dove metterla.
