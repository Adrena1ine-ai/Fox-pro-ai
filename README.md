# 🦊 Fox Pro AI

<div align="center">

**🦊 AI-Native Development Toolkit — Stop burning tokens on garbage. 99% context reduction for Cursor, Copilot, Claude. Smart project generator + code auditor.**

[![Version](https://img.shields.io/badge/version-4.0-blue.svg)](https://github.com/Adrena1ine-ai/Fox-pro-ai)
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)

* 🔒 100% local — code never leaves your machine
* 🔒 No API keys required for analysis
* 🔒 NDA/compliance safe
* 💰 99% reduction in token costs

</div>

---

## 💡 The Problem We Solve

Every AI coding assistant has the same problem:

```
Your actual code:     50 files
What AI sees:         47,000 files (venv, node_modules, cache, logs...)
What AI does:         Hallucinates, slow, confused
```

**Common "solutions" that don't scale:**

| Solution             | Works For      | Fails When                          |
| -------------------- | -------------- | ----------------------------------- |
| Manual .cursorignore | Small projects | Project grows, you forget to update |
| "Just ignore venv"   | Basic cases    | You have large JSON/CSV/SQLite data |
| Hope Cursor improves | Optimists      | You need it working today           |

**Fox Pro AI:**

* Automatically detects what's eating your tokens
* Moves heavy files externally AND patches your code
* Generates AI navigation maps (schema without data)
* Keeps everything in sync as project grows

---

## ✨ Features

### 🏗️ Project Generator

```bash
python main.py create my_bot --template bot
```

| Template | What You Get                                         |
| -------- | ---------------------------------------------------- |
| bot      | Telegram bot (aiogram) with handlers, keyboards, FSM |
| webapp   | Web app with Telegram WebApp SDK                     |
| fastapi  | REST API with routers, schemas, CRUD                 |
| parser   | Web scraper with httpx, BeautifulSoup                |
| full     | Everything above combined                            |
| monorepo | Multi-project setup with shared libs                 |

### 🩺 Doctor — One Command Fix

```bash
python main.py doctor /path/to/project --auto
```

| What It Finds               | What It Does           |
| --------------------------- | ---------------------- |
| 🔴 venv inside project      | Moves to ../_venvs/   |
| 🔴 node_modules/           | Suggests removal       |
| 🟡 __pycache__/ folders | Deletes                |
| 🟡 Large data files         | Moves + creates bridge |
| 🟡 Old logs                 | Archives               |
| 🟢 Missing AI configs       | Generates              |

### 🧹 Deep Clean — The Nuclear Option

```bash
python main.py doctor /path/to/project --deep-clean
```

**What happens:**

1. Scans for files over 1000 tokens
2. Moves them to external storage (`../project_data/`)
3. Creates `config_paths.py` bridge file
4. **Auto-patches your Python imports** (!)
5. Generates `AST_FOX_TRACE.md` — AI navigation map

**Before:**

```python
with open("data/users.json") as f:
    users = json.load(f)
```

**After (automatic!):**

```python
from config_paths import get_path
with open(get_path("data/users.json")) as f:
    users = json.load(f)
```

### 🦊 Fox Trace — Smart Context Extraction

```bash
python main.py trace src/handlers/payment.py --depth 2
```

Instead of sending entire project to AI, extracts:

* Only the file you're working on
* Only the functions it imports
* Only the schemas it uses

**Result:** 5.1M tokens → 13K tokens (99.7% reduction)

---

## 📋 All Commands

| Command                | What It Does                      |
| ---------------------- | --------------------------------- |
| create                 | Generate new AI-optimized project |
| doctor --report        | Show problems without fixing      |
| doctor --auto          | Fix everything automatically      |
| doctor --deep-clean    | Move heavy files + patch code     |
| doctor --garbage-clean | Remove temp/backup files          |
| doctor --restore       | Undo deep clean                   |
| trace                  | Extract minimal context for AI    |
| pack                   | Export context as XML             |
| review                 | Scan for secrets/API keys         |
| status                 | Generate project status doc       |

---

## 🤖 Supported AI Assistants

| Assistant          | Generated Configs                           |
| ------------------ | ------------------------------------------- |
| **Cursor**         | .cursorrules, .cursorignore, .cursor/rules/ |
| **GitHub Copilot** | .github/copilot-instructions.md             |
| **Claude**         | CLAUDE.md                                   |
| **Windsurf**       | .windsurfrules                              |

---

## 📁 What Gets Generated

```
my_project/
├── .cursor/rules/           # Modular Cursor rules
├── .github/workflows/       # CI/CD pipelines
├── _AI_INCLUDE/             # Shared AI context
├── scripts/
│   ├── bootstrap.sh         # Linux/Mac setup
│   ├── bootstrap.ps1        # Windows setup
│   └── context.py           # Context switcher
├── src/                     # Your code
├── .cursorrules             # Main Cursor config
├── .cursorignore            # Smart ignore (auto-updated)
├── CLAUDE.md                # Claude instructions
├── Dockerfile               # Container ready
└── docker-compose.yml       # Multi-container setup

# External (AI never sees these):
../_venvs/my_project/        # Dependencies
../my_project_data/          # Heavy files (after deep-clean)
```

---

## 🗺️ Roadmap

### ✅ Done (v4.0)

* Unified architecture — one command for everything
* Single path format (`../project_fox/`)
* Symlinks for dynamic paths
* Project generator with 6 templates
* Multi-IDE support (Cursor, Copilot, Claude, Windsurf)
* Doctor command with auto-fix
* Deep Clean with code auto-patching
* Fox Trace (AST-based context extraction)
* Garbage Clean (temp files removal)
* Integration tests

### 🔄 Next Up

| Priority | Feature                                       | Status   |
| -------- | --------------------------------------------- | -------- |
| 🔴       | **PyPI publication** (pip install fox-pro-ai) | Week 1   |
| 🔴       | Simplified CLI (fox doctor .)                 | Week 1   |
| 🟡       | Fox Deep Audit v1 (git diff + validation)     | Week 2-3 |
| 🟡       | Fox Deep Audit v2 (+ optional LLM review)     | Week 4-5 |

### 💡 Future (If There's Interest)

| Feature                        | What It Takes                        |
| ------------------------------ | ------------------------------------ |
| **VS Code / Cursor Extension** | TypeScript, VS Code API (1-2 months) |
| TUI Dashboard                  | Textual library (2-3 weeks)          |
| Web UI                         | Flask/FastAPI + React (1-2 months)   |

> **Note on Extension:** If this project gets traction and community interest, the next big step would be a VS Code/Cursor extension — a simple "Fox Clean" button in your IDE. This requires learning TypeScript and VS Code Extension API. Contributions welcome!

---

## 📊 Honest Expectations

This is a **niche tool**, not a revolution. It helps if you:

| ✅ Good Fit                           | ❌ Not Needed       |
| ------------------------------------ | ------------------ |
| Projects with 50+ files              | Small scripts      |
| Heavy data files (JSON, CSV, SQLite) | No data files      |
| Daily Cursor/Copilot user            | Occasional AI use  |
| Starting new projects regularly      | One-time project   |
| Team needing standards               | Solo hobby project |

**A good `.cursorignore` solves 80% of problems for 80% of people.** Fox Pro AI is for the other 20% — or for those who don't want to configure anything manually.

---

## 🧪 Testing

```bash
python -m pytest tests/ -v
python -m pytest tests/ --cov=src --cov-report=html
```

---

## 🚀 Quick Start

```bash
git clone https://github.com/Adrena1ine-ai/Fox-pro-ai.git
cd Fox-pro-ai
python -m venv ../_venvs/fox-pro-ai-dev
source ../_venvs/fox-pro-ai-dev/bin/activate  # or .ps1 on Windows
pip install -r requirements.txt
python -m pytest tests/ -v
```

---

## 🤝 Contributing

Areas where help is appreciated:

* PyPI packaging
* VS Code Extension (TypeScript)
* Documentation improvements
* Bug reports from real usage

---

## 📄 License

**AGPL-3.0** — Free to use, modify, distribute. If you build a commercial product with it, you must open-source your code too.

---

## 👤 Author

**Mickhael** — Solo developer from Russia

* Telegram: @MichaelSalmin
* Built with help from Claude (Anthropic)

---

## 🦊 Try It

```bash
git clone https://github.com/Adrena1ine-ai/Fox-pro-ai.git
cd Fox-pro-ai && pip install -r requirements.txt
python main.py doctor /your/project --report
```

**If it helps you — star ⭐ the repo**

**If it doesn't — tell me why**

---

_Built by one person. Tested with integration tests. Honest about what it does._
