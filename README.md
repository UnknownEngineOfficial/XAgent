# X-Agent
Der XAgent ist ein autonomer, dauerhaft aktiver KI-Agent, der eigenständig denkt, plant und handelt. Er verarbeitet Befehle, trifft Entscheidungen, lernt aus Erfahrungen und interagiert kontinuierlich mit dem Nutzer. Voll integriert in APIs, Tools und Datenbanken arbeitet er entweder bis zur Zielerreichung oder kontinuierlich als Dauerauftrag.

# 🧠 Autonomer X-Agent
**WICHTIG: DER X-AGENT WIRD ALS EIGENES PROJEKT ENTWICKELT UND IN EINER EIGENEN REPO VERWALTET.**
## Übersicht

Der Autonome X-Agent ist eine Innovation von XTeam, die einen selbstständig denkenden, entscheidenden und arbeitenden Agent ermöglicht. Dieser Agent ist in der Lage, relativ alles uneingeschränkt zu können - sei es Coding, Planung, Analyse oder andere Aufgaben.

### Kernmerkmale

- **Autonome Arbeitsweise**: Der Agent arbeitet kontinuierlich bis zum expliziten Stopp durch den Nutzer
- **Vollständige Implementierung**: Keine halben Umsetzungen oder selbstauferlegte Einschränkungen
- **Interaktive Kommunikation**: Während der Arbeit können Infos gegeben, Kritik geäußert und Fragen gestellt werden
- **Flexible Anpassung**: Umgang mit allen Arten von Eingaben und freie Bewegung im Arbeitskontext

---

## 🧠 Theoretisches Funktionsmodell

### 1. Zielstruktur (Purpose Core)

Der Agent kann in zwei Modi arbeiten:

**A) Zielorientierter Modus**:
Aufträge werden in ein strukturiertes Zielsystem überführt:
- **Hauptziel (Mission)**: Die übergeordnete Aufgabe
- **Teilziele (Subtasks)**: Schrittweise Zerlegung der Mission
- **Erfolgskriterien (Completion Metrics)**: Messbare Kriterien für den Abschluss

**B) Dauerauftrag-Modus**:
Der Agent arbeitet kontinuierlich ohne definiertes Endziel:
- **Fortlaufende Aufgaben**: Überwachung, Wartung, kontinuierliche Verbesserung
- **Reaktive Arbeit**: Reagiert auf Events und Anfragen
- **Proaktive Optimierung**: Sucht selbstständig nach Verbesserungsmöglichkeiten

**Funktionsweise**:
- Der Agent arbeitet kontinuierlich, bis der Nutzer explizit "stoppt"
- Bei zielorientierten Aufträgen: "Bin ich näher am Ziel?" → Falls nicht, ändere Strategie
- Bei Daueraufträgen: "Gibt es etwas zu tun/verbessern?" → Falls ja, handle entsprechend

---

### 2. Kognitive Schleife (Cognitive Loop)

Diese Schleife läuft permanent, ähnlich einem Bewusstseins-Takt:

#### Perception (Wahrnehmung)
- Nimmt Befehle, Nachrichten, Daten, Umgebungszustände und API-Antworten auf
- Bewertet Relevanz (Signal vs. Rauschen)

#### Interpretation
- Versteht, was das bedeutet für aktuelle Ziele
- Nutzt semantische Modelle, logische Schlussfolgerung, Pattern-Matching

#### Planning (Handlungsentwurf)
- Erstellt Handlungsplan mit Prioritäten
- Nutzt Chain-of-Thought-ähnliche Planung, aber persistent

#### Execution (Ausführung)
- Führt Befehle aus, ruft Tools/APIs auf, schreibt Dateien, kommuniziert

#### Reflection (Selbstüberwachung)
- Bewertet Resultate, Fehler, Abweichungen
- Passt Strategien an, speichert Erkenntnisse in Memory

#### Loop-Back
- Wiederholt alles kontinuierlich

---

### 3. Gedächtnissystem (Memory Layer)

Mehrschichtig aufgebaut:

| Ebene | Funktion | Beispiel |
|-------|----------|----------|
| **Kurzzeit (RAM)** | Aktueller Kontext & laufende Tasks | Letzte 10 Aktionen |
| **Mittelzeit (Buffer)** | Projekthistorie, Zwischenziele | Zwischenberichte |
| **Langzeit (Knowledge Store)** | Alles Gelernte, Fakten, Nutzerpräferenzen | SQL/Vectorstore (z. B. Redis + Postgres + Chroma) |

