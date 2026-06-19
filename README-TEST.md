# Guida Test Estensione Antigravity Unified Engine

## Test Ambiente Interno

### Risultati Test Automatici ✅

- **Struttura file**: Tutti i 24 file richiesti presenti
- **Sintassi JavaScript**: Tutti i file JavaScript verificati
- **Configurazione package.json**: Validato con repository e updateUrl
- **Comandi Ctrl+Shift+P**: 3 comandi API key configurati correttamente
- **PROJECT_INDEX.json**: Presente e aggiornato

### Come Testare l'Estensione Completa

#### Metodo 1: Debug in VSCode (Consigliato)

1. Apri questa cartella in VSCode:
   ```
   File > Open Folder
   Seleziona: C:\Users\infoa\.vscode-oss\extensions\local-developer.antigravity-unified-cascade-4.0.0
   ```

2. Premi **F5** per avviare il debug estensione
   - Si aprirà una nuova finestra VSCode "Extension Development Host"
   - L'estensione sarà caricata in questa finestra

3. Nella nuova finestra:
   - Apri Command Palette: **Ctrl+Shift+P**
   - Digita "Antigravity" per vedere i comandi disponibili:
     - `Antigravity: Set OpenRouter API Key`
     - `Antigravity: Set Hugging Face API Key`
     - `Antigravity: Set Cloudflare Account ID & API Key`
     - `Antigravity: Show Orchestrator Status`

4. Apri il pannello "Antigravity AI" dalla Activity Bar (sinistra)

#### Metodo 2: Installazione Manuale

1. Crea il pacchetto VSIX:
   ```bash
   npm install -g vsce
   vsce package
   ```

2. Installa in VSCode:
   - Apri Command Palette: **Ctrl+Shift+P**
   - Digita "Install from VSIX"
   - Seleziona il file `.vsix` generato

### Verifica Funzionamento

#### Test Comandi API Keys

1. **OpenRouter API Key**:
   - Ctrl+Shift+P → "Antigravity: Set OpenRouter API Key"
   - Inserisci: `sk-or-v1-...`
   - Verifica messaggio di conferma

2. **Hugging Face API Key**:
   - Ctrl+Shift+P → "Antigravity: Set Hugging Face API Key"
   - Inserisci: `hf_...`
   - Verifica messaggio di conferma

3. **Cloudflare Keys**:
   - Ctrl+Shift+P → "Antigravity: Set Cloudflare Account ID & API Key"
   - Inserisci Account ID
   - Inserisci API Token
   - Verifica messaggio di conferma

#### Test Interfaccia Chat

1. Apri il pannello "Antigravity AI Chat"
2. Scrivi un messaggio di test
3. Verifica che:
   - Lo stato venga aggiornato
   - La risposta venga visualizzata
   - Non ci siano errori nella console

### Monitoraggio Log

Per vedere i log dell'estensione:

1. Nella finestra Extension Development Host:
   - Apri Developer Tools: **Ctrl+Shift+I**
   - Vai alla tab "Console"
   - Cerca messaggi che iniziano con "Antigravity"

2. Nella finestra principale VSCode:
   - Apri Output panel: **Ctrl+Shift+U**
   - Seleziona "Extension Host" dal dropdown
   - Vedi log di caricamento estensione

### Risoluzione Problemi

#### Estensione non si carica
- Verifica che `package.json` sia valido
- Controlla che tutti i file siano presenti
- Apri Developer Tools per vedere errori

#### Comandi non appaiono
- Verifica che i comandi siano definiti in `package.json`
- Ricarica la finestra (Ctrl+R)
- Riavvia l'estensione (F5)

#### Errori API Keys
- Verifica che le chiavi siano salvate correttamente
- Controlla che i nomi dei secret siano corretti
- Riprova a inserire le chiavi

### Stato Attuale

✅ **Pronto per il test**
- Tutti i file presenti e validi
- Configurazione VSIX aggiornabile
- Comandi API key configurati
- Nuovi agenti implementati
- Sistema di test automatico funzionante

### Prossimi Passi

1. Esegui il test completo seguendo la guida sopra
2. Verifica che tutti i comandi funzionino
3. Testa l'interfaccia chat
4. Se tutto funziona, crea il pacchetto VSIX per distribuzione
