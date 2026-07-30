# comfyClient.js + webSearch.js + torBrowser.js — ANALISI RIGA PER RIGA

## comfyClient.js (212 righe)
Genera immagini con ComfyUI SENZA aprirlo: se spento lo avvia da solo.
- `HOST/PORT` = 127.0.0.1:8188. `COMFY_ROOT` (29): AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI, `COMFY_PY` = .venv\Scripts\python.exe. `COMFY_SHARED` = ComfyUI-Shared (output/modelli).
- `CHECKPOINT` (34) = realisticVisionV60B1_v51HyperVAE.safetensors. ⚠️ NOTA: il commento (riga 19-23) parla di "Realistic Vision V6 / SD 1.5", ma nativeAgent e i prompt dicono "Z-Image Turbo" — INCOERENZA DOC: il modello reale è Realistic Vision Hyper (SD1.5), non Z-Image. Se cambi modello, aggiorna CHECKPOINT + il check incompleteModels.
- `workflow` (40-58): grafo txt2img SD1.5 (CheckpointLoaderSimple → CLIPTextEncode x2 → EmptyLatentImage → KSampler dpmpp_sde+karras, 6 step, cfg 1.5 → VAEDecode → SaveImage).
- `incompleteModels` (99-115): controlla che il .safetensors non sia troncato (header dichiara byte pesi; se file più piccolo → incompleto). Evita errori criptici su tensori.
- `ensureUp` (122-148): se spento spawn main.py --port 8188 --base-directory COMFY_SHARED --disable-auto-launch (detached, unref). Aspetta 90×2s (3 min).
- `generate` (154-209): controlla modelli incompleti → ensureUp → POST /prompt → polling /history/id (150×2s = 5 min) → ritorna {file, filename}. width/height 256-1024, steps 1-20, cfg default 1.5.
- ⚠️ GPU = Quadro T1000 4GB: SD1.5 è scelta per la VRAM piccola.

## webSearch.js (282 righe)
Ricerca web riscritta il 2026-07-26 (scraping DDG morto → fonti che funzionano).
- `env` (38-53): legge chiavi da process.env o `../.env` (home) / `./.env`. ⚠️ .env HOME.
- `httpGet`/`httpJson` (56-96): helper HTTPS con redirect (4 hop) e timeout.
- `searchGitHub` (112-133): cerca repo via GITHUB_TOKEN (api.github.com/search/repositories). Toglie operatori site:/"" dalla query.
- `searchGrounded` (185-223): GEMINI_API_KEY/GOOGLE_API_KEY → Gemini con tool google_search; le CITAZIONI (groundingChunks) diventano i risultati. Cascata modelli (gemini-2.5-flash → 3.5-flash → 2.0-flash → flash-latest). `risolviTutti` (159-176) segue i redirect vertexaisearch (li rende URL veri) e deduplica.
- `searchDdg` (226-245): ULTIMO tentativo (oggi risponde 202 anti-bot). Regex sui result__a/result__snippet.
- `search` (253-266): se la query "sa di codice" (github|repo|plugin...) → prima GitHub, poi Google, poi DDG; altrimenti Google→GitHub→DDG. Si ferma alla prima fonte con risultati.
- `fetchPage` (269-280): scarica pagina, toglie script/style, stripTags, ritorna testo (max 8000 char).
- ⚠️ Dipende da GITHUB_TOKEN e GEMINI_API_KEY nel .env. Senza, la ricerca web è vuota.

## torBrowser.js (211 righe)
"Lettore" Tor lato server (sicurezza: niente JS, niente risorse esterne dal telefono).
- `TOR_DIR` = ~/tor-bundle, `TOR_EXE` = tor/tor.exe, `SOCKS` = 127.0.0.1:9050. `CURL` = System32\curl.exe (SOCKS5 nativo, zero npm).
- `available`/`isUp` (42-52): check.torproject.org/api/ip via curl --socks5-hostname → "IsTor":true.
- `ensureRunning` (58-81): spawn tor.exe (nascosto, detached) se non su, aspetta bootstrap 100% leggendo TOR_LOG (30×2s = 60s).
- `fetch` (87-112): curl --socks5-hostname, ritorna {ok, status, contentType, body(Buffer)}.
- `analyzeRisk` (125-159): PRE-ANALISI rischio (semi): download eseguibili (+2), password/cv/seed (+1/+2), wallet crypto (+1), JS offuscato (+1), redirect, termini mercato. level = pericolo (≥2) / attenzione / ok. NON è antivirus.
- `sanitize` (168-208): toglie script/style/link/iframe/object/embed/form, gestori on*, javascript:; riproxa le <img> via /tor/raw (Tor, no leak IP); riscrive i <a> con data-tor-url (click riapre dentro Tor, non Safari). toglie srcset/base/background.

## Dipendenze
- comfyClient: http, fs, os, path, child_process.
- webSearch: https, fs, path, url.
- torBrowser: child_process, path, os, fs.

## Rischi / note
- comfyClient.CHECKPOINT fisso: cambiare modello richiede di aggiornare il file e il check incompleteModels. Incoerenza doc (Z-Image vs Realistic Vision).
- webSearch funziona SOLO con GITHUB_TOKEN + GEMINI_API_KEY nel .env.
- torBrowser richiede ~/tor-bundle/tor/tor.exe installato; è un LETTORE (siti JS-heavy non funzionano).