**Integration**: Alle Ebenen werden über ein Embedding-System verknüpft (ähnlich LangChain Memory, aber persistent).

---

### 4. Kommunikationssystem (Interactive Layer)

- **Echtzeit-Eingabe**: Akzeptiert jederzeit neue Eingaben (Befehle, Fragen, Feedback)
- **Priorisierung**: Sofortige menschliche Interaktion über Hintergrundprozesse
- **Dialogfenster**: Mit der laufenden Cognitive Loop verknüpft (z. B. WebSocket-based Session)
- **Dynamische Anpassung**: Änderungen durch Nutzer → Re-Evaluation der Ziele in Echtzeit

---

### 5. Handlungsebene (Action Layer)

**Toolkits**:
- Coding
- Search
- OS
- Data-Ops
- Netzwerk

**Entscheidungsbaum**:
Jedes Tool hat definierte Fähigkeiten und Rückkanäle. Aktionen erfolgen nach internem Entscheidungsbaum:
1. Kann ich es selbst lösen?
2. Wenn nein: brauche ich ein Tool, Wissen oder Rückfrage?
3. Nach Ausführung → Rückmeldung an Memory und Nutzer

---

### 6. Metakognition (Selbstüberwachung)

- **Fehlerkennung**: Erkennt Fehlverhalten, Endlosschleifen, Sackgassen
- **Effektivitätsbewertung**: Bewertet Effektivität seiner Strategien (Meta-Scores)
- **Autonome Korrektur**: Korrigiert Pläne autonom, bevor externe Kontrolle nötig ist
- **Audit-Modul**: Optional, protokolliert alle Entscheidungen

---

### 7. Arbeitsmodus

| Modus | Beschreibung |
|-------|-------------|
| **Focus** | Arbeitet aktiv an einem Ziel (maximale Priorität) |
| **Interactive** | Reagiert live auf Nutzer und Kontextänderungen |
| **Idle/Background** | Wartet, überwacht, reflektiert, reorganisiert |
| **Emergency** | Fehler, Konflikt oder Sicherheitsverletzung erkannt → Selbststopp oder Eskalation |

---

### 8. Ethik- & Sicherheitskern

Selbst bei "uneingeschränktem" Verhalten:
- **Grenzen durch Policy-Layer**: Safety-Filter, Sandbox, Auth-Scope
- **Berechtigungskonzept**: Kein Zugriff außerhalb seiner Berechtigungen
- **Override-Option**: Optional für High-Trust-Betrieb

---

### 9. Emergente Intelligenz (Selbstverbesserung)

- **Mustererkennung**: Erkennt Muster über eigene Leistung
- **Strategieerweiterung**: Erweitert Strategien, verbessert Tool-Nutzung
- **Erfahrungsbasiertes Lernen**: Baut aus Erfahrung neue Entscheidungsmuster (rein algorithmisch, nicht biologisch)

---

## 🔄 Implementierungsstatus

**Status**: ✅ Implemented (v0.1.0)  
**Priorität**: High  
**Kategorie**: Backend/Frontend AI

---

## 🚀 Quick Start

### Installation

#### Using Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/UnknownEngineOfficial/X-Agent.git
cd X-Agent

# Copy environment file
cp .env.example .env

# Edit .env with your API keys
# Start all services
docker-compose up -d

# Access services:
# - REST API: http://localhost:8000
# - WebSocket: ws://localhost:8001
# - Prometheus: http://localhost:9090
```

#### Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run agent
python -m xagent.core.agent

# Or run CLI
python -m xagent.cli.main

# Or run API
uvicorn xagent.api.rest:app --host 0.0.0.0 --port 8000
```

### Usage Examples

#### CLI

```bash
python -m xagent.cli.main

# In CLI:
start Build a web application
goal Create REST API
status
command Add authentication
feedback Looks good
stop
```

#### REST API

```bash
# Start agent
curl -X POST http://localhost:8000/start

# Get status
curl http://localhost:8000/status

# Send command
curl -X POST http://localhost:8000/command \
  -H "Content-Type: application/json" \
  -d '{"command": "Create documentation"}'
```

#### Python API

```python
import asyncio
from xagent.core.agent import XAgent

async def main():
    agent = XAgent()
    await agent.initialize()
    await agent.start("Build a web scraper")
    
    status = await agent.get_status()
    print(status)
    
    await agent.stop()

asyncio.run(main())
```

---

## 📋 Implementation Status

### Phase 1: Grundarchitektur ✅
- [x] Design der Zielstruktur (Purpose Core)
- [x] Implementierung der kognitiven Schleife
- [x] Aufbau des mehrschichtigen Gedächtnissystems
- [x] Integration von Redis + Postgres + ChromaDB

