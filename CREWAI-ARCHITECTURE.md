# CrewAI Architecture Implementation

## Overview
L'orchestratore è stato completamente riscritto seguendo esattamente l'architettura CrewAI, mantenendo la piena compatibilità con i pattern CrewAI ma rimanendo completamente modificabile per le esigenze del progetto.

## Componenti CrewAI Implementati

### 1. Agent Class (`src/crewai/Agent.js`)
**Proprietà CrewAI:**
- `role`: Ruolo dell'agente (es. "System Architect")
- `goal`: Obiettivo principale dell'agente
- `backstory`: Contesto e storia dell'agente
- `verbose`: Output dettagliato durante esecuzione
- `allowDelegation`: Permette delegazione di task ad altri agenti
- `tools`: Strumenti disponibili all'agente
- `llm`: Modello linguistico configurato
- `maxIter`: Numero massimo di iterazioni
- `maxRpm`: Limite richieste per minuto
- `memory`: Abilita memoria per l'agente

**Metodi:**
- `executeTask(task, context)`: Esegue un task
- `_shouldDelegate(task)`: Determina se delegare
- `_delegateTask(task, context)`: Delega task ad altro agente
- `_executeTools(task, context)`: Esegue strumenti
- `_generateResponse(task, context, toolsResults)`: Genera risposta LLM
- `getStatus()`: Ottiene stato agente
- `reset()`: Resetta stato agente

### 2. Task Class (`src/crewai/Task.js`)
**Proprietà CrewAI:**
- `description`: Descrizione del task
- `expectedOutput`: Output atteso
- `agent`: Agente assegnato
- `tools`: Strumenti per il task
- `asyncExecution`: Esecuzione asincrona
- `context`: Contesto aggiuntivo
- `outputFormat`: Formato output strutturato
- `callback`: Callback al completamento
- `dependencies`: Task dipendenti
- `maxRetries`: Numero massimo retry

**Metodi:**
- `execute(context)`: Esegue il task
- `_checkDependencies(context)`: Verifica dipendenze
- `addDependency(taskId)`: Aggiunge dipendenza
- `removeDependency(taskId)`: Rimuove dipendenza
- `getStatus()`: Ottiene stato task
- `reset()`: Resetta stato task
- `clone()`: Clona task

### 3. Process Class (`src/crewai/Process.js`)
**Tipi CrewAI:**
- `sequential`: Esecuzione sequenziale dei task
- `hierarchical`: Esecuzione gerarchica con manager agent

**Metodi:**
- `execute(context)`: Esegue il processo
- `_executeSequential(context)`: Esecuzione sequenziale
- `_executeHierarchical(context)`: Esecuzione gerarchica
- `_createExecutionPlan(managerAgent, tasks, context)`: Crea piano esecuzione
- `addTask(task)`: Aggiunge task
- `addAgent(agent)`: Aggiunge agente
- `on(event, callback)`: Imposta callback
- `getStatus()`: Ottiene stato processo
- `reset()`: Resetta processo

### 4. Crew Class (`src/crewai/Crew.js`)
**Proprietà CrewAI:**
- `agents`: Lista agenti
- `tasks`: Lista task
- `process`: Processo (sequential/hierarchical)
- `verbose`: Output dettagliato
- `memory`: Abilita memoria crew
- `cache`: Abilita cache
- `maxRpm`: Limite richieste per minuto
- `shareCrew`: Condivide crew tra task

**Metodi:**
- `kickoff(context)`: Avvia esecuzione crew
- `addAgent(agent)`: Aggiunge agente
- `addTask(task)`: Aggiunge task
- `setProcess(type)`: Imposta tipo processo
- `on(event, callback)`: Imposta callback
- `getStatus()`: Ottiene stato crew
- `getAgentByRole(role)`: Ottiene agente per ruolo
- `getTaskById(taskId)`: Ottiene task per ID
- `exportConfig()`: Esporta configurazione crew
- `reset()`: Resetta crew

### 5. Tool Class (`src/crewai/Tool.js`)
**Proprietà CrewAI:**
- `name`: Nome strumento
- `description`: Descrizione strumento
- `func`: Funzione esecuzione
- `argsSchema`: Schema argomenti
- `returnDirect`: Ritorna risultato diretto
- `handleToolError`: Gestisce errori

**Metodi:**
- `execute(task, context, args)`: Esegue strumento
- `validateArgs(args)`: Valida argomenti
- `getSchema()`: Ottiene schema strumento
- `clone()`: Clona strumento

