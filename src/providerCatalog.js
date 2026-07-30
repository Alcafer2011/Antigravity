"use strict";

/**
 * providerCatalog — CATALOGO PRECONFIGURATO di TUTTI i provider LLM noti
 * (OpenAI-compatibili) + delle piattaforme GPU dove ospitare i modelli tuoi.
 *
 * ★ 2026-07-30 — PERCHÉ ESISTE QUESTO FILE
 * Il cacciatore di taglie proponeva provider (letti dalle liste online) che NON
 * erano nel registro: creavi la chiave, la incollavi e il rilevamento diceva
 * "provider non riconosciuto", oppure il selettore manuale conteneva solo i 25
 * provider scritti a mano in providerRegistry.js. Qui c'è la lista LARGA, già
 * pronta con endpoint, nome della variabile .env, formato della chiave e alias
 * (i nomi con cui le liste online li chiamano), così:
 *   1) incolli la chiave → il provider si riconosce da solo (detect);
 *   2) se non si riconosce → il selettore manuale contiene TUTTI questi provider;
 *   3) il cacciatore, quando trova "Nebius"/"Cohere"/"Scaleway"/..., riesce ad
 *      agganciarli a una voce vera (knownId) e mostra il bottone "Incolla qui".
 *
 * providerRegistry.js FONDE questo catalogo con le sue voci curate: le voci
 * curate VINCONO (hanno note/quote tarate a mano), da qui arriva tutto il resto.
 *
 * Campi (stessi di providerRegistry, più questi):
 *   aliases[]  nomi alternativi (come li scrivono le liste online / il cacciatore)
 *   verified   true = endpoint controllato · false = plausibile ma da confermare
 *              col bottone "Verifica" del pannello chiavi. Le voci non verificate
 *              restano selezionabili: al massimo il probe risponde 404 e lo vedi.
 *   strong     true = il prefisso della chiave è UNICO → riconoscimento diretto
 *   freeModels[] modelli gratuiti noti (per la scheda del cacciatore)
 *
 * REGOLA: qui NON vanno chiavi/segreti. Solo endpoint pubblici e link ufficiali.
 */

const NV = "⚠️ endpoint da confermare col bottone «Verifica» dopo aver salvato la chiave.";