### Phase 2: Kommunikation & Interaktion ✅
- [x] WebSocket-basiertes Kommunikationssystem
- [x] REST API für externe Kommunikation
- [x] CLI Interface
- [x] Dynamische Ziel-Re-Evaluation

### Phase 3: Handlung & Metakognition ✅
- [x] Tool-Integration (Think, Search, Code, File)
- [x] Tool Server Architektur
- [x] Selbstüberwachungs-Modul (Meta-Cognition)
- [x] Strukturiertes Logging-System

### Phase 4: Modi & Sicherheit ✅
- [x] Cognitive Loop States (Idle, Thinking, Acting, Reflecting)
- [x] Policy-Layer für Sicherheit
- [x] YAML-basierte Sicherheitsregeln
- [x] Sandboxing-Konzept

### Phase 5: Emergente Intelligenz 🔄
- [x] Mustererkennung über eigene Leistung
- [x] Meta-Score-System
- [ ] Strategieverbesserung (Advanced)
- [ ] Erfahrungsbasiertes Lernen mit RLHF

---

## 🏗️ Implementierte Architektur

Das X-Agent System ist vollständig implementiert gemäß der Spezifikation. Hier ist die realisierte Architektur:

### Kernkomponenten

```
┌─────────────────────────────────────┐
│ X-Agent Core                        │
│ ├─ Goal Engine ✅                   │
│ ├─ Cognitive Loop ✅                │
│ ├─ Memory Layer ✅                  │
│ ├─ Planner & Executor ✅            │
│ ├─ Meta-Cognition Monitor ✅        │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│ Tool Server ✅                      │
│ ├─ Think Tool                       │
│ ├─ Search Tool                      │
│ ├─ Code Tool                        │
│ ├─ File Tool                        │
│ └─ Sandbox Support                  │
└─────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────┐
│ I/O & Interface Layer ✅            │
│ ├─ WebSocket Gateway                │
│ ├─ REST API                         │
│ ├─ CLI Interface                    │
│ └─ Structured Logging               │
└─────────────────────────────────────┘
```

### Speicher-Architektur

| Ebene | Technologie | Zweck | Status |
|-------|-------------|-------|--------|
| **Kurzzeit** | Redis | Aktiver Kontext, laufende Tasks | ✅ |
| **Mittelzeit** | PostgreSQL | Projekthistorie, Sessions | ✅ |
| **Langzeit** | ChromaDB | Semantisches Wissen, Muster | ✅ |

### Kognitive Schleife

Implementiert als permanenter asynchroner Loop:

```
while not stopped:
    Perception    → Nimmt Inputs auf (Commands, Events, Feedback)
    Interpretation → Analysiert Kontext und Relevanz
    Planning       → Erstellt Handlungsplan mit Planner
    Execution      → Führt Plan aus via Executor
    Reflection     → Bewertet Ergebnis, aktualisiert Memory
```

### Security & Policy Layer

- **Policy-basierte Sicherheit**: YAML-konfigurierbare Regeln
- **Drei Aktionstypen**: `allow`, `block`, `require_confirmation`
- **Sandboxing**: Isolierte Tool-Ausführung
- **Audit-Trail**: Vollständiges Logging aller Aktionen

---

## 📚 Dokumentation

Detaillierte Dokumentation verfügbar:

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Vollständige Architektur-Dokumentation
- **[QUICKSTART.md](docs/QUICKSTART.md)**: Schnellstart-Anleitung mit Beispielen
- **API Docs**: http://localhost:8000/docs (nach Start)

### Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| Backend Core | Python 3.10+, FastAPI, asyncio |
| Memory | Redis, PostgreSQL, ChromaDB |
| Messaging | WebSocket, Celery (optional) |
| Agents/Planning | LangChain, LangGraph ready |
| Monitoring | Prometheus, structlog |
| Auth & Policies | JWT, YAML Policy Layer |
| Containerisierung | Docker, Docker Compose |

---

## ✅ Akzeptanzkriterien

