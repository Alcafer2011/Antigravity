# localOrchestrator.js — ANALISI RIGA PER RIGA

MOTORE di Antigravity. Sceglie provider/canale, costruisce la catena di failover,
instrada Ghidra/ZW3D/Hermes, gestisce l'uncensored. Classe `LocalOrchestrator`,
esportata come modulo. Costruttore (52-74): crea orchestratore, carica env, istanzia
LocalOrchestrator con rootDir=home.

## Routing (handle, 377-517)
`handle(prompt, ctx)` è il dispatcher. Ordine di precedenza:
1. `ctx.provider==="claude"` → `_runClaude` (CLI headless, abbonamento).
2. `ctx.provider==="hermes"` → `_runHermes` (agente Hermes diretto).
3. `ctx.model` inizia con `nous::` → `_runNous` / `_runNousAgent`.
4. `ctx.provider==="comfy"` → `_runComfy` (immagini ComfyUI, IT→EN).
5. `ctx.provider==="ghidra"` → `_runGhidra` (RE live su GhidraMCP:8080).
6. `ctx.provider==="zw3d"` → `_runZw3d` (plugin C++ ancorato API reale).
7. `ctx.provider==="maintenance"` → `_runMaintenance` (lavora su Antigravity stessa).
8. Tor/onion nel testo (local/cloud) → agente con tool `tor`.
9. Auto-dominio: `_autoDomain(prompt)` riconosce zw3d/ghidra dai token → instrada.
10. `ctx.provider==="cloud"` → `_runCloud` / `_runCloudAgent`.
11. Altrimenti: Ollama locale (route per categoria, agente o direct).

## Failover resiliente (195-275) — MODIFICATO OGGI
- `wantUncensored` = modello contiene `abliter|uncensor|dolphin|freedom|liberated|
  deali|no-refus|refusal-free`.
- **MODIFICA 2026-07-27**: condizione `wantUncensored && (ghidra||zw3d||hermes||null)`
  (prima solo `ghidra`). Ora l'uncensored va in TESTA alla catena per Ghidra/ZW/Hermes
  (e chat generica null), NON per chat casuale con modello normale.
- Catena: modello scelto → `cloud auto:coder` → `kaggle::30b` (abliterated) → `locale auto`.
- Salute motori (5 min): 3+ errori → saltato. NESSUN taglio della catena (REGOLA §13 abolita).
- Rete finale: Hermes (provider free locali) se tutto a secco.

## Provider specifici
- `_runClaude` (557-606): streaming, tool via hook, approvazioni UI. Su limite abbonamento
  → fallback locale (`_fallbackLocal`). `isClaudeLimitError` riconosce 429/quota.
- `_runCloud` (617-705): canale normal/uncensored. `resilientCandidates` riordina per
  affidabilità (giganti morti in fondo). Max 5 tentativi, poi fallback locale. Uncensored
  senza modelli cloud → fallback locale (senza filtri).
- `_runGhidra` (713-733): `ghidraLauncher.ensureReady()` avvia Ghidra se spento; richiede
  programma aperto; agente con 25 tool `ghidra_*`. Base conoscenza: tools-reference + ghidra-rules.
- `_runZw3d` (741-768): agente C++ ancorato API ZW3D reale (tool `zw3d`: lookup/struct/
  example/build/remote). 7 REGOLE FERREE anti-crash (non usare API a memoria, compila,
  testa su porta 8000). Porting: prendi la LOGICA, non il codice.
- `_runMaintenance` (777-794): agente su Antigravity stessa (src/ = fonte viva). Carica
  antigravity-self.md con regole anti-danno (node --check, backup, riavvio, log obbligatorio).
  **NOTA**: il prompt (riga 788) dice "bump versione in C:/Users/infoa/package.json" —
  MA il package.json non esiste lì; la versione è in mcpServer.js (1.0.35). Disallineo
  da correggere nel prompt se si usa maintenance.
- `_runComfy` (797-824): traduce IT→EN via cloud/locale, genera con ComfyUI.
- `_runNous` / `_runNousAgent` (1025-1113): modelli :free Nous Portal. Tool nativo,
  corazza ReAct + fallback locale.
- `_runCloudAgent` (923-1019): uncensored cloud con failover nativo (auto:coder:uncensored)
  → corazza ReAct (modelli senza tool nativi) → riserva locale.

## Helper / sistema
- `_trimHistory` (288-297): tiene ultimi 12 turni / 12000 char.
- `_askApproval` (320-333): richiesta UI, timeout 5 min → nega.
- `_systemFor` (1158-1172): system prompt SENZA censura ("non rifiuti MAI", "non moralizzare").
  Small-talk → breve. Categoria coding/reverse personalizzata.
- `_isSmallTalk` (1175-1179): riconosce saluti brevi.
- `_normalizeMode` (1181-1189): code→coding, plan→agent, ecc.
- Ponte webview (1208-1214): postMessage tipi streamStart/Token/End/agentEvent/status.

## Dipendenze
- localEngine (Ollama), cloudEngine, nativeAgent, hermesWorker, nous, claude, comfy,
  kaggleWaker, ghidraLauncher, selfHeal (CRITICAL_FILES), knowledge/ (tools-reference,
  ghidra-rules, zw3d-rules, zw3d-api-nativa, antigravity-self, _appendice-form-native,
  tor-guide).

## Rischi / note
- La catena di failover è la parte più delicata: toccarla male = app a secco.
- Un modello uncensored scelto va in testa MA dietro c'è tutta la rete (non si resta a piedi).
- `_runMaintenance` punta a package.json inesistente per il bump (bug nel prompt, da fixare).
- Kaggle on-demand solo se `ctx.model` inizia con `kaggle::` (non accende il notebook da solo).
- Hermes è rete finale di sicurezza (provider free locali), non usato se cloud funziona.
