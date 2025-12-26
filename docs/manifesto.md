# 📜 AI Toolkit Manifesto

## 🎯 Main Principle

> **The project must remain clean for AI assistants**

---

## 🚫 Three Main Restrictions

### 1. Never create venv inside the project

**Bad:**
```
my_project/
├── venv/           ← 500 MB of junk
├── bot/
└── ...
```

**Good:**
```
projects/
├── _venvs/
│   └── my_project-venv/    ← Here!
└── my_project/
    ├── bot/
    └── ...
```

**Why?** AI (Cursor, Copilot) indexes all files. 500 MB of Python packages = slowdowns + noise in context.

---

### 2. Never read large files entirely

**Bad:**
```python
content = open("logs/bot.log").read()  # 100 MB in memory
```

**Good:**
```bash
tail -50 logs/bot.log
head -10 data/export.csv
sqlite3 db.sqlite3 ".schema"
```

**Why?** AI context is limited. 100 MB log = loss of important information.

---

### 3. Always check before creating

**Bad:**
```
Creating new file utils.py...
# But it already exists in bot/utils/
```

**Good:**
```
1. Read _AI_INCLUDE/WHERE_IS_WHAT.md
2. Check existing files
3. Create only if needed
```

---

## ✅ Correct Structure

```
project/
├── _AI_INCLUDE/              # Rules for AI
│   ├── PROJECT_CONVENTIONS.md
│   └── WHERE_IS_WHAT.md
├── .cursorrules              # Cursor
├── .cursorignore             # Cursor ignore
├── .github/
│   ├── copilot-instructions.md  # Copilot
│   └── workflows/            # CI/CD
├── CLAUDE.md                 # Claude
├── scripts/
│   ├── bootstrap.sh          # Create venv outside project
│   ├── health_check.sh       # Health check
│   └── context.py            # Context Switcher
├── bot/                      # Bot code
├── database/                 # Database
├── logs/                     # Logs (gitignored)
├── data/                     # Data (gitignored)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## 🎮 Context Switcher

When AI struggles on a large project:

```bash
python scripts/context.py bot     # Sees only bot/
python scripts/context.py webapp  # Sees only webapp/
python scripts/context.py all     # Sees everything
```

Updates `.cursorignore` to hide unnecessary modules.

---

## 🛡️ Protections

1. **pre-commit hook** — blocks commit if venv is in project
2. **health_check.sh** — verifies correct setup
3. **.cursorignore** — hides junk from AI

---

## 📋 New Project Checklist

- [ ] venv created in `../_venvs/`
- [ ] `_AI_INCLUDE/` exists
- [ ] `.cursorrules` configured
- [ ] `.cursorignore` configured
- [ ] `scripts/bootstrap.sh` works
- [ ] `.env` created from `.env.example`
- [ ] Git repository initialized
- [ ] `health_check.sh` passes
