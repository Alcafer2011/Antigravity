# Agenti specializzati (sotto-agenti di Antigravity)

Idea dell'utente (2026-07-27): NON un unico mattone di istruzioni, ma UN direttore
(curatore) più sotto-agenti specializzati per i "mestieri pesanti". Il direttore
riceve la richiesta, capisce di che mestiere è, e carica SOLO il prompt mirato
del sotto-agente giusto. Così resta lucido e ogni specialista sa solo il suo.

Come funziona:
- `src/specialists.js` legge questi file e, dato il testo della richiesta,
  ritorna il blocco del sotto-agente rilevante (o "" se nessuno calza).
- `nativeAgent.js` (run/runReact) appende quel blocco al system prompt quando serve.
- Priorità: ghidra > zw3d > immagini > web (il primo che riconosce vince).

File:
- ghidra.md      — Reverse Engineering (decompilazione live via GhidraMCP)
- zw3d.md        — CAD ZW3D (API reale, generazione C++ funzionante)
- immagini.md    — Generazione immagini (ComfyUI / Realistic Vision SD1.5)
- web.md         — Ricerca web + Tor (.onion sicuro)

Sicurezza: se un file manca, il dispatcher ritorna "" e l'agente continua col
solo MANIFESTO + istruzioni vive (non si rompe mai).