const CATALOG = [
    // ================= GRANDI CLOUD / OPENAI-COMPAT =========================
    {
        id: "nebius", label: "Nebius AI Studio", env: "NEBIUS_API_KEY",
        host: "api.studio.nebius.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^eyJ[A-Za-z0-9_-]+\./, strong: false,
        keyFmt: "JWT (inizia con eyJ...)", signup: "https://studio.nebius.com/settings/api-keys",
        free: true, billed: true, verified: true,
        aliases: ["nebius", "nebius ai studio", "nebius token factory"],
        freeModels: ["meta-llama/Llama-3.3-70B-Instruct", "Qwen/Qwen2.5-Coder-32B-Instruct", "deepseek-ai/DeepSeek-V3"],
        note: "Catalogo open grosso (llama, qwen-coder, deepseek) con credito iniziale gratuito. Chiave JWT come Hyperbolic: se il rilevamento propone entrambi, scegli tu."
    },
    {
        id: "moonshot", label: "Moonshot AI (Kimi)", env: "MOONSHOT_API_KEY",
        host: "api.moonshot.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^sk-/, keyFmt: "Inizia con sk- (es. sk-xxxx)",
        signup: "https://platform.moonshot.ai/console/api-keys",
        free: false, billed: true, verified: true,
        aliases: ["moonshot", "moonshot ai", "kimi", "kimi k2", "moonshotai"],
        freeModels: [],
        note: "Kimi K2 (contesto enorme, forte nel coding agentico). A consumo, prezzi bassi."
    },
    {
        id: "zai", label: "Z.ai (GLM / Zhipu)", env: "ZAI_API_KEY",
        host: "api.z.ai", chatPath: "/api/paas/v4/chat/completions", modelsPath: null,
        detect: /^[0-9a-f]{32}\.[A-Za-z0-9]{10,}$/, keyFmt: "Forma id.segreto (32 esadecimali + punto + segreto)",
        signup: "https://z.ai/manage-apikey/apikey-list",
        free: true, billed: true, verified: true,
        aliases: ["z ai", "zai", "zhipu", "zhipu ai", "glm", "bigmodel"],
        freeModels: ["glm-4.5-flash", "glm-4.6-flash"],
        note: "GLM (glm-4.x/5): i modelli *-flash hanno un piano gratuito. Chiave in forma id.segreto come Ollama Cloud: se il rilevamento è incerto, scegli tu."
    },
    {
        id: "bigmodel", label: "Zhipu BigModel (Cina)", env: "BIGMODEL_API_KEY",
        host: "open.bigmodel.cn", chatPath: "/api/paas/v4/chat/completions", modelsPath: null,
        detect: /^[0-9a-f]{32}\.[A-Za-z0-9]{10,}$/, keyFmt: "Forma id.segreto (come Z.ai)",
        signup: "https://open.bigmodel.cn/usercenter/apikeys",
        free: true, billed: true, verified: true,
        aliases: ["bigmodel", "open bigmodel", "zhipu bigmodel", "chatglm"],
        freeModels: ["glm-4-flash", "glm-4.5-flash"],
        note: "Portale cinese di Zhipu: glm-4-flash gratis. Stesso endpoint di Z.ai ma dominio .cn (più lento dall'Italia)."
    },
    {
        id: "minimax", label: "MiniMax", env: "MINIMAX_API_KEY",
        host: "api.minimax.io", chatPath: "/v1/text/chatcompletion_v2", modelsPath: null,
        detect: /^eyJ[A-Za-z0-9_-]+\./, keyFmt: "JWT (inizia con eyJ...)",
        signup: "https://www.minimax.io/platform/user-center/basic-information/interface-key",
        free: false, billed: true, verified: false,
        aliases: ["minimax", "minimax m2", "minimaxi"],
        freeModels: [],
        note: "MiniMax M2 (coding/agent, contesto grande). Endpoint OpenAI-compat su /v1/text/chatcompletion_v2. " + NV
    },
    {
        id: "siliconflow", label: "SiliconFlow", env: "SILICONFLOW_API_KEY",
        host: "api.siliconflow.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^sk-/, keyFmt: "Inizia con sk- (es. sk-xxxx)",
        signup: "https://cloud.siliconflow.com/account/ak",
        free: true, billed: true, verified: true,
        aliases: ["siliconflow", "silicon flow", "siliconcloud"],
        freeModels: ["Qwen/Qwen2.5-7B-Instruct", "THUDM/glm-4-9b-chat", "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"],
        note: "Gateway cinese con molti modelli open; alcuni piccoli sono gratis a vita, gli altri a consumo economico."
    },
    {
        id: "hunyuan", label: "Tencent Hunyuan", env: "HUNYUAN_API_KEY",
        host: "api.hunyuan.cloud.tencent.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^sk-/, keyFmt: "Inizia con sk- (es. sk-xxxx)",
        signup: "https://console.cloud.tencent.com/hunyuan/api-key",
        free: true, billed: true, verified: false,
        aliases: ["hunyuan", "tencent", "tencent hunyuan", "tencent cloud"],
        freeModels: ["hunyuan-lite"],
        note: "hunyuan-lite è gratuito; i modelli grossi a consumo. " + NV
    },
    {
        id: "stepfun", label: "StepFun", env: "STEPFUN_API_KEY",
        host: "api.stepfun.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: null, keyFmt: "Chiave alfanumerica lunga (senza prefisso fisso)",
        signup: "https://platform.stepfun.com/interface-key",
        free: false, billed: true, verified: false,
        aliases: ["stepfun", "step fun", "step-3", "step 3.5"],
        freeModels: [],
        note: "Modelli step-* (gli stessi :free che passano da Kilo). " + NV
    },
    {
        id: "qianfan", label: "Baidu Qianfan (ERNIE)", env: "QIANFAN_API_KEY",
        host: "qianfan.baidubce.com", chatPath: "/v2/chat/completions", modelsPath: null,
        detect: /^bce-v3\//, strong: true, keyFmt: "Inizia con bce-v3/ (es. bce-v3/ALTAK-...)",
        signup: "https://console.bce.baidu.com/iam/#/iam/apikey/list",
        free: true, billed: true, verified: false,
        aliases: ["qianfan", "baidu", "baidu qianfan", "ernie", "wenxin"],
        freeModels: ["ernie-speed-128k", "ernie-lite-8k"],
        note: "ERNIE: le versioni speed/lite sono gratuite. " + NV
    },
    {
        id: "modelscope", label: "ModelScope (Alibaba, free)", env: "MODELSCOPE_API_KEY",
        host: "api-inference.modelscope.cn", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^ms-[0-9a-fA-F-]{20,}$/, strong: true, keyFmt: "Inizia con ms- (es. ms-xxxxxxxx-....)",
        signup: "https://modelscope.cn/my/myaccesstoken",
        free: true, billed: false, verified: true,
        aliases: ["modelscope", "model scope", "modelscope inference"],
        freeModels: ["Qwen/Qwen3-Coder-480B-A35B-Instruct", "deepseek-ai/DeepSeek-V3", "Qwen/QwQ-32B"],
        note: "GRATIS ~2000 chiamate/giorno su modelli GROSSI (qwen3-coder-480b, deepseek). Serve solo un account ModelScope (Alibaba), niente carta."
    },
    {
        id: "ppinfra", label: "PPIO / PPInfra (Novita Cina)", env: "PPINFRA_API_KEY",
        host: "api.ppinfra.com", chatPath: "/v3/openai/chat/completions", modelsPath: "/v3/openai/models",
        detect: /^sk_/, keyFmt: "Inizia con sk_ (come Novita)",
        signup: "https://ppinfra.com/settings/key-management",
        free: true, billed: true, verified: false,
        aliases: ["ppinfra", "ppio", "pp infra"],
        freeModels: [],
        note: "Gemello cinese di Novita (stessa API /v3/openai). Credito di benvenuto. " + NV
    },

    // ================= GATEWAY / AGGREGATORI ================================
    {
        id: "vercel", label: "Vercel AI Gateway", env: "VERCEL_AI_API_KEY",
        host: "ai-gateway.vercel.sh", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^vck_/, strong: true, keyFmt: "Inizia con vck_ (es. vck_xxxx)",
        signup: "https://vercel.com/docs/ai-gateway",
        free: true, billed: true, verified: true,
        aliases: ["vercel", "vercel ai gateway", "ai gateway"],
        freeModels: ["(router a molti provider — credito mensile incluso nel piano Hobby)"],
        note: "Aggregatore: una chiave sola, tutti i provider dietro. Credito gratuito mensile col piano Hobby."
    },
    {
        id: "requesty", label: "Requesty (router)", env: "REQUESTY_API_KEY",
        host: "router.requesty.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: null, keyFmt: "Chiave alfanumerica lunga (senza prefisso fisso)",
        signup: "https://app.requesty.ai/api-keys",
        free: true, billed: true, verified: false,
        aliases: ["requesty", "requesty router", "requesty ai"],
        freeModels: [],
        note: "Router tipo OpenRouter con credito di prova. " + NV
    },
    {
        id: "aimlapi", label: "AI/ML API", env: "AIMLAPI_API_KEY",
        host: "api.aimlapi.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^[0-9a-fA-F]{32,80}$/, keyFmt: "chiave esadecimale (32–80 caratteri)",
        signup: "https://aimlapi.com/app/keys",
        free: true, billed: true, verified: false,
        aliases: ["aimlapi", "ai ml api", "ai/ml api"],
        freeModels: ["(200+ modelli, piccolo credito free all'iscrizione)"],
        note: "Aggregatore con 200+ modelli e un piccolo credito gratuito. " + NV
    },
    {
        id: "aihubmix", label: "AiHubMix", env: "AIHUBMIX_API_KEY",
        host: "aihubmix.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^sk-/, keyFmt: "Inizia con sk-",
        signup: "https://aihubmix.com/token",
        free: false, billed: true, verified: false,
        aliases: ["aihubmix", "ai hub mix"],
        freeModels: [],
        note: "Aggregatore (anche modelli cinesi) OpenAI-compat. " + NV
    },
    {
        id: "api302", label: "302.AI", env: "API302_API_KEY",
        host: "api.302.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^sk-/, keyFmt: "Inizia con sk-",
        signup: "https://dash.302.ai/apis/list",
        free: false, billed: true, verified: false,
        aliases: ["302 ai", "302ai", "302.ai"],
        freeModels: [],
        note: "Aggregatore a consumo, credito di prova all'iscrizione. " + NV
    },

    // ================= PROVIDER CON PIANO FREE / TRIAL ======================
    {
        id: "cohere", label: "Cohere (trial gratis)", env: "COHERE_API_KEY",
        host: "api.cohere.ai", chatPath: "/compatibility/v1/chat/completions", modelsPath: "/compatibility/v1/models",
        detect: /^[A-Za-z0-9]{40}$/, keyFmt: "40 caratteri alfanumerici",
        signup: "https://dashboard.cohere.com/api-keys",
        free: true, billed: false, verified: true,
        aliases: ["cohere", "command a", "command r", "command r+"],
        freeModels: ["command-a-03-2025", "command-r-plus-08-2024", "command-r7b-12-2024"],
        note: "Chiave 'Trial' gratuita: 1000 chiamate/mese, nessuna carta. ★ Ora punta all'endpoint OpenAI-compat /compatibility/v1, quindi può entrare nel failover (prima era escluso)."
    },
    {
        id: "codestral", label: "Mistral Codestral (chiave free dedicata)", env: "CODESTRAL_API_KEY",
        host: "codestral.mistral.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^[A-Za-z0-9]{32}$/, keyFmt: "32 caratteri alfanumerici (come Mistral)",
        signup: "https://console.mistral.ai/codestral",
        free: true, billed: false, verified: true,
        aliases: ["codestral", "mistral codestral", "codestral api"],
        freeModels: ["codestral-latest", "codestral-2501"],
        note: "Chiave Codestral SEPARATA e gratuita (endpoint dedicato codestral.mistral.ai): ottima per il completamento di codice."
    },
    {
        id: "upstage", label: "Upstage Solar", env: "UPSTAGE_API_KEY",
        host: "api.upstage.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^up_/, strong: true, keyFmt: "Inizia con up_ (es. up_xxxx)",
        signup: "https://console.upstage.ai/api-keys",
        free: true, billed: true, verified: true,
        aliases: ["upstage", "solar", "solar pro", "upstage solar"],
        freeModels: ["solar-pro2 (credito di benvenuto)"],
        note: "Solar Pro (coreano, veloce e capace). Credito gratuito all'iscrizione."
    },
    {
        id: "friendli", label: "FriendliAI", env: "FRIENDLI_TOKEN",
        host: "api.friendli.ai", chatPath: "/serverless/v1/chat/completions", modelsPath: "/serverless/v1/models",
        detect: /^flp_/, strong: true, keyFmt: "Inizia con flp_ (es. flp_xxxx)",
        signup: "https://suite.friendli.ai/user-settings/tokens",
        free: true, billed: true, verified: true,
        aliases: ["friendli", "friendliai", "friendli ai", "periflow"],
        freeModels: ["meta-llama-3.3-70b-instruct", "deepseek-r1", "qwen2.5-coder-32b"],
        note: "Serverless veloce sui modelli open, con credito gratuito iniziale."
    },
    {
        id: "inference-net", label: "Inference.net", env: "INFERENCE_API_KEY",
        host: "api.inference.net", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^inference-/, strong: true, keyFmt: "Inizia con inference- (es. inference-xxxx)",
        signup: "https://inference.net/dashboard/api-keys",
        free: true, billed: true, verified: true,
        aliases: ["inference net", "inference.net", "inferencenet"],
        freeModels: ["meta-llama/llama-3.3-70b-instruct/fp-8", "deepseek/deepseek-r1-distill-llama-70b"],
        note: "Credito gratuito iniziale su modelli open. OpenAI-compat pulito."
    },
    {
        id: "kluster", label: "Kluster.ai", env: "KLUSTER_API_KEY",
        host: "api.kluster.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: null, keyFmt: "Chiave alfanumerica lunga (senza prefisso fisso)",
        signup: "https://platform.kluster.ai/apikeys",
        free: true, billed: true, verified: true,
        aliases: ["kluster", "kluster ai", "kluster.ai"],
        freeModels: ["klusterai/Meta-Llama-3.3-70B-Instruct-Turbo", "deepseek-ai/DeepSeek-V3"],
        note: "Credito di prova gratuito su modelli open grossi (e batch a metà prezzo)."
    },
    {
        id: "io-intelligence", label: "io.net Intelligence (free)", env: "IOINTELLIGENCE_API_KEY",
        host: "api.intelligence.io.solutions", chatPath: "/api/v1/chat/completions", modelsPath: "/api/v1/models",
        detect: /^eyJ[A-Za-z0-9_-]+\./, keyFmt: "JWT (inizia con eyJ...)",
        signup: "https://ai.io.net/ai/api-keys",
        free: true, billed: false, verified: true,
        aliases: ["io net", "io.net", "io intelligence", "ionet"],
        freeModels: ["meta-llama/Llama-3.3-70B-Instruct", "deepseek-ai/DeepSeek-R1-0528", "Qwen/Qwen3-235B-A22B"],
        note: "Piano GRATUITO con quota giornaliera su modelli grossi (llama-70b, deepseek-r1, qwen-235b). Chiave JWT."
    },
    {
        id: "scaleway", label: "Scaleway Generative APIs", env: "SCALEWAY_API_KEY",
        host: "api.scaleway.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/, strong: true,
        keyFmt: "UUID (8-4-4-4-12, es. 0a1b2c3d-....)",
        signup: "https://console.scaleway.com/iam/api-keys",
        free: true, billed: true, verified: true,
        aliases: ["scaleway", "scaleway generative apis", "scaleway ai"],
        freeModels: ["llama-3.3-70b-instruct", "qwen2.5-coder-32b-instruct", "deepseek-r1-distill-llama-70b"],
        note: "Datacenter europeo (Parigi): quota gratuita mensile, poi a consumo. Buono se ti interessa che i dati restino in UE."
    },
    {
        id: "lambda", label: "Lambda Inference", env: "LAMBDA_API_KEY",
        host: "api.lambda.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^secret_/, strong: true, keyFmt: "Inizia con secret_ (es. secret_xxxx)",
        signup: "https://cloud.lambda.ai/api-keys",
        free: false, billed: true, verified: true,
        aliases: ["lambda", "lambda labs", "lambda ai", "lambda inference"],
        freeModels: [],
        note: "Modelli open a prezzi bassi (llama, qwen, deepseek). A consumo."
    },
    {
        id: "baseten", label: "Baseten", env: "BASETEN_API_KEY",
        host: "inference.baseten.co", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: null, keyFmt: "Chiave alfanumerica lunga (senza prefisso fisso)",
        signup: "https://app.baseten.co/settings/api_keys",
        free: true, billed: true, verified: false,
        aliases: ["baseten", "base ten"],
        freeModels: ["(credito di prova su llama/qwen/deepseek)"],
        note: "Model APIs OpenAI-compat + possibilità di ospitare modelli tuoi. Credito di prova. " + NV
    },
    {
        id: "avian", label: "Avian.io", env: "AVIAN_API_KEY",
        host: "api.avian.io", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: null, keyFmt: "Chiave alfanumerica lunga (senza prefisso fisso)",
        signup: "https://avian.io/dashboard",
        free: false, billed: true, verified: false,
        aliases: ["avian", "avian io", "avian.io"],
        freeModels: [],
        note: "Inference veloce su modelli open. " + NV
    },
    {
        id: "parasail", label: "Parasail", env: "PARASAIL_API_KEY",
        host: "api.parasail.io", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: null, keyFmt: "Chiave alfanumerica lunga (senza prefisso fisso)",
        signup: "https://www.parasail.io/",
        free: true, billed: true, verified: false,
        aliases: ["parasail", "parasail io"],
        freeModels: ["(credito di prova, modelli open)"],
        note: "Serverless su GPU a basso costo, credito di prova. " + NV
    },
    {
        id: "ai21", label: "AI21 Jamba", env: "AI21_API_KEY",
        host: "api.ai21.com", chatPath: "/studio/v1/chat/completions", modelsPath: null,
        detect: null, keyFmt: "Chiave alfanumerica lunga (senza prefisso fisso)",
        signup: "https://studio.ai21.com/account/api-key",
        free: true, billed: true, verified: false,
        aliases: ["ai21", "ai21 labs", "jamba"],
        freeModels: ["jamba-mini (credito di prova)"],
        note: "Jamba (contesto lunghissimo). Credito di prova gratuito. " + NV
    },
    {
        id: "writer", label: "Writer Palmyra", env: "WRITER_API_KEY",
        host: "api.writer.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: null, keyFmt: "Chiave alfanumerica lunga (senza prefisso fisso)",
        signup: "https://app.writer.com/aistudio/organization/api-keys",
        free: true, billed: true, verified: false,
        aliases: ["writer", "writer ai", "palmyra"],
        freeModels: ["palmyra-x5 (credito di prova)"],
        note: "Palmyra X (buono sui testi lunghi). Credito di prova. " + NV
    },
    {
        id: "reka", label: "Reka AI", env: "REKA_API_KEY",
        host: "api.reka.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: null, keyFmt: "Chiave alfanumerica lunga (senza prefisso fisso)",
        signup: "https://platform.reka.ai/apikeys",
        free: false, billed: true, verified: false,
        aliases: ["reka", "reka ai", "reka core", "reka flash"],
        freeModels: [],
        note: "Reka Flash/Core (multimodale). " + NV
    },

    // ================= SENZA FILTRI / ROLEPLAY (uncensored) ==================
    {
        id: "nanogpt", label: "NanoGPT (senza filtri)", env: "NANOGPT_API_KEY",
        host: "nano-gpt.com", chatPath: "/api/v1/chat/completions", modelsPath: "/api/v1/models",
        detect: null, keyFmt: "Chiave alfanumerica lunga (senza prefisso fisso)",
        signup: "https://nano-gpt.com/api",
        free: false, billed: true, uncensored: true, verified: true,
        aliases: ["nanogpt", "nano gpt", "nano-gpt"],
        freeModels: ["(pay-per-prompt: anche modelli abliterated/uncensored)"],
        note: "Si paga a singolo prompt (pochi centesimi, carta o cripto) e include modelli SENZA FILTRI. Nessun abbonamento."
    },
    {
        id: "infermatic", label: "Infermatic / TotalGPT (RP senza filtri)", env: "INFERMATIC_API_KEY",
        host: "api.totalgpt.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: null, keyFmt: "Chiave alfanumerica lunga (senza prefisso fisso)",
        signup: "https://infermatic.ai/",
        free: false, billed: true, uncensored: true, verified: false,
        aliases: ["infermatic", "totalgpt", "total gpt", "infermatic ai"],
        freeModels: ["(abbonamento fisso: modelli RP/abliterated illimitati)"],
        note: "Abbonamento mensile fisso con modelli roleplay/abliterated (Midnight-Miqu, magnum...). " + NV
    },
    {
        id: "mancer", label: "Mancer (senza filtri)", env: "MANCER_API_KEY",
        host: "neuro.mancer.tech", chatPath: "/oai/v1/chat/completions", modelsPath: "/oai/v1/models",
        detect: null, keyFmt: "Chiave alfanumerica lunga (senza prefisso fisso)",
        signup: "https://mancer.tech/",
        free: false, billed: true, uncensored: true, verified: false,
        aliases: ["mancer", "mancer tech", "mancer ai"],
        freeModels: ["(a crediti: mytholite, weaver — nessun filtro)"],
        note: "Storico provider RP senza filtri, a crediti. Endpoint OpenAI-compat su /oai/v1. " + NV
    },
    {
        id: "targon", label: "Targon (Bittensor)", env: "TARGON_API_KEY",
        host: "api.targon.com", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^sn4_/, strong: true, keyFmt: "Inizia con sn4_ (es. sn4_xxxx)",
        signup: "https://targon.com/",
        free: true, billed: false, uncensored: true, verified: false,
        aliases: ["targon", "bittensor", "sybil", "manifold"],
        freeModels: ["deepseek-ai/DeepSeek-V3", "(modelli open serviti dai miner Bittensor)"],
        note: "Rete decentralizzata Bittensor: quota gratuita, nessun filtro aggiunto dal gateway. " + NV
    },
    {
        id: "nineteen", label: "Nineteen.ai (Bittensor)", env: "NINETEEN_API_KEY",
        host: "api.nineteen.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: null, keyFmt: "Chiave alfanumerica lunga (senza prefisso fisso)",
        signup: "https://nineteen.ai/app/api",
        free: true, billed: false, uncensored: true, verified: false,
        aliases: ["nineteen", "nineteen ai", "nineteen.ai", "sn19"],
        freeModels: ["unsloth/Llama-3.2-3B-Instruct", "(modelli open dai miner)"],
        note: "Gateway Bittensor con piano gratuito, modelli open senza filtri aggiuntivi. " + NV
    },
    {
        id: "redpill", label: "RedPill", env: "REDPILL_API_KEY",
        host: "api.redpill.ai", chatPath: "/v1/chat/completions", modelsPath: "/v1/models",
        detect: /^sk-/, keyFmt: "Inizia con sk-",
        signup: "https://red-pill.ai/",
        free: false, billed: true, uncensored: true, verified: false,
        aliases: ["redpill", "red pill", "red-pill"],
        freeModels: [],
        note: "Router (anche TEE/privacy) con modelli open non filtrati. " + NV
    }
];

