#!/usr/bin/env python3
"""
🦊 Fox Pro AI — Interactive Menu
Run with: python -m src.menu
"""
import os
import sys
import subprocess
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


class FoxMenu:
    """Interactive menu for Fox Pro AI."""
    
    def __init__(self):
        self.fox_home = Path(__file__).parent.parent.resolve()
        self.project_path = None
        self.language = "RU"  # RU or EN
    
    def clear_screen(self):
        """Clear terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        """Print Fox Pro AI header."""
        print()
        print("╔══════════════════════════════════════════════════════════════════╗")
        print("║  🦊 FOX PRO AI — Professional AI-Native Development Toolkit      ║")
        print("║     Smart tools for smart developers                             ║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        print()
    
    def get_project_path(self):
        """Get project path from user."""
        if self.project_path:
            return self.project_path
        
        if self.language == "EN":
            print("📁 Enter project path (or press Enter for current directory):")
        else:
            print("📁 Введите путь к проекту (или Enter для текущей директории):")
        
        print(f"   Example: C:\\Users\\YourName\\Projects\\MyBot")
        print()
        
        path = input("   Path/Путь: ").strip()
        
        if not path:
            path = os.getcwd()
        
        # Validate path
        if not os.path.exists(path):
            print(f"\n❌ Path not found: {path}")
            input("\nPress Enter...")
            return None
        
        self.project_path = os.path.abspath(path)
        return self.project_path
    
    def run_command(self, *args):
        """Run Fox Pro AI CLI command."""
        cmd = [sys.executable, "-m", "src.cli"] + list(args)
        print(f"\n🔧 Running: {' '.join(cmd)}\n")
        print("─" * 60)
        
        try:
            result = subprocess.run(cmd, cwd=str(self.fox_home))
            return result.returncode == 0
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False
    
    def show_menu(self):
        """Display main menu."""
        self.clear_screen()
        self.print_header()
        
        if self.project_path:
            print(f"📂 Project: {self.project_path}")
        else:
            print("📂 Project: (not selected)")
        print()
        
        if self.language == "EN":
            menu = """
╔══════════════════════════════════════════════════════════════╗
║  Select action:                                              ║
╠══════════════════════════════════════════════════════════════╣
║  1. 🔍 Diagnose project                                      ║
║  2. 🔧 Auto-fix issues                                       ║
║  3. 🧹 Deep Clean (move heavy files)                         ║
║  4. 🗑️  Garbage Clean (temp files)                           ║
║  5. 📊 Update documentation                                  ║
║  6. 🔄 Restore from Deep Clean                               ║
║  7. 📝 Show project status                                   ║
║  8. 🏗️  Architect (restructure)                              ║
║  9. 🚀 FULL HEAL (all at once)                               ║
║ ──────────────────────────────────────────────────────────── ║
║ 10. 📖 Help                                                  ║
║ 11. 🔄 Change project                                        ║
║ 12. 🌐 Switch language                                       ║
║  0. ❌ Exit                                                   ║
╚══════════════════════════════════════════════════════════════╝
"""
        else:
            menu = """
