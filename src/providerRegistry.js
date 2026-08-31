"use strict";

/**
 * providerRegistry — catalogo dei provider LLM (OpenAI-compatibili) con
 * RILEVAMENTO AUTOMATICO dalla forma della chiave. L'utente incolla SOLO la
 * chiave: endpoint (host/base_url), nome variabile .env e altro si auto-compilano.
 *
 * Ogni voce:
 *   id        identificatore interno (usato come "id::modello")
 *   label     nome leggibile
 *   env       nome variabile in .env
 *   host      host HTTPS dell'endpoint OpenAI-compat
 *   chatPath  path chat completions
 *   modelsPath path per elencare i modelli (GET, OpenAI-compat) — opzionale
 *   detect    regex sul formato della chiave (per l'auto-rilevamento)
 *   signup    URL dove ottenere la chiave (reindirizzamento)
 *   free      true se ha un piano gratuito utile
 *   keyFmt    descrizione UMANA del formato della chiave (es. "sk-or-v1-...",
 *             "chiave senza prefisso fisso", "JWT (eyJ...)") — la UI la mostra
 *             così l'utente sa COSA incollare e il cacciatore può scriverlo in
 *             automatico sotto il nome del provider.
 *   note      suggerimento breve (perché è utile / cosa offre)
 *   billed    true se a consumo (costi) — la barra uso lo considera
 *
 * NB: alcune chiavi hanno prefissi condivisi (`sk-...` = OpenAI/DeepSeek/Alibaba):
 * per quelle il rilevamento propone il candidato più probabile con ambiguous=true,
 * e la UI lascia scegliere/confermare.
 */