**Decorator:**
- `@tool(name, description, argsSchema)`: Decoratore per creare tool da funzioni

### 6. LLM Class (`src/crewai/LLM.js`)
**Proprietà CrewAI:**
- `model`: Modello linguistico
- `temperature`: Temperatura generazione
- `maxTokens`: Token massimi
- `topP`: Top P sampling
- `frequencyPenalty`: Penalità frequenza
- `presencePenalty`: Penalità presenza
- `stop`: Sequenze stop

**Metodi:**
- `complete(prompt, options)`: Completa prompt
- `chat(messages, options)`: Chat completion
- `getUsage()`: Ottiene statistiche uso
- `resetUsage()`: Resetta statistiche

### 7. OutputParser Class (`src/crewai/OutputParser.js`)
**Tipi CrewAI:**
- `text`: Output testo semplice
- `json`: Output JSON strutturato
- `pydantic`: Output Pydantic-style
- `csv`: Output CSV
- `list`: Output lista

**Metodi:**
- `parse(text)`: Parsa output
- `getFormatInstructions()`: Ottiene istruzioni formato
- `_parseJson(text)`: Parsa JSON
- `_parsePydantic(text)`: Parsa Pydantic
- `_parseCsv(text)`: Parsa CSV
- `_parseList(text)`: Parsa lista
- `_validateSchema(data, schema)`: Valida schema

### 8. CrewAIOrchestrator (`src/orchestrator-crewai.js`)
**Funzionalità:**
- Gestione agenti CrewAI-style
- Gestione task CrewAI-style
- Gestione crew CrewAI-style
- Configurazione LLM
- Sistema tools integrato
- Memory management
- Callback system
- Project indexing
- Integrazione con VSCode

**Metodi:**
- `initializeAgents()`: Inizializza agenti
- `initializeTools()`: Inizializza tools
- `configureLLM(config)`: Configura LLM
- `createTask(config)`: Crea task
- `createCrew(config)`: Crea crew
- `executeTask(taskConfig, context)`: Esegue task
- `executeCrew(crewConfig, context)`: Esegue crew
- `getStatus()`: Ottiene stato orchestrator
- `reset()`: Resetta orchestrator

## Pattern CrewAI Supportati

### Sequential Process
```javascript
const crew = new Crew({
    agents: [agent1, agent2, agent3],
    tasks: [task1, task2, task3],
    process: new Process("sequential")
});
await crew.kickoff();
```

### Hierarchical Process
```javascript
const crew = new Crew({
    agents: [managerAgent, workerAgent1, workerAgent2],
    tasks: [task1, task2, task3],
    process: new Process("hierarchical")
});
await crew.kickoff();
```

### Tool Usage
```javascript
const tool = new Tool({
    name: 'read_file',
    description: 'Read a file',
    func: async (args, context) => { /* implementation */ }
});

agent.tools.push(tool);
```

### Memory
```javascript
const crew = new Crew({
    agents: agents,
    tasks: tasks,
    memory: true
});
```

### Callbacks
```javascript
crew.on('onAgentStart', async (agent, task, context) => {
    console.log(`Agent ${agent.role} starting task ${task.id}`);
});
```

## Customizzazione

Il framework è completamente modificabile:
- Tutte le classi possono essere estese
- Nuovi tools possono essere aggiunti
- Nuovi process types possono essere implementati
- LLM providers possono essere customizzati
- Memory strategies possono essere personalizzate

## Integrazione con Codice Esistente

L'orchestrator legacy (`src/orchestrator.js`) rimane disponibile per compatibilità, mentre il nuovo `CrewAIOrchestrator` fornisce la piena compatibilità CrewAI.

## Stato Implementazione

✅ **Completato:**
- Agent class (role, goal, backstory, tools, verbose, allowDelegation)
- Task class (description, expectedOutput, agent, tools, asyncExecution)
- Process class (sequential, hierarchical)
- Crew class (agents, tasks, process, verbose, memory)
- Tool class (name, description, function, argsSchema)
- LLM class (model, temperature, maxTokens)
- OutputParser class (text, json, pydantic, csv, list)
- CrewAIOrchestrator (integrazione completa)
- Tools integrati (file system, terminal, search)
- Memory management
- Callback system
- Extension integration

Il framework è ora identico a CrewAI in architettura e funzionalità, ma completamente personalizzabile per le esigenze del progetto.
