# Antigravity Unified Engine v4.0 - Architettura Completa

## 📋 Indice
- [Panoramica](#panoramica)
- [Struttura dei File](#struttura-dei-file)
- [Componenti Principali](#componenti-principali)
- [Sistema di Logging](#sistema-di-logging)
- [Orchestratori](#orchestratori)
- [Sistema di Agenti](#sistema-di-agenti)
- [CrewAI Architecture](#crewai-architecture)
- [Webview Interface](#webview-interface)
- [Comandi VSCode](#comandi-vscode)
- [Flusso di Esecuzione](#flusso-di-esecuzione)

---

## 🎯 Panoramica

Antigravity Unified Engine è un'estensione VSCode/VSCodium che fornisce un ecosistema AI completo con 14 agenti specializzati, multi-provider AI routing, e orchestratori avanzati.

**Versione:** 4.0.0  
**Publisher:** local-developer  
**Engine:** VSCode ^1.60.0  
**Linguaggio:** JavaScript (Node.js)

---

## 📁 Struttura dei File

```
antigravity-vscodium-extension/
├── extension.js                    # Punto di ingresso principale
├── package.json                    # Manifesto dell'estensione
├── interface.html                   # Webview UI
├── icon.svg                         # Icona SVG animata
├── icon.png                         # Icona principale
├── icon-16x16.png                   # Icona 16x16
├── icon-32x32.png                   # Icona 32x32
├── icon-48x48.png                   # Icona 48x48
├── icon-128x128.png                 # Icona 128x128
├── icon-256x256.png                 # Icona 256x256
├── generate-icons.js                # Script generazione icone
├── convert-icon.js                  # Script conversione icone
├── resize-icon.js                   # Script ridimensionamento icone
├── test-extension.js                # Test dell'estensione
├── settings.json                    # Configurazione predefinita
├── README.md                        # Documentazione principale
├── LICENSE                          # Licenza
├── node_modules/                    # Dipendenze
└── src/                             # Codice sorgente
    ├── agentFactory.js              # Factory per agenti Cloudflare
    ├── cloudDeployer.js             # Deploy su Cloudflare Workers
    ├── hiveCoordinator.js           # Coordinatore hive
    ├── orchestrator.js              # Orchestratore avanzato
    ├── orchestrator-crewai.js       # Orchestratore CrewAI
    ├── providerManager.js           # Gestione provider AI
    ├── agents/                      # 14 Agenti specializzati
    │   ├── analyzer.js              # Analizzatore codice
    │   ├── debugger.js              # Debugger esperto
    │   ├── deployer.js              # Deployer applicazioni
    │   ├── documenter.js            # Generatore documentazione
    │   ├── immune_guardian.js        # Guardian immunitario
    │   ├── indexer.js               # Indicizzatore progetto
    │   ├── integrator.js             # Integratore sistemi
    │   ├── liquid_programmer.js     # Programmatore liquido
    │   ├── optimizer.js             # Ottimizzatore codice
    │   ├── realtime_tester.js       # Tester real-time
    │   ├── sandbox_executor.js       # Esecutore sandbox
    │   ├── security.js              # Scanner sicurezza
    │   ├── subsystem_architect.js   # Architetto sottosistemi
    │   └── tester.js                # Tester automatizzato
    └── crewai/                      # Architettura CrewAI
        ├── Agent.js                 # Classe Agent
        ├── Crew.js                  # Classe Crew
        ├── LLM.js                   # Classe LLM
        ├── OutputParser.js          # Parser output
        ├── Process.js               # Classe Process
        ├── Task.js                  # Classe Task
        ├── Tool.js                  # Classe Tool
        └── index.js                 # Export moduli
```

---

## 🔧 Componenti Principali

### 1. extension.js
**Responsabilità:** Punto di ingresso principale dell'estensione

**Componenti:**
- `InternalLogger` - Sistema di logging strutturato
- `consoleChannel` - OutputChannel dedicato per logging
- `activate()` - Attivazione estensione
- `deactivate()` - Disattivazione estensione
- `processHiveRequest()` - Gestione richieste AI
- Gestione comandi VSCode
- Gestione webview provider
- Intercettazione errori runtime

### 2. package.json
**Responsabilità:** Manifesto dell'estensione

**Sezioni chiave:**
- `contributes.viewsContainers` - Container activity bar
- `contributes.views` - Webview chat
- `contributes.commands` - 14 comandi disponibili
- `dependencies` - Dipendenze (sharp per icone)

### 3. interface.html
**Responsabilità:** Interfaccia utente webview

**Componenti:**
- Chat interface
- Console interna con filtri
- Pannello raw code
- Stacktrace cliccabili
- Impostazioni
- Gestione messaggi

---

## 📊 Sistema di Logging

### InternalLogger
Classe centralizzata per logging strutturato:

```javascript
class InternalLogger {
    - entries: LogEntry[]           // Buffer log
    - listeners: Function[]          // Listener pattern
    
    + log(level, message, details)  // Log generico
    + debug(message, details)        // Log debug
    + info(message, details)         // Log info
    + warn(message, details)         // Log warning
    + error(message, details)       // Log error
    + onEntry(listener)              // Registra listener
    + getAll()                       // Tutti i log
    + filterByLevel(level)           // Filtra per livello
}
```

### LogEntry Structure
```typescript
interface LogEntry {
    level: 'debug' | 'info' | 'warn' | 'error'
    message: string
    details?: any
    timestamp: string
}
```

### OutputChannel
- Nome: "Antigravity Dev Console"
- Apertura automatica all'avvio
- Log formattati con timestamp e livello

---

## 🎼 Orchestratori

### AdvancedOrchestrator
**File:** `src/orchestrator.js`

**Responsabilità:** Orchestratore principale con 14 agenti

**Componenti:**
- `agents: Map` - Mappa agenti principali
- `subAgents: Map` - Mappa sub-agenti
- `taskQueue: Array` - Coda task
- `activeTasks: Map` - Task attivi
- `performanceMetrics: Map` - Metriche performance
- `knowledgeBase: Map` - Base conoscenza
- `projectIndex: Map` - Indice progetto
- `dependencyGraph: Map` - Grafo dipendenze
- `callGraph: Map` - Grafo chiamate
- `changeHistory: Array` - Storico modifiche

**Metodi chiave:**
- `initializeAgents()` - Inizializza 14 agenti
- `initializeSubAgents()` - Inizializza 12 sub-agenti
- `executeTask(task)` - Esegue task
- `breakDownTask(task)` - Spezza task complessi
- `analyzeDependencies()` - Analizza dipendenze
- `getProjectContext(task)` - Ottiene contesto progetto
- `recordChanges(task, changes)` - Registra modifiche
- `rollbackChanges(task, snapshot)` - Rollback modifiche

### CrewAIOrchestrator
**File:** `src/orchestrator-crewai.js`

**Responsabilità:** Orchestratore stile CrewAI

**Componenti:**
- `agents: Map` - Agenti CrewAI
- `tasks: Map` - Task CrewAI
- `crews: Map` - Crew CrewAI
- `activeCrew: Crew` - Crew attiva
- `llm: LLM` - LLM configurato

**Metodi chiave:**
- `initializeAgents()` - Inizializza agenti CrewAI
- `executeTask(task)` - Esegue task CrewAI
- `createCrew(agents, tasks)` - Crea crew
- `executeCrew(crew)` - Esegue crew

---

## 🤖 Sistema di Agenti

### 14 Agenti Specializzati

#### 1. Analyzer (`analyzer.js`)
**Specialità:** Analisi codice statica
- Analisi qualità codice
- Rilevamento anti-pattern
- Suggerimenti miglioramento

#### 2. Debugger (`debugger.js`)
**Specialità:** Debugging avanzato
- Analisi root cause
- Generazione fix
- Testing automatico

#### 3. Deployer (`deployer.js`)
**Specialità:** Deploy applicazioni
- CI/CD pipeline
- Configurazione deployment
- Monitoraggio deploy

#### 4. Documenter (`documenter.js`)
**Specialità:** Generazione documentazione
- Auto-doc da codice
- Generazione README
- API documentation

#### 5. Immune Guardian (`immune_guardian.js`)
**Specialità:** Protezione codice
- Rilevamento vulnerabilità
- Patch automatiche
- Monitoraggio sicurezza

#### 6. Indexer (`indexer.js`)
**Specialità:** Indicizzazione progetto
- Analisi struttura
- Mapping dipendenze
- Grafo chiamate

#### 7. Integrator (`integrator.js`)
**Specialità:** Integrazione sistemi
- Connessione API
- Configurazione servizi
- Gestione endpoint

#### 8. Liquid Programmer (`liquid_programmer.js`)
**Specialità:** Programmazione dinamica
- Code generation
- Refactoring automatico
- Ottimizzazione codice

#### 9. Optimizer (`optimizer.js`)
**Specialità:** Ottimizzazione performance
- Analisi performance
- Suggerimenti ottimizzazione
- Profiling

#### 10. Realtime Tester (`realtime_tester.js`)
**Specialità:** Testing real-time
- Test automatici
- Coverage analysis
- Regression testing

#### 11. Sandbox Executor (`sandbox_executor.js`)
**Specialità:** Esecuzione sicura
- Sandbox isolato
- Esecuzione codice
- Monitoraggio risorse

#### 12. Security (`security.js`)
**Specialità:** Sicurezza avanzata
- Security scanning
- Penetration testing
- Compliance check

#### 13. Subsystem Architect (`subsystem_architect.js`)
**Specialità:** Architettura sistemi
- Design pattern
- Microservices
- System architecture

#### 14. Tester (`tester.js`)
**Specialità:** Testing automatizzato
- Unit tests
- Integration tests
- E2E tests

### AgentFactory
**File:** `src/agentFactory.js`

**Responsabilità:** Compilazione agenti per Cloudflare Workers

**Metodo:**
```javascript
static compileAgent(agentType, taskDescription)
```

Genera codice Cloudflare Worker pronto per deployment.

---

## 🧠 CrewAI Architecture

### Componenti CrewAI

#### 1. Agent.js
**Classe:** `Agent`

**Proprietà:**
- `role: string` - Ruolo agente
- `goal: string` - Obiettivo
- `backstory: string` - Storia
- `tools: Tool[]` - Strumenti
- `llm: LLM` - LLM configurato

**Metodi:**
- `executeTask(task, context)` - Esegue task

#### 2. Task.js
**Classe:** `Task`

**Proprietà:**
- `description: string` - Descrizione
- `expectedOutput: string` - Output atteso
- `agent: Agent` - Agente assegnato
- `tools: Tool[]` - Strumenti
- `dependencies: Task[]` - Dipendenze
- `status: string` - Stato
- `result: any` - Risultato

**Metodi:**
- `execute(context)` - Esegue task
- `_estimateComplexity()` - Stima complessità
- `_checkDependencies(context)` - Controlla dipendenze

#### 3. Crew.js
**Classe:** `Crew`

**Proprietà:**
- `agents: Agent[]` - Agenti della crew
- `tasks: Task[]` - Task della crew
- `process: Process` - Processo di esecuzione

**Metodi:**
- `kickoff()` - Avvia crew
- `execute()` - Esegue crew

#### 4. Process.js
**Classe:** `Process`

**Tipi:**
- `sequential` - Esecuzione sequenziale
- `hierarchical` - Esecuzione gerarchica
- `parallel` - Esecuzione parallela

#### 5. LLM.js
**Classe:** `LLM`

**Proprietà:**
- `model: string` - Modello
- `temperature: number` - Temperatura
- `maxTokens: number` - Max tokens

**Metodi:**
- `complete(prompt)` - Completa prompt

#### 6. Tool.js
**Classe:** `Tool`

**Proprietà:**
- `name: string` - Nome
- `description: string` - Descrizione
- `func: Function` - Funzione

#### 7. OutputParser.js
**Classe:** `OutputParser`

**Metodi:**
- `parse(output)` - Parsa output

---

## 🖥️ Webview Interface

### interface.html
**Responsabilità:** Interfaccia utente principale

**Componenti:**
- Chat container
- Input area
- Console panel
- Raw code panel
- Settings panel
- Status indicator

### Funzionalità Console
- **Console:** Mostra tutti i log
- **Errori:** Filtra solo errori
- **Debug:** Filtra solo debug
- Stacktrace cliccabili
- Formattazione timestamp
- Dettagli JSON espandibili

### Comunicazione Extension ↔ Webview
```javascript
// Extension → Webview
webviewView.webview.postMessage({
    type: 'consoleLogs' | 'errorLogs' | 'debugLogs',
    entries: LogEntry[]
})

// Webview → Extension
vscode.postMessage({
    type: 'getConsoleLogs' | 'getErrorsOnly' | 'getDebugLogs',
    // ...
})
```

---

## ⌨️ Comandi VSCode

### Comandi Disponibili

1. **antigravity.focusChat** - Focus Antigravity Chat
2. **antigravity.clearChat** - Clear Chat History
3. **antigravity.reindexWorkspace** - Reindex Workspace
4. **antigravity.setOpenRouterKey** - Set OpenRouter API Key
5. **antigravity.setHuggingFaceKey** - Set Hugging Face API Key
6. **antigravity.setCloudflareKeys** - Set Cloudflare Account ID & API Key
7. **antigravity.discoverModels** - Discover Available Models
8. **antigravity.showStatus** - Show Orchestrator Status
9. **antigravity.autoOptimize** - Auto-Optimize Project
10. **antigravity.generateTests** - Generate Automated Tests
11. **antigravity.securityScan** - Deep Security Scan
12. **antigravity.predictiveAnalysis** - Predictive Analysis
13. **antigravity.autoRefactor** - Auto-Refactor Codebase
14. **antigravity.generateDocs** - Generate Documentation
15. **antigravity.performanceAudit** - Performance Audit

---

## 🔄 Flusso di Esecuzione

### 1. Attivazione Estensione
```
extension.js:activate()
├── Crea InternalLogger
├── Crea OutputChannel
├── Intercetta errori runtime
├── Inizializza AdvancedOrchestrator
├── Inizializza CrewAIOrchestrator
├── Registra comandi VSCode
├── Registra webview provider
└── Setup message handlers
```

### 2. Gestione Richiesta AI
```
processHiveRequest(prompt, context, webviewView, mode, provider, model)
├── logger.debug('Starting orchestrator execution')
├── Recupera API keys
├── Crea task
├── logger.debug('Starting orchestrator execution')
├── orchestrator.executeTask(task)
├── logger.debug('Orchestrator execution completed')
├── Gestisci risultato
└── Invia risposta a webview
```

### 3. Esecuzione Task
```
orchestrator.executeTask(task)
├── Analizza complessità
├── Spezza task se necessario
├── Seleziona agente appropriato
├── Esegue task
├── Registra modifiche
├── Aggiorna knowledge base
└── Restituisce risultato
```

### 4. Logging
```
InternalLogger.log(level, message, details)
├── Crea LogEntry
├── Aggiunge a buffer
├── Notifica listeners
├── Invia a OutputChannel
└── Disponibile per webview
```

### 5. Console Webview
```
loadConsoleLogs()
├── vscode.postMessage('getConsoleLogs')
├── extension.js: logger.getAll()
├── webviewView.webview.postMessage('consoleLogs')
├── formatLogEntries(entries)
└── Mostra in textarea
```

---

## 🔒 Gestione Storage

### Storage Directory
```javascript
this.storageDir = context.globalStorageUri.fsPath
```

### File Storage
- `project_index.json` - Indice progetto
- `knowledge_base.json` - Base conoscenza
- `change_history.json` - Storico modifiche

### Creazione Automatica
```javascript
if (!fs.existsSync(this.storageDir)) {
    fs.mkdirSync(this.storageDir, { recursive: true });
}
```

---

## 🚀 Deployment Cloudflare

### CloudDeployer
**File:** `src/cloudDeployer.js`

**Metodo:**
```javascript
static async deployToCloudflare(accountId, apiToken, workerName, script)
```

**Processo:**
1. Compila script agente
2. Invia a Cloudflare Workers
3. Configura environment variables
4. Restituisce URL worker

---

## 📡 Provider AI

### ProviderManager
**File:** `src/providerManager.js`

**Provider Supportati:**
- OpenRouter
- Hugging Face
- Cloudflare Workers

### Configurazione
```javascript
{
    openrouter: apiKey,
    huggingface: apiKey,
    cloudflareId: accountId,
    cloudflareToken: apiToken
}
```

---

## 🛠️ Utility Scripts

### generate-icons.js
Genera icone PNG da SVG in diverse dimensioni.

### convert-icon.js
Converte icone tra formati.

### resize-icon.js
Ridimensiona icone.

---

## 📝 Note Tecniche

### Error Handling
- Intercettazione `uncaughtException`
- Intercettazione `unhandledRejection`
- Try-catch in funzioni critiche
- Stacktrace dettagliati
- Logging strutturato

### Performance
- Caching file context
- Limitazione dimensione log
- Lazy loading agenti
- Parallel task execution

### Sicurezza
- Storage in globalStorageUri
- API keys in secrets
- Sandbox execution
- Security scanning

---

## 🎯 Roadmap

### v4.1 (Prossimo)
- [ ] Miglioramento UI webview
- [ ] Aggiunta più provider AI
- [ ] Ottimizzazione performance
- [ ] Enhanced security features

### v5.0 (Futuro)
- [ ] Supporto TypeScript
- [ ] Plugin system
- [ ] Distributed execution
- [ ] Advanced analytics

---

## 📚 Riferimenti

- [VSCode Extension API](https://code.visualstudio.com/api)
- [CrewAI Documentation](https://docs.crewai.com)
- [Cloudflare Workers](https://developers.cloudflare.com/workers)
- [OpenRouter API](https://openrouter.ai/docs)

---

**Versione Documento:** 1.0  
**Ultimo Aggiornamento:** 2026-06-18  
**Autore:** Antigravity Development Team