const PROVIDERS = [
    // ---- GRATIS, ottimi per coding/reverse engineering -------------------
    // ⚠️ 2026-07-24 — i :free grossi (llama-3.3-70b, hermes-405b) sono passati a
    // PAGAMENTO: rispondono 404 "use the paid slug". Tenuto nel registro (il giorno
    // che c'è budget si riaccende con OPENROUTER_ENABLE=1) ma fuori dal failover free.
    { keyFmt: "Inizia con sk-or-v1- (es. «redacted:sk-or-v1-...»)", id: "openrouter", label: "OpenRouter (aggregatore)", env: "OPENROUTER_API_KEY", host: "openrouter.ai", chatPath: "/api/v1/chat/completions", modelsPath: "/api/v1/models", detect: /^sk-or-v1-/, signup: "https://openrouter.ai/keys", free: false, note: "⚠️ i modelli :free grossi ora sono a pagamento. Riattivabile con OPENROUTER_ENABLE=1 nel .env." },
    { keyFmt: "Inizia con gsk_ (es. gsk_xxxx)", id: "groq", label: "Groq", env: "GROQ_API_KEY", host: "api.groq.com", chatPath: "/openai/v1/chat/completions", modelsPath: "/openai/v1/models", detect: /^gsk_/, signup: "https://console.groq.com/keys", free: true, note: "Velocissimo, gratis: llama-3.3-70b, qwen, gpt-oss-120b, deepseek-distill." },
    { keyFmt: "Inizia con csk- (es. csk-xxxx)", id: "cerebras", label: "Cerebras", env: "CEREBRAS_API_KEY", host: "api.cerebras.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: /^csk-/, signup: "https://cloud.cerebras.ai/", free: true, note: "Gratis e ULTRA-veloce: llama-3.3-70b, qwen-3-32b/coder. Ottimo per l'agente." },
    { keyFmt: "Inizia con nvapi- (es. nvapi-xxxx)", id: "nvidia", label: "NVIDIA NIM", env: "NVIDIA_API_KEY", host: "integrate.api.nvidia.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: /^nvapi-/, signup: "https://build.nvidia.com/", free: true, note: "Gratis: modelli GROSSI (nemotron, deepseek, qwen-coder, llama-405b). Ottimo per RE." },
    { keyFmt: "Chiave senza prefisso fisso (50+ caratteri alfanumerici)", id: "sambanova", label: "SambaNova", env: "SAMBANOVA_API_KEY", host: "api.sambanova.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: null, signup: "https://cloud.sambanova.ai/apis", free: true, note: "Gratis e veloce: llama-3.1-405B, qwen. Chiave senza prefisso fisso." },
    { keyFmt: "Inizia con hf_ (es. hf_xxxx)", id: "hf", label: "HuggingFace", env: "HF_TOKEN", envAliases: ["HUGGINGFACE_API_KEY"], host: "router.huggingface.co", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: /^hf_/, signup: "https://huggingface.co/settings/tokens", free: true, note: "Router su molti provider; modelli abliterated/uncensored. Crediti free mensili.", billed: true },
    { keyFmt: "Inizia con AIza o AQ. (chiave Google AI Studio)", id: "google", label: "Google Gemini", env: "GOOGLE_API_KEY", envAliases: ["GEMINI_API_KEY"], host: "generativelanguage.googleapis.com", chatPath: "/v1beta/openai/chat/completions", modelsPath: "/v1beta/openai/models", detect: /^AIza/, signup: "https://aistudio.google.com/app/apikey", free: true, note: "Gratis: gemini-2.x-flash (grande contesto). Buono anche per immagini." },
    { keyFmt: "32 caratteri alfanumerici (es. abcdef0123456789abcdef0123456789)", id: "mistral", label: "Mistral", env: "MISTRAL_API_KEY", host: "api.mistral.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: /^[A-Za-z0-9]{32}$/, signup: "https://console.mistral.ai/api-keys/", free: true, note: "Piano free: mistral-large, codestral (coding). Chiave 32 caratteri." },
    // ⚠️ 2026-07-24 — verificato con la chiave reale: 402 "insufficient funds".
    // Resta selezionabile a mano, ma è FUORI dal failover gratuito (creava buchi).
    { keyFmt: "JWT (inizia con eyJ...)", id: "hyperbolic", label: "Hyperbolic", env: "HYPERBOLIC_API_KEY", host: "api.hyperbolic.xyz", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: /^eyJ/, signup: "https://app.hyperbolic.xyz/settings", free: false, note: "⚠️ credito esaurito (402). Riattivabile con HYPERBOLIC_ENABLE=1 nel .env." },
    // ★ 2026-07-24 — NUOVA CORSIA GRATIS: GitHub Models. Basta un token GitHub
    // (ghp_/github_pat_), nessuna carta: gpt-4o-mini, llama, phi, qwen, deepseek.
    // ★ 2026-07-24 — CLOUDFLARE WORKERS AI. Caso particolare: l'endpoint contiene
    // l'ID dell'account, quindi oltre alla chiave (CLOUDFLARE_API_KEY, formato
    // cfat_...) serve CLOUDFLARE_ACCOUNT_ID nel .env. Il segnaposto {ACCOUNT} viene
    // sostituito da cloudEngine._buildProviders; senza ID il provider resta spento.
    { keyFmt: "Inizia con cfat_ o cfut_ (es. cfat_xxxx)", id: "cloudflare", label: "Cloudflare Workers AI", env: "CLOUDFLARE_API_KEY", host: "api.cloudflare.com", chatPath: "/client/v4/accounts/{ACCOUNT}/ai/v1/chat/completions", modelsPath: "/client/v4/accounts/{ACCOUNT}/ai/models/search?task=Text+Generation&per_page=100", needsEnv: "CLOUDFLARE_ACCOUNT_ID", detect: /^cf(at|ut)_/, signup: "https://dash.cloudflare.com/profile/api-tokens", free: true, note: "Gratis ogni giorno sull'edge Cloudflare: gpt-oss-120b, kimi-k2, deepseek-r1-distill. Serve anche CLOUDFLARE_ACCOUNT_ID." },
    { keyFmt: "Inizia con ghp_ o github_pat_", id: "github", label: "GitHub Models", env: "GITHUB_TOKEN", host: "models.github.ai", chatPath: "/inference/chat/completions", modelsPath: "/catalog/models", models: ["openai/gpt-4o-mini"], detect: /^(ghp_|github_pat_)/, signup: "https://github.com/settings/tokens", free: true, note: "Gratis col tuo account GitHub (token classic o fine-grained): gpt-4o-mini, llama, phi, qwen, deepseek." },
    { keyFmt: "Inizia con sk_ (es. sk_xxxx)", id: "novita", label: "Novita AI", env: "NOVITA_API_KEY", host: "api.novita.ai", chatPath: "/v3/openai/chat/completions", modelsPath: "/v3/openai/models", detect: /^sk_/, signup: "https://novita.ai/settings/key-management", free: true, note: "Crediti gratis: molti modelli open (llama, qwen, deepseek)." },
    { keyFmt: "Inizia con cpk_ (es. cpk_xxxx)", id: "chutes", label: "Chutes", env: "CHUTES_API_KEY", host: "llm.chutes.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: /^cpk_/, signup: "https://chutes.ai/", free: true, note: "Modelli open serverless, molti gratuiti (deepseek, qwen)." },
    { keyFmt: "Inizia con glhf_ (es. glhf_xxxx)", id: "glhf", label: "glhf.chat", env: "GLHF_API_KEY", host: "glhf.chat", chatPath: "/api/openai/v1/chat/completions", modelsPath: "/api/openai/v1/models", detect: /^glhf_/, signup: "https://glhf.chat/", free: true, note: "Esegue quasi ogni modello HuggingFace, gratis in beta." },
    { keyFmt: "Forma id.segreto (es. 0123456789abcdef0123456789abcdef.secret)", id: "ollama-cloud", label: "Ollama Cloud", env: "OLLAMA_API_KEY", host: "ollama.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: /^[0-9a-f]{32}\./, signup: "https://ollama.com/settings/keys", free: true, note: "I tuoi modelli Ollama nel cloud (qwen, deepseek-coder). Chiave id.segreto." },
    // ★ CORSIA PRIORITARIA dell'utente: abliterated coder su GPU Kaggle (Ollama) via
    // tunnel ngrok con dominio FISSO. Attiva quando il notebook Kaggle gira. La chiave
    // è fittizia (Ollama la ignora): basta KAGGLE_KEY=ollama nel .env per attivarla.
    { keyFmt: "Chiave fittizia: basta KAGGLE_KEY=ollama (il notebook non la usa)", id: "kaggle", label: "Kaggle GPU (abliterated coder)", env: "KAGGLE_KEY", host: "paving-preschool-facelift.ngrok-free.dev", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: null, signup: "https://www.kaggle.com/code", free: true, note: "La TUA corsia abliterated coder (Qwen2.5-Coder 14B/32B) su GPU Kaggle via tunnel ngrok. Priorità nel failover quando il notebook è acceso." },
    // ★ 2026-07-30 — HOST CORRETTO. Puntava al workspace eu-central (Francoforte):
    // con una chiave creata sul portale CINESE (bailian.console.aliyun.com) quel
    // dominio risponde 401 "Incorrect API key", e il pannello dichiarava "chiave
    // obsoleta" una chiave in realtà PERFETTAMENTE VIVA. Verificato dal vivo:
    // dashscope.aliyuncs.com → 200 col tuo sk-ws-... · eu-central e -intl → 401.
    // Se un domani la chiave la fai sul portale internazionale, usa la voce
    // "alibaba-intl" qui sotto (DASHSCOPE_INTL_API_KEY).
    { keyFmt: "Inizia con sk- (es. sk-ws-xxxx)", id: "alibaba", label: "Alibaba Qwen (DashScope Cina)", env: "DASHSCOPE_API_KEY", host: "dashscope.aliyuncs.com", chatPath: "/compatible-mode/v1/chat/completions", modelsPath: "/compatible-mode/v1/models", detect: /^sk-/, signup: "https://bailian.console.aliyun.com/", free: true, note: "Model Studio CINESE (qwen-coder/max/flash). La chiave del portale cinese funziona SOLO su dashscope.aliyuncs.com, non sui domini -intl/eu-central.", ambiguousHint: true },
    { keyFmt: "Inizia con sk- (es. sk-xxxx)", id: "alibaba-intl", label: "Alibaba Qwen (DashScope internazionale)", env: "DASHSCOPE_INTL_API_KEY", host: "dashscope-intl.aliyuncs.com", chatPath: "/compatible-mode/v1/chat/completions", modelsPath: "/compatible-mode/v1/models", detect: /^sk-/, signup: "https://bailian.console.alibabacloud.com/", free: true, note: "Model Studio INTERNAZIONALE (Singapore/Francoforte). Chiave separata da quella cinese: le due NON sono intercambiabili.", ambiguousHint: true },

    // ★ 2026-07-27 — NUOVI GATEWAY GRATUITI (scoperti dal cacciatore online):
    // veri endpoint OpenAI-compat, piano free senza carta -> entrano nel failover.
    { keyFmt: "Chiave fittizia: KILO_KEY=none (nessun account richiesto)", id: "kilo", label: "Kilo Gateway (free, no account)", env: "KILO_API_KEY", host: "api.kilo.ai", chatPath: "/api/gateway/v1/chat/completions", modelsPath: "/api/gateway/v1/models", detect: null, signup: "https://kilo.ai/docs/gateway", free: true, note: "Gateway OpenAI-compat: free model senza account (kilo-auto/free router, minimax-m2.5:free, step-3.5-flash:free, nemotron-3-super-120b:free). Limite ~200 req/h per IP. Chiave fittizia: KILO_KEY=none.", ambiguousHint: false },
    { keyFmt: "Chiave fittizia: OPENCODE_ZEN_KEY=none (nessun account richiesto)", id: "opencode", label: "OpenCode Zen (gateway free)", env: "OPENCODE_ZEN_KEY", host: "opencode.ai", chatPath: "/zen/v1/chat/completions", modelsPath: "/zen/v1/models", detect: null, signup: "https://opencode.ai/docs/zen/", free: true, note: "Gateway curato di modelli free (DeepSeek V4 Flash Free, Laguna S 2.1 Free, Ling-3.0-flash Free, North Mini Code Free). OpenAI-compat. Chiave fittizia: OPENCODE_ZEN_KEY=none." },

    // ★ AGGIUNTO — Venice AI: OpenAI-compat, modelli UNCENSORED (venice-uncensored,
    // zai-org-glm-5-2). Chiave + base URL nel .env (VENICE_API_KEY, VENICE_BASE_URL).
    { keyFmt: "Inizia con VENICE_ (es. VENICE_xxxx)", id: "venice", label: "Venice AI (uncensored)", env: "VENICE_API_KEY", host: "api.venice.ai", chatPath: "/api/v1/chat/completions", modelsPath: "/api/v1/models", detect: /^VENICE_/, signup: "https://venice.ai/", free: true, note: "Uncensored: venice-uncensored, glm-5-2. OpenAI-compat su api.venice.ai." },

    // ★ 2026-07-27 — NUOVI PROVIDER (endpoint verificati live con curl). OpenAI-compat.
        // ArliAI: specializzato in modelli UNCENSORED/RP (senza filtri), piano free con
        // limite di richieste. Endpoint api.arliai.com/v1 (401 senza chiave = vivo).
        // Chiave: alphanumerica, 40+ caratteri, senza prefisso fisso.
        // ★ 2026-07-30 — la chiave ArliAI puo' essere alfanumerica lunga OPPURE un
        // UUID coi trattini (es. 64e12d03-17bc-...): la vecchia regex accettava solo
        // la prima e rifiutava l'UUID (i trattini). Ora accetta entrambe; a decidere
        // davvero e' comunque il test dal vivo (identifyKeyLive).
        { keyFmt: "Chiave alfanumerica lunga (40+) o UUID (xxxxxxxx-xxxx-...)", id: "arliai", label: "ArliAI (uncensored/RP)", env: "ARLIAI_API_KEY", host: "api.arliai.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: /^[A-Za-z0-9]{40,}$|^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i, signup: "https://www.arliai.com/", free: true, note: "Modelli UNCENSORED/roleplay illimitati sul piano (Mistral-Nemo, Llama-3.1-8B abliterated, Qwen2.5-Coder (varie)). Piano free disponibile.", uncensored: true },
        // DeepInfra: catalogo enorme open-weight, credito iniziale gratuito, OpenAI-compat.
        // Chiave: alphanumerica, 40+ caratteri, senza prefisso fisso.
        { keyFmt: "Chiave alfanumerica lunga (40+ caratteri, es. abcdef123456...)", id: "deepinfra", label: "DeepInfra", env: "DEEPINFRA_API_KEY", host: "api.deepinfra.com", chatPath: "/v1/openai/chat/completions", modelsPath: "/v1/openai/models", detect: /^[A-Za-z0-9]{40,}$/, signup: "https://deepinfra.com/dash/api_keys", free: true, note: "Tanti modelli open (llama, qwen, deepseek, mixtral). Credito iniziale gratuito, poi economico. Chiave alfanumerica lunga.", billed: true },
        // Featherless: 'run any HuggingFace model', include molti abliterated/uncensored.
        { keyFmt: "Inizia con rc_ (es. rc_xxxx)", id: "featherless", label: "Featherless (HF models)", env: "FEATHERLESS_API_KEY", host: "api.featherless.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: /^rc_/, signup: "https://featherless.ai/", free: false, note: "Esegue quasi ogni modello HuggingFace, inclusi abliterated/uncensored. Abbonamento a prezzo fisso. Chiave rc_...", uncensored: true, billed: true },
        // Cloudrift: gateway inference OpenAI-compat, credito di prova.
        // Chiave: alphanumerica, 40+ caratteri, senza prefisso fisso.
        { keyFmt: "Chiave alfanumerica lunga (40+ caratteri, es. abcdef123456...)", id: "cloudrift", label: "Cloudrift", env: "CLOUDRIFT_API_KEY", host: "inference.cloudrift.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: /^[A-Za-z0-9]{40,}$/, signup: "https://www.cloudrift.ai/", free: true, note: "Gateway inference OpenAI-compat (deepseek, qwen, llama). Credito di prova gratuito. Chiave alfanumerica lunga.", uncensored: true },

    // ---- A PAGAMENTO / trial (utili ma con costi) ------------------------
    { keyFmt: "Inizia con sk- (es. sk-proj-xxxx o sk-xxxx)", id: "openai", label: "OpenAI", env: "OPENAI_API_KEY", host: "api.openai.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: /^sk-(proj-|svcacct-)?[A-Za-z0-9_-]{20,}$/, signup: "https://platform.openai.com/api-keys", free: false, billed: true, note: "GPT-4o/4.1/o-series. A pagamento. Chiave sk-... o sk-proj-...", ambiguousHint: true },
    { keyFmt: "Inizia con sk- (es. sk-xxxx)", id: "deepseek", label: "DeepSeek", env: "DEEPSEEK_API_KEY", host: "api.deepseek.com", chatPath: "/chat/completions", modelsPath: "/models", detect: /^sk-/, signup: "https://platform.deepseek.com/api_keys", free: false, billed: true, note: "deepseek-chat/reasoner, economici e forti nel coding. Chiave sk-... (ambigua).", ambiguousHint: true },
    { keyFmt: "Inizia con sk-ant- (es. sk-ant-xxxx)", id: "anthropic", label: "Anthropic Claude", env: "ANTHROPIC_API_KEY", host: "api.anthropic.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: /^sk-ant-/, signup: "https://console.anthropic.com/settings/keys", free: false, billed: true, note: "Claude (Opus/Sonnet). Endpoint OpenAI-compat su /v1. A pagamento." },
    { keyFmt: "Inizia con xai- (es. xai-xxxx)", id: "xai", label: "xAI Grok", env: "XAI_API_KEY", host: "api.x.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: /^xai-/, signup: "https://console.x.ai/", free: false, billed: true, note: "Grok. Trial iniziale, poi a pagamento." },
    { keyFmt: "Inizia con pplx- (es. pplx-xxxx)", id: "perplexity", label: "Perplexity", env: "PERPLEXITY_API_KEY", host: "api.perplexity.ai", chatPath: "/chat/completions", modelsPath: null, detect: /^pplx-/, signup: "https://www.perplexity.ai/settings/api", free: false, billed: true, note: "Sonar con ricerca web integrata. A pagamento." },
    { keyFmt: "Inizia con fw_ (es. fw_xxxx)", id: "fireworks", label: "Fireworks AI", env: "FIREWORKS_API_KEY", host: "api.fireworks.ai", chatPath: "/inference/v1/chat/completions", modelsPath: "/inference/v1/models", detect: /^fw_/, signup: "https://fireworks.ai/account/api-keys", free: false, billed: true, note: "Modelli open velocissimi (llama, qwen, deepseek). Credito di prova." },
    { keyFmt: "64 caratteri esadecimali (es. a1b2c3...f0)", id: "together", label: "Together AI", env: "TOGETHER_API_KEY", host: "api.together.xyz", chatPath: "/v1/chat/completions", modelsPath: "/v1/models", detect: /^[0-9a-f]{64}$/, signup: "https://api.together.ai/settings/api-keys", free: false, billed: true, note: "Molti modelli open. Credito iniziale gratuito. Chiave 64 esadecimali." },
];

// ★ 2026-07-30 — FUSIONE COL CATALOGO PRECONFIGURATO (providerCatalog.js).
// Il registro qui sopra è la lista CURATA (note e quote tarate a mano); il
// catalogo è la lista LARGA di tutti i provider noti, con endpoint e formato
// della chiave già pronti. Le voci curate VINCONO: dal catalogo prendono solo i
// campi che non hanno (alias, freeModels, verified). Le voci nuove si aggiungono
// in coda, così il selettore manuale e il rilevamento le vedono subito.
// Se il file manca, il registro continua a funzionare com'era (nessun crash).
let CATALOG = [];
try { CATALOG = require("./providerCatalog").CATALOG || []; } catch (_) { CATALOG = []; }
for (const c of CATALOG) {
    const cur = PROVIDERS.find(p => p.id === c.id);
    if (cur) {
        for (const k of ["aliases", "verified", "freeModels", "keyFmt", "signup", "keyUrl"]) {
            if (cur[k] === undefined && c[k] !== undefined) cur[k] = c[k];
        }
        continue;
    }
    PROVIDERS.push(Object.assign({}, c));
}

/** Quanto è "probabile" un candidato: gratis e verificati prima, a pagamento e
 *  da confermare dopo. Serve a ordinare le proposte quando la chiave è ambigua. */
function candRank(p) {
    return (p.free ? 0 : 3) + (p.verified === false ? 2 : 0) + (p.billed ? 1 : 0);
}

/**
 * ★ 2026-07-30 — NORMALIZZAZIONE CHIAVE (causa #1 di "chiave non riconosciuta").
 * L'utente incolla spesso più della chiave nuda: spazi, a-capo, virgolette, il
 * prefisso "Bearer "/"Authorization:", oppure copia dall'ambiente la riga intera
 * `ARLIAI_API_KEY=xxx` (o `export NAME=xxx`). Qui riduciamo tutto alla sola chiave.
 * Conserviamo la punteggiatura INTERNA (i JWT hanno i punti, github_pat gli _,
 * sk-... i trattini): togliamo solo il rumore ai bordi.
 * @param {string} raw
 * @returns {string} la chiave pulita
 */
function normalizeKey(raw) {
    let k = String(raw == null ? "" : raw);
    k = k.replace(/[\u200B-\u200D\uFEFF]/g, "").replace(/\u00A0/g, " ").trim();  // via zero-width / no-break space
    k = k.replace(/^(?:export|set)\s+/i, "");                                    // "export NAME=..."
    const kv = /^[A-Za-z_][A-Za-z0-9_]*\s*[:=]\s*([\s\S]+)$/.exec(k);            // "NAME=valore" / "NAME: valore"
    if (kv) k = kv[1].trim();
    k = k.replace(/^[`'"<[(]+/, "").replace(/[`'">\])]+$/, "").trim();           // virgolette/parentesi ai bordi
    k = k.replace(/^Authorization\s*:\s*/i, "").replace(/^(?:Bearer|Token)\s+/i, "").trim(); // header auth
    const first = /^(\S+)/.exec(k);                                              // una chiave non ha spazi interni
    if (first) k = first[1];
    return k;
}

/**
 * Rileva il/i provider da una chiave incollata. Ritorna:
 *   { best, candidates:[{id,label,...,ambiguous}], value }
 * best = miglior candidato (o null). candidates = tutti i plausibili (ordinati).
 */
function detectProvider(rawKey) {
    const key = normalizeKey(rawKey);
    if (!key) return { best: null, candidates: [] };

    // 1) Prefissi FORTI (un solo provider possibile) — controllati in ordine.
    const STRONG = [
        [/^sk-or-v1-/, "openrouter"],
        [/^sk-ant-/, "anthropic"],
        [/^sk-(proj|svcacct)-/, "openai"],
        [/^gsk_/, "groq"],
        [/^hf_/, "hf"],
        [/^csk-/, "cerebras"],
        [/^nvapi-/, "nvidia"],
        [/^xai-/, "xai"],
        [/^pplx-/, "perplexity"],
        [/^fw_/, "fireworks"],
        [/^glhf_/, "glhf"],
        [/^cpk_/, "chutes"],
        [/^rc_/, "featherless"],
        // Cloudflare: `cfat_` = account token, `cfut_` = user token (quello che si
        // ottiene creando il token dal profilo). Vanno bene entrambi.
        [/^cf(at|ut)_/, "cloudflare"],
        [/^ghp_/, "github"],
        [/^github_pat_/, "github"],
        // ★ 2026-07-30 — JWT (eyJ...) e id.segreto NON sono più "forti": li usano
        // più provider (JWT: Hyperbolic, Nebius, io.net, MiniMax · id.segreto:
        // Ollama Cloud, Z.ai, BigModel). Prima vinceva sempre il primo della lista
        // — cioè Hyperbolic, che è pure a credito zero — e la chiave finiva salvata
        // sul provider sbagliato. Ora scendono fra i casi ambigui e scegli tu.
        [/^AIza[0-9A-Za-z_-]{10,}$/, "google"]
    ];
    for (const [rx, id] of STRONG) {
        if (rx.test(key)) return { best: publicView(byId(id)), candidates: [Object.assign(publicView(byId(id)), { ambiguous: false })] };
    }

    // 1-ter) ★ 2026-07-30 — TRAPPOLA GOOGLE. Un token che inizia con "AQ." NON è
    // una chiave API di AI Studio: è un token OAuth TEMPORANEO (dura circa un'ora)
    // che si prende copiando dal posto sbagliato — di solito dalla sessione del
    // browser o dagli strumenti Gemini/Code Assist. Prima il registro lo trattava
    // come chiave Google valida: veniva salvato nel .env, funzionava per qualche
    // minuto e poi il pannello lo dichiarava "chiave obsoleta". Verificato dal vivo
    // il 2026-07-30: 401 "Expected OAuth 2 access token" su tutti e tre i modi
    // (Bearer, ?key=, x-goog-api-key). Ora lo diciamo PRIMA di salvarlo.
    if (/^AQ\./.test(key)) {
        const g = byId("google");
        return {
            best: null,
            candidates: g ? [Object.assign(publicView(g), { ambiguous: true })] : [],
            warn: "Questo NON è una chiave API di Google: i token che iniziano con «AQ.» sono temporanei e scadono in circa un'ora. La chiave vera inizia con «AIza» e si prende su aistudio.google.com/app/apikey → «Create API key»."
        };
    }

    // 1-bis) ★ 2026-07-30 — PREFISSI FORTI DEL CATALOGO (vck_, up_, flp_, sn4_,
    // secret_, inference-, ms-, bce-v3/, UUID Scaleway...): sono prefissi unici,
    // quindi valgono come la lista STRONG qui sopra. Prima questi provider non
    // venivano riconosciuti affatto e finivano in "provider non riconosciuto".
    const strongCat = PROVIDERS.filter(p => p.strong && p.detect && p.detect.test(key));
    if (strongCat.length === 1) {
        return { best: publicView(strongCat[0]), candidates: [Object.assign(publicView(strongCat[0]), { ambiguous: false })] };
    }

    // 2) Forme AMBIGUE (più provider plausibili) → proponi i candidati, UI conferma.
    let ids = [];
    if (/^sk-[A-Za-z0-9]/.test(key)) {
        // sk- generico: molti provider lo usano. Includi i principali + together
        // (alcune chiavi Together hanno prefisso sk-). La UI fa scegliere.
        ids = ["deepseek", "openai", "alibaba", "together", "mistral"];
    }
    else if (/^eyJ[A-Za-z0-9_-]+\./.test(key)) ids = ["io-intelligence", "nebius", "minimax", "hyperbolic"];
    else if (/^[0-9a-f]{32}\.[A-Za-z0-9_-]{10,}$/.test(key)) ids = ["ollama-cloud", "zai", "bigmodel"];
    else if (/^sk_/.test(key)) ids = ["novita", "ppinfra"];
    else if (/^[0-9a-f]{64}$/.test(key)) ids = ["together"];
    else if (/^[A-Za-z0-9]{32}$/.test(key)) ids = ["deepinfra", "mistral", "together"];

    // ★ 2026-07-30 — CANDIDATI DAL CATALOGO: qualunque altra voce la cui regex
    // riconosce questa chiave entra fra i candidati (in coda a quelli storici,
    // che restano i preferiti), ordinata per probabilità: gratis e verificati
    // prima. Così una chiave sk- propone anche moonshot/siliconflow/hunyuan/...
    // invece di lasciare l'utente davanti a un elenco vuoto.
    const extra = PROVIDERS
        .filter(p => p.detect && p.detect.test(key) && ids.indexOf(p.id) < 0)
        .sort((a, b) => candRank(a) - candRank(b))
        .map(p => p.id);
    ids = ids.concat(extra);

    const cands = ids.map(byId).filter(Boolean);
    return {
        best: cands[0] ? Object.assign(publicView(cands[0]), { ambiguous: cands.length > 1 }) : null,
        candidates: cands.map(p => Object.assign(publicView(p), { ambiguous: cands.length > 1 }))
    };
}

/** Vista "pubblica" (senza la regex) di una voce provider. */
function publicView(p) {
    return {
        id: p.id, label: p.label, env: p.env, host: p.host,
        chatPath: p.chatPath, modelsPath: p.modelsPath || null,
        signup: p.signup, free: !!p.free, billed: !!p.billed, note: p.note || "",
        keyFmt: p.keyFmt || "", uncensored: !!p.uncensored,
        // ★ 2026-07-30 — verified:false = endpoint preso dal catalogo ma non ancora
        // confermato dal vivo. La UI lo mostra, così sai che dopo il salvataggio
        // conviene premere "Verifica".
        verified: p.verified !== false
    };
}

function byId(id) { return PROVIDERS.find(p => p.id === id) || null; }
function byEnv(env) { return PROVIDERS.find(p => p.env === env) || null; }
function all() { return PROVIDERS.map(publicView); }
/** Solo i provider con piano gratuito, per i "suggerimenti". */
function freeSuggestions() { return PROVIDERS.filter(p => p.free).map(publicView); }

/**
 * FREE_PROVIDERS — "Cacciatore di taglie": lista CURATA (NON discovery automatica)
 * di provider/modelli gratuiti verificati. L'agente la mantiene a mano qui, così
 * la UI può proporli all'utente senza rischi di rate-limit/ban/falsi positivi.
 * Ogni voce:
 *   id        identificatore (coincide con PROVIDERS[].id quando esiste)
 *   name      nome leggibile
 *   keyUrl    dove prendere la chiave (apre il sito; MAI esponre chiavi altrui)
 *   freeModels elenco (curato) di modelli :free noti
 *   note      perché vale la pena / cosa offre
 *   uncensored true per provider/modelli senza filtri (dolphin/abliterated)
 */
const FREE_PROVIDERS = [
    { id: "openrouter", name: "OpenRouter ⚠️ (ora a pagamento)", keyUrl: "https://openrouter.ai/keys",
      freeModels: [],
      note: "⚠️ Verificato 2026-07-24: i modelli :free grossi sono passati a pagamento (404 → 'use the paid slug'). Escluso dal failover gratuito per non creare buchi. Si riattiva con OPENROUTER_ENABLE=1 nel .env." },
    { id: "github", name: "GitHub Models (gratis col tuo account)", keyUrl: "https://github.com/settings/tokens",
      freeModels: ["openai/gpt-4o-mini", "meta/llama-3.3-70b-instruct", "microsoft/phi-4", "deepseek/deepseek-v3", "mistral-ai/codestral-2501"],
      note: "Gratis con un token GitHub (nessuna carta). Metti il token come GITHUB_TOKEN: diventa subito una corsia del failover." },
    { id: "mistral", name: "Mistral (piano free)", keyUrl: "https://console.mistral.ai/api-keys/",
      freeModels: ["codestral-latest", "devstral-medium-latest", "mistral-large-latest", "mistral-small-latest"],
      note: "Piano free con 50 richieste/minuto: codestral è ottimo per il codice. Chiave da 32 caratteri." },
    { id: "groq", name: "Groq", keyUrl: "https://console.groq.com/keys",
      freeModels: ["llama-3.3-70b-versatile", "qwen-qwq-32b", "gpt-oss-120b", "deepseek-r1-distill-llama-70b"],
      note: "Velocissimo, gratis: llama-3.3-70b, qwen, gpt-oss-120b, deepseek-distill." },
    { id: "google", name: "Google AI Studio (Gemini)", keyUrl: "https://aistudio.google.com/app/apikey",
      freeModels: ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-2.5-pro (quota giornaliera)"],
      note: "Gratis: gemini-2.x-flash (grande contesto). Buono anche per immagini." },
    { id: "hf", name: "HuggingFace Inference", keyUrl: "https://huggingface.co/settings/tokens",
      freeModels: ["meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen2.5-Coder-32B-Instruct", "deepseek-ai/DeepSeek-V3-0324"],
      note: "Router su molti provider; crediti free mensili. Ospita anche modelli abliterated (vedi uncensored).",
      uncensored: false },
    { id: "cloudflare", name: "Cloudflare Workers AI", keyUrl: "https://dash.cloudflare.com/profile/api-tokens",
      freeModels: ["@cf/openai/gpt-oss-120b", "@cf/moonshotai/kimi-k2.7-code", "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"],
      note: "Gratis ogni giorno (quota neuroni). Oltre alla chiave cfat_... serve CLOUDFLARE_ACCOUNT_ID nel .env, perché l'indirizzo contiene l'ID account." },
    { id: "cerebras", name: "Cerebras", keyUrl: "https://cloud.cerebras.ai/",
      freeModels: ["gpt-oss-120b", "zai-glm-4.7", "gemma-4-31b"],
      note: "Gratis e ULTRA-veloce. ATTENZIONE al limite vero: 5 richieste al MINUTO (2400 al giorno) — non è la quota che finisce, è la raffica. Il router ora lo rispetta da solo." },
    { id: "nvidia", name: "NVIDIA NIM", keyUrl: "https://build.nvidia.com/",
      freeModels: ["nvidia/llama-3.1-nemotron-ultra-253b-v1", "deepseek-ai/deepseek-v3-0324", "qwen/qwen3-coder-480b-a35b"],
      note: "Gratis: modelli GROSSI (nemotron, deepseek, qwen-coder, llama-405b). Ottimo per RE.",
      uncensored: true },
    { id: "sambanova", name: "SambaNova", keyUrl: "https://cloud.sambanova.ai/apis",
      freeModels: ["Meta-Llama-3.3-70B-Instruct", "Qwen2.5-Coder-32B-Instruct", "DeepSeek-V3-0324"],
      note: "Gratis e veloce: llama-3.1-405B, qwen. Chiave senza prefisso fisso." },
    { id: "hyperbolic", name: "Hyperbolic ⚠️ (credito finito)", keyUrl: "https://app.hyperbolic.xyz/settings",
      freeModels: [],
      note: "⚠️ Verificato 2026-07-24: 402 'insufficient funds'. Fuori dal failover finché non ha credito (HYPERBOLIC_ENABLE=1 per riaccenderlo)." },
    { id: "novita", name: "Novita AI", keyUrl: "https://novita.ai/settings/key-management",
      freeModels: ["meta-llama/llama-3.3-70b-instruct", "qwen/qwen2.5-coder-32b-instruct", "deepseek/deepseek-v3-turbo"],
      note: "Crediti gratis: molti modelli open (llama, qwen, deepseek)." },
    { id: "chutes", name: "Chutes", keyUrl: "https://chutes.ai/",
      freeModels: ["deepseek-ai/DeepSeek-V3", "Qwen/Qwen3-235B-A22B", "meta-llama/Llama-3.3-70B-Instruct"],
      note: "Modelli open serverless, molti gratuiti (deepseek, qwen)." },
    { id: "ollama-cloud", name: "Ollama Cloud", keyUrl: "https://ollama.com/settings/keys",
      freeModels: ["qwen2.5-coder:32b", "deepseek-r1:70b", "llama3.3:70b"],
      note: "I tuoi modelli Ollama nel cloud (qwen, deepseek-coder). Chiave id.segreto." },
    { id: "kaggle", name: "Kaggle GPU (abliterated coder)", keyUrl: "https://www.kaggle.com/code",
      freeModels: ["Qwen2.5-Coder-14B-Instruct-abliterated (notebook 14B)", "Qwen3-Coder-30B-A3B MoE abliterated (notebook 30B)"],
      note: "La TUA corsia abliterated coder su GPU Kaggle via tunnel ngrok. Priorità nel failover quando il notebook è acceso." },

    // ★ 2026-07-27 — NUOVI GATEWAY FREE (scoperti dal cacciatore online). OpenAI-compat,
    // piano gratuito senza carta: entrano nel failover quando incolli la chiave fittizia.
    { id: "kilo", name: "Kilo Gateway (free, no account)", keyUrl: "https://kilo.ai/docs/gateway",
      freeModels: ["kilo-auto/free (router)", "minimax/minimax-m2.5:free", "stepfun/step-3.5-flash:free", "nvidia/nemotron-3-super-120b-a12b:free"],
      note: "Gateway OpenAI-compat: i modelli free funzionano SENZA account (basta KILO_KEY=none nel .env). Limite ~200 req/h per IP condiviso. Buon rinforzo al failover." },
    { id: "opencode", name: "OpenCode Zen (gateway free)", keyUrl: "https://opencode.ai/docs/zen/",
      freeModels: ["DeepSeek V4 Flash Free", "Laguna S 2.1 Free", "Ling-3.0-flash Free", "North Mini Code Free"],
      note: "Gateway curato di modelli free (OpenAI-compat su opencode.ai/zen/v1). Metti OPENCODE_ZEN_KEY=none nel .env per attivarlo." },

    // ★ 2026-07-27 — NUOVI PROVIDER (endpoint verificati live). Uncensored dove indicato.
        { id: "arliai", name: "ArliAI (senza filtri / roleplay)", keyUrl: "https://www.arliai.com/",
          freeModels: ["Mistral-Nemo-12B-ArliAI-RPMax", "Llama-3.1-8B abliterated", "Qwen2.5-Coder (varie)"],
          note: "Specializzato in modelli SENZA FILTRI e roleplay: sul piano le richieste sono illimitate come modelli, con un limite di richieste in parallelo. Piano free disponibile.",
          uncensored: true },
        { id: "deepinfra", name: "DeepInfra (catalogo enorme open)", keyUrl: "https://deepinfra.com/dash/api_keys",
          freeModels: ["meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen2.5-Coder-32B-Instruct", "deepseek-ai/DeepSeek-V3", "mistralai/Mixtral"],
          note: "Tantissimi modelli open a prezzo bassissimo, con credito iniziale gratuito. OpenAI-compat, ottimo come rincalzo.",
          uncensored: false },
        { id: "featherless", name: "Featherless (ogni modello HuggingFace)", keyUrl: "https://featherless.ai/",
          freeModels: ["qualsiasi modello HF, inclusi abliterated/uncensored"],
          note: "Esegue quasi OGNI modello di HuggingFace (compresi gli abliterated senza filtri) ad abbonamento fisso. Chiave rc_...",
          uncensored: true },
        { id: "cloudrift", name: "Cloudrift (gateway inference)", keyUrl: "https://www.cloudrift.ai/",
          freeModels: ["deepseek", "qwen", "llama (secondo catalogo live)"],
          note: "Gateway inference OpenAI-compat con credito di prova gratuito. Buon rincalzo al failover.",
          uncensored: true },

    // ★ 2026-07-27 — SUGGERIMENTI (NON nel failover: endpoint non OpenAI-compat standard
    // o richiedono account). Il cacciatore li propone, ma Antigravity non li usa attivamente.
    { id: "cohere", name: "Cohere (free trial, no carta)", keyUrl: "https://dashboard.cohere.com/api-keys",
      freeModels: ["command-a-03-2025", "command-r-plus-08-2024", "command-r7b-12-2024"],
      note: "Free 'Trial' 1000 chiamate/mese, no carta, ma endpoint /v2 NON OpenAI-compat -> non usato dal failover. Utile solo chiamandolo a mano." },
    { id: "vercel", name: "Vercel AI Gateway (aggregatore)", keyUrl: "https://vercel.com/docs/ai-gateway",
      freeModels: ["(router a molti provider, $5/mese di credito)"],
      note: "Aggregatore che instrada a tanti provider. Richiede account Vercel + chiave -> non nel failover automatico, ma buono come fonte di modelli." },
    // ★ 2026-07-24 — RIMOSSE tre voci che facevano perdere tempo all'utente:
    //   • "nous" → creare la chiave sul portale Nous CHIEDE SOLDI, non è gratis;
    //   • "hf-uncensored" e "ollama-uncensored" → non sono provider con API gratuita:
    //     scaricano modelli da far girare IN LOCALE, e su una Quadro T1000 (4 GB)
    //     non gira niente di utile. Proporli era una presa in giro.
    // Il cacciatore deve proporre SOLO API gratuite raggiungibili dalla rete.
];

// ★ 2026-07-30 — Il cacciatore ora propone anche TUTTI i provider del catalogo
// preconfigurato (scheda "Provider" e scheda "Senza filtri"). Ogni proposta ha
// già id/endpoint/variabile .env nel registro: premendo "Incolla qui" e
// incollando la chiave, il salvataggio funziona davvero e il provider entra nel
// failover senza toccare il codice.
for (const c of CATALOG) {
    if (FREE_PROVIDERS.some(f => f.id === c.id)) continue;
    FREE_PROVIDERS.push({
        id: c.id,
        name: c.label + (c.verified === false ? " (da verificare)" : ""),
        keyUrl: c.signup || "",
        freeModels: c.freeModels || [],
        note: c.note || "",
        uncensored: !!c.uncensored,
        // niente piano gratuito vero: resta proposto ma marcato, così sai che è
        // credito di prova / a consumo prima di perderci tempo.
        paid: !c.free
    });
}

/** Vista pubblica della lista curata (niente chiavi/segreti).
 *  type: undefined|"all" → tutto · "uncensored" → solo senza filtri. */
function freeProviders(type) {
    let list = FREE_PROVIDERS;
    if (type === "uncensored") list = list.filter(p => p.uncensored);
    return list.map(p => Object.assign({}, p));
}

module.exports = { PROVIDERS, detectProvider, normalizeKey, publicView, byId, byEnv, all, freeSuggestions, FREE_PROVIDERS, freeProviders };