/**
 * PIATTAFORME GPU aggiuntive (dove PORTI i tuoi modelli abliterated).
 * Stessa forma di gpuPlatforms.PLATFORMS: gpuPlatforms le fonde con le sue e
 * le sue vincono (Kaggle è cablata e ha lo stato live).
 */
const PLATFORMS_EXTRA = [
    {
        id: "beam", url: "https://www.beam.cloud/", name: "Beam Cloud (serverless GPU)",
        kind: "freemium", freeGpu: true, alwaysOn: false, uncensoredOk: true, remote: false,
        costo: "ore GPU gratis ogni mese sul free tier, poi a consumo al secondo",
        pros: [
            "Ore GPU gratis ogni mese senza carta",
            "Serverless: paghi solo i secondi di inferenza",
            "Container tuoi: nessun controllo sui modelli abliterated",
            "Deploy da CLI in un minuto"
        ],
        cons: [
            "Cold start di qualche decina di secondi",
            "Serve un token nel .env per accenderlo da remoto (non ancora cablato)"
        ],
        howto: "Da cablare: BEAM_TOKEN nel .env, deploy di un endpoint Ollama/vLLM e puntarlo al failover come Kaggle.",
        note: "Buon compromesso: gratis all'inizio e non si scollega come Colab."
    },
    {
        id: "cerebrium", url: "https://www.cerebrium.ai/", name: "Cerebrium (serverless GPU)",
        kind: "freemium", freeGpu: true, alwaysOn: false, uncensoredOk: true, remote: false,
        costo: "credito gratuito iniziale, poi fatturazione al secondo",
        pros: ["Credito iniziale gratis", "Scale-to-zero: spento non costa", "Modelli tuoi senza restrizioni"],
        cons: ["Finito il credito si paga", "Cold start", "Non ancora cablato in Antigravity"],
        howto: "Da cablare: deploy di un runtime vLLM/Ollama e puntarlo al failover.",
        note: "Alternativa a Modal, molto simile nell'uso."
    },
    {
        id: "koyeb", url: "https://www.koyeb.com/", name: "Koyeb (dominio stabile, GPU a consumo)",
        kind: "freemium", freeGpu: false, alwaysOn: true, uncensoredOk: true, remote: false,
        costo: "free tier solo CPU; GPU a consumo con scale-to-zero",
        pros: ["Servizi sempre accesi con dominio pubblico incluso (niente ngrok)", "Deploy da Git/Docker semplicissimo"],
        cons: ["Le GPU non sono gratis", "Sul free tier (CPU) girano solo modelli minuscoli"],
        howto: "Utile come PONTE stabile (dominio fisso) davanti a un backend GPU, al posto di ngrok.",
        note: "Da considerare per togliere di mezzo ngrok, più che per la GPU."
    },
    {
        id: "flyio", url: "https://fly.io/gpu", name: "Fly.io (GPU a consumo)",
        kind: "paid", freeGpu: false, alwaysOn: true, uncensoredOk: true, remote: false,
        costo: "GPU a ore, con macchine che si sospendono da sole quando sono inattive",
        pros: ["Macchine sospendibili: paghi solo quando servono", "Rete globale e dominio stabile", "Nessun limite sui modelli"],
        cons: ["Nessuna GPU gratis", "Serve carta di credito"],
        howto: "Da cablare: FLY_API_TOKEN nel .env per accendere/spegnere la macchina come Kaggle.",
        note: "Buono se vuoi un endpoint tuo affidabile pagando a ore."
    },
    {
        id: "tensordock", url: "https://tensordock.com/", name: "TensorDock (marketplace GPU)",
        kind: "paid", freeGpu: false, alwaysOn: true, uncensoredOk: true, remote: false,
        costo: "marketplace: prezzi molto bassi anche su 4090/A100",
        pros: ["Prezzi bassissimi", "VM complete: ci metti quello che vuoi", "Nessun limite sui modelli"],
        cons: ["A pagamento", "Affidabilità variabile (host indipendenti)", "Setup manuale"],
        howto: "Da cablare: API TensorDock per creare/distruggere la VM da remoto.",
        note: "Alternativa a Vast.ai, spesso con listino più chiaro."
    },
    {
        id: "jarvislabs", url: "https://jarvislabs.ai/", name: "JarvisLabs (GPU a ore, disco che resta)",
        kind: "paid", freeGpu: false, alwaysOn: false, uncensoredOk: true, remote: false,
        costo: "a ore (A5000/A6000), con pausa/riprendi",
        pros: ["Pausa e riprendi tenendo il disco: i modelli restano scaricati", "Semplice, orientato ai notebook", "API per accendere/spegnere"],
        cons: ["A pagamento", "Niente free tier"],
        howto: "Da cablare: JARVISLABS_API_KEY per accendere/spegnere e puntare al failover.",
        note: "Comodo perché il disco resta: non riscarichi 20 GB di modello ogni volta."
    },
    {
        id: "novita-gpu", url: "https://novita.ai/gpu-instance", name: "Novita GPU Instance",
        kind: "paid", freeGpu: false, alwaysOn: true, uncensoredOk: true, remote: false,
        costo: "a ore (4090/A100), fatturazione al minuto",
        pros: ["Stesso account che usi già per l'API Novita", "Template Ollama/vLLM pronti", "Modelli tuoi senza restrizioni"],
        cons: ["A pagamento", "Nessuna GPU gratis"],
        howto: "Da cablare: la chiave Novita che hai già serve anche per le istanze GPU.",
        note: "Se hai già la chiave Novita, è la strada più corta per una GPU 24/7."
    },
    {
        id: "sagemaker-lab", url: "https://studiolab.sagemaker.aws/", name: "Amazon SageMaker Studio Lab",
        kind: "free", freeGpu: true, alwaysOn: false, uncensoredOk: true, remote: false,
        costo: "0€ — sessioni GPU a tempo, nessuna carta di credito",
        pros: ["GPU gratis senza carta", "Ambiente persistente (il disco resta)", "Più stabile di Colab"],
        cons: ["Sessioni a tempo, poi va riavviato a mano", "Approvazione dell'account non immediata", "Non gestibile da remoto"],
        howto: "Alternativa gratuita a Kaggle quando la quota settimanale è finita.",
        note: "Ore GPU gratis in più, utili come riserva."
    },
    {
        id: "saturn", url: "https://saturncloud.io/", name: "Saturn Cloud (free GPU)",
        kind: "freemium", freeGpu: true, alwaysOn: false, uncensoredOk: true, remote: false,
        costo: "0€ — ore di calcolo gratis ogni mese (una parte su GPU)",
        pros: ["Ore GPU gratis al mese", "Ambienti Jupyter persistenti", "Niente carta per il free tier"],
        cons: ["Risorse gratis limitate e a volte in coda", "Non cablato in Antigravity"],
        howto: "Come Kaggle: notebook con Ollama + tunnel, da puntare al failover.",
        note: "Buona riserva quando Kaggle è a quota zero."
    },
    {
        id: "thunder", url: "https://www.thundercompute.com/", name: "Thunder Compute (GPU low cost)",
        kind: "paid", freeGpu: false, alwaysOn: true, uncensoredOk: true, remote: false,
        costo: "A100 virtualizzata a poche decine di centesimi l'ora, al minuto",
        pros: ["Tra i prezzi più bassi per una A100", "CLI semplice, istanze in pochi secondi", "Nessun limite sui modelli"],
        cons: ["A pagamento", "GPU virtualizzata: qualche punto percentuale di prestazioni in meno"],
        howto: "Da cablare: token nel .env per accendere/spegnere l'istanza.",
        note: "Se serve un modello 70B senza spendere come su AWS."
    },
    {
        id: "primeintellect", url: "https://www.primeintellect.ai/", name: "Prime Intellect (confronto prezzi GPU)",
        kind: "paid", freeGpu: false, alwaysOn: true, uncensoredOk: true, remote: false,
        costo: "aggregatore: prende il prezzo più basso tra molti fornitori",
        pros: ["Confronta i prezzi di molti fornitori in un unico posto", "API unica per accendere/spegnere", "Nessun limite sui modelli"],
        cons: ["A pagamento", "La qualità dipende dal fornitore che ti assegna"],
        howto: "Da cablare: API key per creare/distruggere l'istanza dal telefono.",
        note: "Comodo per trovare la GPU più economica disponibile al momento."
    },
    {
        id: "hyperstack", url: "https://www.hyperstack.cloud/", name: "Hyperstack (GPU europee)",
        kind: "paid", freeGpu: false, alwaysOn: true, uncensoredOk: true, remote: false,
        costo: "a ore (A100/H100), datacenter in Europa",
        pros: ["Datacenter europei: latenza bassa dall'Italia e dati in UE", "API completa per accendere/spegnere", "Modelli tuoi senza restrizioni"],
        cons: ["A pagamento", "Niente free tier"],
        howto: "Da cablare: HYPERSTACK_API_KEY nel .env.",
        note: "La scelta 'europea' se ti interessa dove stanno i dati."
    }
];

module.exports = { CATALOG, PLATFORMS_EXTRA };