Der Autonome X-Agent ist vollständig implementiert, wenn:
1. Agent kann kontinuierlich arbeiten ohne zu stoppen (außer bei explizitem Befehl)
2. Agent unterstützt sowohl zielorientierte Aufgaben als auch permanente Daueraufträge
3. Agent implementiert Aufgaben vollständig ohne Einschränkungen
4. Agent kann während der Arbeit auf Eingaben reagieren (Infos, Kritik, Fragen)
5. Kognitive Schleife läuft permanent und passt Strategien an
6. Gedächtnissystem speichert und nutzt Kontext über alle Ebenen
7. Tool-Integration funktioniert mit autonomen Entscheidungen
8. Selbstüberwachung erkennt und korrigiert Probleme
9. Alle Arbeitsmodi sind implementiert und funktional
10. Sicherheits- und Berechtigungssystem ist aktiv
11. Emergente Intelligenz verbessert Performance über Zeit
12. Agent erkennt und handhabt sowohl endliche als auch unendliche Aufgabentypen

---

## 🎯 Anwendungsfälle

### Use Case 1: Vollständige Projektentwicklung
**Eingabe**: "Entwickle eine vollständige E-Commerce-Plattform mit Zahlungsintegration"

**Verhalten**:
- Agent analysiert Anforderungen
- Erstellt Architektur
- Implementiert Features iterativ
- Schreibt Tests
- Behebt Fehler autonom
- Optimiert Performance
- Dokumentiert Code
- Arbeitet bis zur Produktionsreife

### Use Case 2: Interaktive Entwicklung mit Feedback
**Szenario**: Agent arbeitet an einer Webapp

**Interaktionen**:
- Nutzer: "Das Login-Design gefällt mir nicht"
- Agent: Passt Design an, aktualisiert Code
- Nutzer: "Füge Two-Factor-Authentication hinzu"
- Agent: Analysiert, plant, implementiert 2FA
- Nutzer: "Wie ist der Fortschritt?"
- Agent: Gibt Statusbericht mit Metriken

### Use Case 3: Kontinuierliche Verbesserung (Zielorientiert)
**Langzeit-Aufgabe**: "Verbessere dieses Projekt bis es produktionsreif ist"

**Agent-Aktivitäten**:
- Läuft kontinuierlich
- Führt Tests aus → Identifiziert Probleme → Behebt sie
- Überprüft Code-Qualität → Refactored Code
- Analysiert Performance → Optimiert Bottlenecks
- Prüft Sicherheit → Schließt Lücken
- Signalisiert Abschluss bei Erreichen aller Kriterien

### Use Case 4: Permanenter Wartungs-Agent (Dauerauftrag)
**Permanente Aufgabe**: "Überwache und warte dieses System kontinuierlich"

**Agent-Aktivitäten**:
- Läuft unbegrenzt im Hintergrund
- Überwacht System-Metriken und Logs
- Reagiert auf Fehler und Anomalien sofort
- Optimiert Performance proaktiv
- Aktualisiert Dependencies automatisch
- Führt regelmäßige Backups durch
- Erstellt periodische Berichte
- Arbeitet ohne definiertes Endziel - stoppt nur bei explizitem Befehl

---

## 🔗 Verknüpfung mit XTeam-Features

Der Autonome X-Agent integriert sich in bestehende XTeam-Features:

- **Feature 6.7**: Persistent Agent / Dauer-Agent
- **Feature 7.4**: Intelligentes Planungssystem (Idea-to-Plan)
- **Feature 6.1-6.6**: MetaGPT Integration & Agent Manager
- **Feature 4.1-4.3**: Real-time & WebSocket für Kommunikation
- **Feature 12**: Observability & Monitoring für Selbstüberwachung

---

## 🧪 Testing & Quality Assurance

X-Agent maintains comprehensive test coverage with a central control point for quality assurance.

### Test Coverage

- **Core Modules Coverage**: **97.15%** ✅ (exceeds 90% target)
- **Total Unit Tests**: 76 tests
- **Central Control**: `scripts/run_tests.py`

### Running Tests

```bash
# Using the central control script
python scripts/run_tests.py --core      # Show core modules coverage
python scripts/run_tests.py --report    # Generate HTML report
python scripts/run_tests.py --strict    # Enforce 90% threshold

# Using Make
make test                               # Run all tests
make test-cov                           # Run with coverage
make test-cov-report                    # Run with 90% threshold enforcement
```

For detailed testing documentation, see [docs/TESTING.md](docs/TESTING.md).

---

## 📚 Referenzen

- **FEATURES.md**: Hauptdokument für alle Features
- **docs/ENTWICKLUNGSSTAND.md**: Entwicklungsstatus
- **docs/ACTION_ITEMS.md**: Aktuelle Aufgaben
- **docs/TESTING.md**: Test coverage documentation

---

**Erstellt**: 2025-11-05  
**Status**: Konzeptdokument  
**Nächste Überprüfung**: Nach Architektur-Review
