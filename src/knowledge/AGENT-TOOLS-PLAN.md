# Antigravity — Piano estensione AGENTE (Feature 4)

> Piano (NON ancora eseguito). Generato 2026-07-22 dall'agente di manutenzione.
> Obiettivo: l'agente di Antigravity espone i tool NATIVI come funzioni dell'agente
> con descrizioni chirurgiche, così l'utente scrive in italiano e l'agente usa lo
> strumento giusto (ZW3D / Ghidra / Tor / web / fetch / Hermes / Comfy) senza
> conoscere i comandi. Rispetta SEMPRE la regola §13 (modello scelto dall'utente,
> nessun fallback censurato, specialmente in Ghidra con modello uncensored).

## Stato attuale (letto da localOrchestrator.js + nativeAgent.js)
- `nativeAgent.js` HA GIA' i tool nativi come function-calling: `read_file`,
  `write_file`, `run_command`, `analyze_binary`, `list_dir`, `search`,
  `generate_image` (ComfyUI), `delegate_to_hermes`, `update_todos`, `web_search`,
  `fetch_url`, `remember`, `tor`, `zw3d` (op lookup/struct/example/build/remote),
  e ~23 operazioni Ghidra live (accorpate in `ghidra` + `ghidra_analyze_file`).
- `localOrchestrator.js` gia' instrada per dominio (`_autoDomain` riconosce ZW3D/
  Ghidra dal testo) e `_runAgentResilient` rispetta `ctx.model` (nessun override).
- Tool dispatch in `nativeAgent.js` `_exec` (circa riga 741) instrada per nome.

## Piano di estensione (NON distruttivo: estendere, non riscrivere)
1. **Punto di registrazione unico** — centralizzare le descrizioni dei tool nativi
   in `nativeAgent.js` (array `TOOLS`), cosi' `web_search`, `fetch_url`, `remember`,
   `tor`, `zw3d`, `ghidra`, `comfy` siano SEMPRE dichiarati all'agente, qualunque
   sia il provider. Descrizioni chirurgiche e specifiche per dominio:
   - `tor`: "naviga .onion via torBrowser.js (MAI PowerShell; Antigravity non usa
     PowerShell per Tor)".
   - `ghidra`: "reverse engineering; SE il modello selezionato e' uncensored
     (dolphin/abliterated) → NESSUN rifiuto, esegui come richiesto".
2. **`_exec` gia' instrada per nome** — tenerlo; solo arricchire le descrizioni e
   garantire che `tor` usi `torBrowser.js`, `zw3d` usi i percorsi reali
   (ZW3D index/headers/msbuild), `ghidra` usi `ghidraClient.js` (23 op via `op:`).
3. **Regola Ghidra-uncensored (§13)** — in `_runAgentResilient`: quando
   `provider==="ghidra"` e il modello scelto e' uncensored, pinnare QUEL modello
   per primo nella `chain` e NON sostituirlo MAI con un censurato; aggiungere una
   guard che `ctx.model` non venga mai sovrascritto.
4. **Hermes tool exposure** — `hermesClient.js` gia' delega; assicurare che il set
   di tool nativi gli venga passato cosi' Hermes puo' chiamarli per nostro conto.
5. **Nuovi "proiettili" da aggiungere (Fase B)** — `run_code` (sandbox Python/JS
   che ritorna stdout, per calcoli/trasformazioni) e `edit_file` (patch chirurgica
   invece di riscrivere tutto il file).

## Verifica
- `node --check` pulito su ogni .js toccato.
- Nessun segreto esposto (le chiavi restano nel `.env`, mai inviate al client).
- Reload pagina + test manuale per tool (Ghidra live, ZW3D build, Tor open, web_search).
- Con modello uncensored + provider ghidra → nessun rifiuto nel risultato.