╔══════════════════════════════════════════════════════════════╗
║  Выберите действие:                                          ║
╠══════════════════════════════════════════════════════════════╣
║  1. 🔍 Диагностика проекта                                   ║
║  2. 🔧 Авто-исправление                                      ║
║  3. 🧹 Deep Clean (тяжелые файлы)                            ║
║  4. 🗑️  Garbage Clean (временные файлы)                      ║
║  5. 📊 Обновить документацию                                 ║
║  6. 🔄 Восстановить из Deep Clean                            ║
║  7. 📝 Статус проекта                                        ║
║  8. 🏗️  Architect (реструктуризация)                         ║
║  9. 🚀 ПОЛНОЕ ЛЕЧЕНИЕ                                        ║
║ ──────────────────────────────────────────────────────────── ║
║ 10. 📖 Справка                                               ║
║ 11. 🔄 Сменить проект                                        ║
║ 12. 🌐 Сменить язык                                          ║
║  0. ❌ Выход                                                  ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(menu)
        
        prompt = "Your choice (0-12): " if self.language == "EN" else "Ваш выбор (0-12): "
        return input(prompt).strip()
    
    def action_diagnose(self):
        """Run project diagnosis."""
        if not self.get_project_path():
            return
        
        self.clear_screen()
        print("\n🔍 Diagnosing project..." if self.language == "EN" else "\n🔍 Диагностика проекта...")
        self.run_command("doctor", self.project_path, "--report")
        input("\nPress Enter to continue..." if self.language == "EN" else "\nНажмите Enter...")
    
    def action_auto_fix(self):
        """Run auto-fix."""
        if not self.get_project_path():
            return
        
        self.clear_screen()
        print("\n🔧 Auto-fixing..." if self.language == "EN" else "\n🔧 Авто-исправление...")
        self.run_command("doctor", self.project_path, "--auto")
        input("\nPress Enter to continue..." if self.language == "EN" else "\nНажмите Enter...")
    
    def action_deep_clean(self):
        """Run deep clean with options."""
        if not self.get_project_path():
            return
        
        self.clear_screen()
        print("\n🧹 Deep Clean")
        print()
        
        if self.language == "EN":
            print("  1. Preview (dry-run)")
            print("  2. Execute")
            print("  3. Custom threshold")
            choice = input("\nYour choice (1-3): ").strip()
        else:
            print("  1. Предпросмотр (dry-run)")
            print("  2. Выполнить")
            print("  3. Свой порог токенов")
            choice = input("\nВаш выбор (1-3): ").strip()
        
        if choice == "1":
            self.run_command("doctor", self.project_path, "--deep-clean", "--dry-run")
        elif choice == "2":
            self.run_command("doctor", self.project_path, "--deep-clean", "--auto")
        elif choice == "3":
            threshold = input("Threshold/Порог (default 1000): ").strip() or "1000"
            self.run_command("doctor", self.project_path, "--deep-clean", "--threshold", threshold, "--auto")
        
        input("\nPress Enter to continue..." if self.language == "EN" else "\nНажмите Enter...")
    
    def action_garbage_clean(self):
        """Run garbage clean."""
        if not self.get_project_path():
            return
        
        self.clear_screen()
        print("\n🗑️  Garbage Clean")
        print()
        
        if self.language == "EN":
            print("  1. Preview (dry-run)")
            print("  2. Execute")
            choice = input("\nYour choice (1-2): ").strip()
        else:
            print("  1. Предпросмотр (dry-run)")
            print("  2. Выполнить")
            choice = input("\nВаш выбор (1-2): ").strip()
        
        if choice == "1":
            self.run_command("doctor", self.project_path, "--garbage-clean", "--dry-run")
        elif choice == "2":
            self.run_command("doctor", self.project_path, "--garbage-clean", "--auto")
        
        input("\nPress Enter to continue..." if self.language == "EN" else "\nНажмите Enter...")
    
    def action_update_docs(self):
        """Update documentation."""
        if not self.get_project_path():
            return
        
        self.clear_screen()
        print("\n📊 Updating documentation..." if self.language == "EN" else "\n📊 Обновление документации...")
        self.run_command("status", self.project_path)
        input("\nPress Enter to continue..." if self.language == "EN" else "\nНажмите Enter...")
    
    def action_restore(self):
        """Restore from deep clean."""
        if not self.get_project_path():
            return
        
        self.clear_screen()
        print("\n🔄 Restoring..." if self.language == "EN" else "\n🔄 Восстановление...")
        self.run_command("doctor", self.project_path, "--restore")
        input("\nPress Enter to continue..." if self.language == "EN" else "\nНажмите Enter...")
    
    def action_status(self):
        """Show project status."""
        if not self.get_project_path():
            return
        
        self.clear_screen()
        print("\n📝 Project status..." if self.language == "EN" else "\n📝 Статус проекта...")
        self.run_command("status", self.project_path, "--preview")
        input("\nPress Enter to continue..." if self.language == "EN" else "\nНажмите Enter...")
    
    def action_architect(self):
        """Run architect command."""
        if not self.get_project_path():
            return
        
        self.clear_screen()
        print("\n🏗️  Restructuring..." if self.language == "EN" else "\n🏗️  Реструктуризация...")
        self.run_command("architect", self.project_path)
        input("\nPress Enter to continue..." if self.language == "EN" else "\nНажмите Enter...")
    
    def action_full_heal(self):
        """Run full heal - all optimizations."""
        if not self.get_project_path():
            return
        
        self.clear_screen()
        
        if self.language == "EN":
            print("\n🚀 FULL HEAL")
            print("\nThis will run ALL optimizations:")
            print("  1. Diagnose")
            print("  2. Auto-fix")
            print("  3. Garbage Clean")
            print("  4. Deep Clean")
            print("  5. Update docs")
            confirm = input("\nContinue? (y/N): ").strip().lower()
        else:
            print("\n🚀 ПОЛНОЕ ЛЕЧЕНИЕ")
            print("\nБудут выполнены ВСЕ оптимизации:")
            print("  1. Диагностика")
            print("  2. Авто-исправление")
            print("  3. Garbage Clean")
            print("  4. Deep Clean")
            print("  5. Обновление документации")
            confirm = input("\nПродолжить? (y/N): ").strip().lower()
        
        if confirm != 'y':
            return
        
        steps = [
            ("1/5 Diagnose" if self.language == "EN" else "1/5 Диагностика", 
             ["doctor", self.project_path, "--report"]),
            ("2/5 Auto-fix" if self.language == "EN" else "2/5 Авто-исправление", 
             ["doctor", self.project_path, "--auto"]),
            ("3/5 Garbage Clean", 
             ["doctor", self.project_path, "--garbage-clean", "--auto"]),
            ("4/5 Deep Clean", 
             ["doctor", self.project_path, "--deep-clean", "--auto"]),
            ("5/5 Update docs" if self.language == "EN" else "5/5 Документация", 
             ["status", self.project_path]),
        ]
        
        for step_name, cmd_args in steps:
            print(f"\n{'═' * 60}")
            print(f"  {step_name}")
            print(f"{'═' * 60}")
            self.run_command(*cmd_args)
        
        print(f"\n{'═' * 60}")
        print("  ✅ FULL HEAL COMPLETE!" if self.language == "EN" else "  ✅ ПОЛНОЕ ЛЕЧЕНИЕ ЗАВЕРШЕНО!")
        print(f"{'═' * 60}")
        
        input("\nPress Enter to continue..." if self.language == "EN" else "\nНажмите Enter...")
    
    def action_help(self):
        """Show complete help with full descriptions."""
        self.clear_screen()
        
        if self.language == "EN":
            help_text = """
╔══════════════════════════════════════════════════════════════╗
║  📖 COMPLETE DESCRIPTION OF ALL FOX PRO AI FUNCTIONS      ║
╚══════════════════════════════════════════════════════════════╝


┌──────────────────────────────────────────────────────────────┐
│ 1. 🔍 PROJECT DIAGNOSIS (doctor --report)                    │
└──────────────────────────────────────────────────────────────┘

   Scans the project and identifies issues affecting AI work.

   Checks:
   • Virtual environments inside project (venv/, .venv/)
   • Python cache (__pycache__/)
   • Logs (logs/, *.log)
   • node_modules/ inside project
   • Large data files (>1MB: .csv, .db, .sqlite, .json)
   • Artifacts (*FULL_PROJECT*.txt, *_DUMP.txt)
   • Large documents/logs (.md >50KB)
   • Missing _AI_INCLUDE/, .cursorignore, bootstrap scripts

   Mode: Analysis only, no changes.


┌──────────────────────────────────────────────────────────────┐
│ 2. 🔧 AUTO-FIX ISSUES (doctor --auto)                        │
└──────────────────────────────────────────────────────────────┘

   Runs diagnosis and automatically fixes found issues.

   Fixes:
   • Moves venv/ to ../_venvs/PROJECT_NAME-main/
   • Removes __pycache__/ (moves to archive)
   • Archives logs/ to ../_FOR_DELETION/PROJECT_NAME/logs/
   • Moves scattered .log files to archive
   • Adds node_modules/ to .cursorignore
   • Moves large data files to ../_data/
   • Archives artifacts
   • Creates _AI_INCLUDE/, .cursorignore, bootstrap scripts

   Safety: Creates backup before changes.


┌──────────────────────────────────────────────────────────────┐
│ 3. 🧹 DEEP CLEAN - Move Heavy Files                          │
│    (doctor --deep-clean)                                     │
└──────────────────────────────────────────────────────────────┘

   Optimizes project for AI: moves heavy files and updates code.

   Process (6 steps):
   1. Scanning - finds files with tokens > threshold (1000)
   2. Moving files to ../PROJECT_NAME_data/
   3. Generating bridge (config_paths.py)
   4. Code patching - automatically updates file usage
   5. Generating navigation map (AST_FOX_TRACE.md)
   6. Updating Cursor rules

   Result: 70-95% token reduction, project remains functional.


┌──────────────────────────────────────────────────────────────┐
│ 4. 🗑️  MOVE GARBAGE FILES TO GARBAGE                        │
│    (doctor --garbage-clean)                                  │
└──────────────────────────────────────────────────────────────┘

   Finds and moves temporary/old files.

   Searches for:
   • *.tmp, *.temp, *.bak, *.old, *.backup
   • *.log.old, *.log.* (rotated logs)
   • .DS_Store, Thumbs.db, desktop.ini
   • *_backup.*, *_old.*
   • tmp/, temp/, .tmp/ (directories)
   • Old logs (older than 30 days)

   Destination: ../PROJECT_NAME_garbage_for_removal/


┌──────────────────────────────────────────────────────────────┐
│ 5. 📊 UPDATE DOCUMENTATION (status)                          │
└──────────────────────────────────────────────────────────────┘

   Generates/updates PROJECT_STATUS.md and CURRENT_CONTEXT_MAP.md.

   PROJECT_STATUS.md:
   • Project structure
   • File statistics
   • Dependencies
   • Test results

   CURRENT_CONTEXT_MAP.md:
   • Context map for AI
   • Key files and their purpose
   • Project architecture


┌──────────────────────────────────────────────────────────────┐
│ 6. 🔄 RESTORE FILES FROM DEEP CLEAN (--restore)             │
└──────────────────────────────────────────────────────────────┘

   Reverts Deep Clean changes, returning project to original state.

   Process:
   1. Restores files from manifest.json
   2. Reverts code patches from .bak files
   3. Removes generated files


┌──────────────────────────────────────────────────────────────┐
│ 7. 📝 SHOW PROJECT STATUS (status)                          │
└──────────────────────────────────────────────────────────────┘

   Shows current project state:
   • Project path
   • File count
   • Project size
   • Found issues (if any)
   • Test status


┌──────────────────────────────────────────────────────────────┐
│ 8. 🏗️  ARCHITECTURAL RESTRUCTURING (architect)             │
└──────────────────────────────────────────────────────────────┘

   Restructures project according to AI-Native principles.

   Process:
   1. Creating bridge (config_paths.py)
   2. Moving heavy folders (venv/ → ../_venvs/)
   3. Moving data (*.json, *.csv, *.db → ../_data/)
   4. Updating startup scripts
   5. Updating .cursorignore


┌──────────────────────────────────────────────────────────────┐
│ 9. 🚀 FULL HEAL (all capabilities)                          │
└──────────────────────────────────────────────────────────────┘

   Performs full project optimization with all available tools:

   Steps:
   1. Project diagnosis
   2. Auto-fix issues
   3. Move garbage files
   4. Deep Clean - move heavy files
   5. Update documentation

   This is the most complete project optimization for AI work.


════════════════════════════════════════════════════════════════
"""
        else:
            help_text = """
╔══════════════════════════════════════════════════════════════╗
║  📖 ПОЛНОЕ ОПИСАНИЕ ВСЕХ ФУНКЦИЙ FOX PRO AI                  ║
╚══════════════════════════════════════════════════════════════╝


┌──────────────────────────────────────────────────────────────┐
│ 1. 🔍 ДИАГНОСТИКА ПРОЕКТА (doctor --report)                 │
└──────────────────────────────────────────────────────────────┘

   Сканирует проект и выявляет проблемы, влияющие на работу с AI.

   Проверяет:
   • Виртуальные окружения внутри проекта (venv/, .venv/)
   • Кэш Python (__pycache__/)
   • Логи (logs/, *.log)
   • node_modules/ внутри проекта
   • Большие файлы данных (>1MB: .csv, .db, .sqlite, .json)
   • Артефакты (*FULL_PROJECT*.txt, *_DUMP.txt)
   • Большие документы/логи (.md >50KB)
   • Отсутствие _AI_INCLUDE/, .cursorignore, bootstrap-скриптов

   Режим: Только анализ, без изменений.


┌──────────────────────────────────────────────────────────────┐
│ 2. 🔧 АВТО-ИСПРАВЛЕНИЕ ПРОБЛЕМ (doctor --auto)                │
└──────────────────────────────────────────────────────────────┘

   Выполняет диагностику и автоматически исправляет найденные проблемы.

   Исправления:
   • Перемещает venv/ в ../_venvs/PROJECT_NAME-main/
   • Удаляет __pycache__/ (переносит в архив)
   • Архивирует logs/ в ../_FOR_DELETION/PROJECT_NAME/logs/
   • Перемещает разрозненные .log в архив
   • Добавляет node_modules/ в .cursorignore
   • Перемещает большие файлы данных в ../_data/
   • Архивирует артефакты
   • Создает _AI_INCLUDE/, .cursorignore, bootstrap-скрипты

   Безопасность: Создает резервную копию перед изменениями.


┌──────────────────────────────────────────────────────────────┐
│ 3. 🧹 DEEP CLEAN - Переместить тяжелые файлы                  │
│    (doctor --deep-clean)                                     │
└──────────────────────────────────────────────────────────────┘

   Оптимизирует проект для AI: выносит тяжелые файлы и обновляет код.

   Процесс (6 шагов):
   1. Сканирование - находит файлы с токенами > порога (1000)
   2. Перемещение файлов в ../PROJECT_NAME_data/
   3. Генерация моста (config_paths.py)
   4. Патчинг кода - автоматически обновляет использование файлов
   5. Генерация карты навигации (AST_FOX_TRACE.md)
   6. Обновление правил Cursor

   Результат: Снижение токенов на 70-95%, проект остается функциональным.


┌──────────────────────────────────────────────────────────────┐
│ 4. 🗑️  ПЕРЕМЕСТИТЬ МУСОРНЫЕ ФАЙЛЫ В GARBAGE                  │
│    (doctor --garbage-clean)                                  │
└──────────────────────────────────────────────────────────────┘

   Находит и перемещает временные/старые файлы.

   Ищет:
   • *.tmp, *.temp, *.bak, *.old, *.backup
   • *.log.old, *.log.* (ротированные логи)
   • .DS_Store, Thumbs.db, desktop.ini
   • *_backup.*, *_old.*
   • tmp/, temp/, .tmp/ (директории)
   • Старые логи (старше 30 дней)

   Назначение: ../PROJECT_NAME_garbage_for_removal/


┌──────────────────────────────────────────────────────────────┐
│ 5. 📊 ОБНОВИТЬ ДОКУМЕНТАЦИЮ (status)                          │
└──────────────────────────────────────────────────────────────┘

   Генерирует/обновляет PROJECT_STATUS.md и CURRENT_CONTEXT_MAP.md.

   PROJECT_STATUS.md:
   • Структура проекта
   • Статистика файлов
   • Зависимости
   • Результаты тестов

   CURRENT_CONTEXT_MAP.md:
   • Карта контекста для AI
   • Ключевые файлы и их назначение
   • Архитектура проекта


┌──────────────────────────────────────────────────────────────┐
│ 6. 🔄 ВОССТАНОВИТЬ ФАЙЛЫ ИЗ DEEP CLEAN (--restore)          │
└──────────────────────────────────────────────────────────────┘

   Откатывает изменения Deep Clean, возвращая проект в исходное состояние.

   Процесс:
   1. Восстанавливает файлы из manifest.json
   2. Откатывает патчи кода из .bak файлов
   3. Удаляет сгенерированные файлы


┌──────────────────────────────────────────────────────────────┐
│ 7. 📝 ПОКАЗАТЬ СТАТУС ПРОЕКТА (status)                      │
└──────────────────────────────────────────────────────────────┘

   Показывает текущее состояние проекта:
   • Путь к проекту
   • Количество файлов
   • Размер проекта
   • Найденные проблемы (если есть)
   • Статус тестов


┌──────────────────────────────────────────────────────────────┐
│ 8. 🏗️  АРХИТЕКТУРНАЯ РЕСТРУКТУРИЗАЦИЯ (architect)            │
└──────────────────────────────────────────────────────────────┘

   Реструктурирует проект согласно принципам AI-Native.

   Процесс:
   1. Создание моста (config_paths.py)
   2. Перемещение тяжелых папок (venv/ → ../_venvs/)
   3. Перемещение данных (*.json, *.csv, *.db → ../_data/)
   4. Обновление стартовых скриптов
   5. Обновление .cursorignore


┌──────────────────────────────────────────────────────────────┐
│ 9. 🚀 ПОЛНОЕ ЛЕЧЕНИЕ (все возможности)                       │
└──────────────────────────────────────────────────────────────┘

   Выполняет полную оптимизацию проекта всеми доступными инструментами:

   Шаги:
   1. Диагностика проекта
   2. Авто-исправление проблем
   3. Перемещение мусорных файлов
   4. Deep Clean - перемещение тяжелых файлов
   5. Обновление документации

   Это самая полная оптимизация проекта для работы с AI.


════════════════════════════════════════════════════════════════
"""
        print(help_text)
        input("\nPress any key to return to menu..." if self.language == "EN" else "\nНажмите любую клавишу для возврата в меню...")
    
    def action_change_project(self):
        """Change project path."""
        self.clear_screen()
        
        if self.language == "EN":
            print("\n🔄 Change Project")
            print("=" * 60)
            if self.project_path:
                print(f"\n📂 Current project: {self.project_path}")
            else:
                print("\n📂 No project selected")
            print()
        else:
            print("\n🔄 Сменить проект")
            print("=" * 60)
            if self.project_path:
                print(f"\n📂 Текущий проект: {self.project_path}")
            else:
                print("\n📂 Проект не выбран")
            print()
        
        # Reset project path
        self.project_path = None
        
        # Request new path
        new_path = self.get_project_path()
        if new_path:
            if self.language == "EN":
                print(f"\n✅ Project changed to: {new_path}")
            else:
                print(f"\n✅ Проект изменён на: {new_path}")
            input("\nPress Enter to continue..." if self.language == "EN" else "\nНажмите Enter...")
        else:
            if self.language == "EN":
                print("\n⚠️  Project path not changed")
            else:
                print("\n⚠️  Путь к проекту не изменён")
            input("\nPress Enter to continue..." if self.language == "EN" else "\nНажмите Enter...")
    
    def action_switch_language(self):
        """Switch language."""
        self.language = "EN" if self.language == "RU" else "RU"
        msg = "✅ Language: English" if self.language == "EN" else "✅ Язык: Русский"
        print(f"\n{msg}")
        import time
        time.sleep(1)
    
    def run(self):
        """Main loop."""
        actions = {
            "1": self.action_diagnose,
            "2": self.action_auto_fix,
            "3": self.action_deep_clean,
            "4": self.action_garbage_clean,
            "5": self.action_update_docs,
            "6": self.action_restore,
            "7": self.action_status,
            "8": self.action_architect,
            "9": self.action_full_heal,
            "10": self.action_help,
            "11": self.action_change_project,
            "12": self.action_switch_language,
        }
        
        while True:
            try:
                choice = self.show_menu()
                
                if choice == "0":
                    self.clear_screen()
                    print("\n👋 Goodbye! / До свидания!\n")
                    break
                
                action = actions.get(choice)
                if action:
                    action()
                else:
                    print("\n❌ Invalid choice / Неверный выбор")
                    import time
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye! / До свидания!\n")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                input("\nPress Enter...")


def main():
    """Entry point."""
    menu = FoxMenu()
    menu.run()


if __name__ == "__main__":
    main()
