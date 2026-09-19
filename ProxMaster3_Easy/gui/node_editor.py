#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ProxMaster3 Easy - Node.js Editor Module
Профессиональный редактор скриптов Node.js/JavaScript для Proxmark3.
Включает подсветку синтаксиса, консоль вывода и интеграцию с ИИ.
"""

import sys
import os
import subprocess
import threading
import json
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QLabel, QSplitter, QFileDialog, QMessageBox, QComboBox, 
    QToolBar, QStatusBar, QApplication, QDialog, QLineEdit, 
    QGroupBox, QGridLayout, QSpinBox
)
from PyQt6.QtCore import Qt, QProcess, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import (
    QFont, QColor, QTextCharFormat, QSyntaxHighlighter, 
    QTextCursor, QIcon, QAction, QKeySequence
)

# Попытка импорта QScintilla для профессиональной подсветки
try:
    from QScintilla.Qsci import (
        QsciScintilla, QsciLexerJavaScript, QsciAPIs,
        QsciPrinter, QsciCommand
    )
    HAS_QSCINTILLA = True
except ImportError:
    HAS_QSCINTILLA = False
    print("QScintilla не найден. Используется упрощенный режим подсветки.")

class NodeConsole(QObject):
    """Класс для обработки вывода консоли Node.js"""
    output_received = pyqtSignal(str)
    error_received = pyqtSignal(str)
    process_finished = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.process = QProcess()
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.handle_finished)

    def run_script(self, script_content, working_dir):
        """Запускает скрипт через внешний node.exe или встроенную эмуляцию"""
        # Сохраняем скрипт во временный файл
        temp_file = os.path.join(working_dir, "temp_script.js")
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(script_content)
        
        # Путь к node.exe (можно настроить в настройках)
        node_path = "node"  # Предполагается, что node в PATH
        
        # Проверка наличия node
        if not self.check_node_installed():
            self.error_received.emit("Ошибка: Node.js не найден в системе PATH.\nУстановите Node.js с https://nodejs.org/")
            return

        args = [temp_file]
        self.process.start(node_path, args)

    def check_node_installed(self):
        try:
            proc = QProcess()
            proc.start("node", ["--version"])
            proc.waitForFinished(2000)
            return proc.exitCode() == 0
        except:
            return False

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        self.output_received.emit(data.data().decode("utf-8"))

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        self.error_received.emit(data.data().decode("utf-8"))

    def handle_finished(self, exit_code):
        self.process_finished.emit(exit_code)

    def stop(self):
        if self.process.state() == QProcess.ProcessState.Running:
            self.process.kill()


class JsHighlighter(QSyntaxHighlighter):
    """Упрощенная подсветка синтаксиса JS если QScintilla недоступен"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighting_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#569CD6")) # Синий
        keywords = [
            "var", "let", "const", "function", "return", "if", "else", 
            "for", "while", "do", "switch", "case", "break", "continue",
            "try", "catch", "finally", "throw", "new", "this", "class",
            "extends", "import", "export", "from", "async", "await"
        ]
        for word in keywords:
            self.highlighting_rules.append((f"\\b{word}\\b", keyword_format))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#CE9178")) # Оранжевый
        self.highlighting_rules.append(('"[^"\\\\]*(\\\\.[^"\\\\]*)*"', string_format))
        self.highlighting_rules.append(("'[^'\\\\]*(\\\\.[^'\\\\]*)*'", string_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#6A9955")) # Зеленый
        self.highlighting_rules.append(("//.*", comment_format))
        self.highlighting_rules.append(("/\\*.*?\\*/", comment_format))

        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#B5CEA8")) # Светло-зеленый
        self.highlighting_rules.append(("\\b[0-9]+\\.?[0-9]*\\b", number_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            import re
            for match in re.finditer(pattern, text):
                start, end = match.span()
                self.setFormat(start, end - start, fmt)


class ProxmasterNodeEditor(QWidget):
    """Основной виджет редактора Node.js"""
    
    def __init__(self, ai_assistant=None):
        super().__init__()
        self.ai_assistant = ai_assistant
        self.current_file = None
        self.console = NodeConsole()
        
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Тулбар
        toolbar = QToolBar()
        toolbar.setMovable(False)
        from PyQt6.QtCore import QSize; toolbar.setIconSize(QSize(16, 16))
        
        self.btn_new = QAction("📄 Новый", self)
        self.btn_open = QAction("📂 Открыть", self)
        self.btn_save = QAction("💾 Сохранить", self)
        self.btn_run = QAction("▶️ Запустить", self)
        self.btn_stop = QAction("⏹ Стоп", self)
        self.btn_ai_gen = QAction("🤖 AI Генерация", self)
        
        toolbar.addAction(self.btn_new)
        toolbar.addAction(self.btn_open)
        toolbar.addAction(self.btn_save)
        toolbar.addSeparator()
        toolbar.addAction(self.btn_run)
        toolbar.addAction(self.btn_stop)
        toolbar.addSeparator()
        toolbar.addAction(self.btn_ai_gen)
        
        layout.addWidget(toolbar)

        # Сплиттер для редактора и консоли
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Редактор кода
        if HAS_QSCINTILLA:
            self.editor = QsciScintilla()
            lexer = QsciLexerJavaScript(self.editor)
            lexer.setFont(QFont("Consolas", 10))
            self.editor.setLexer(lexer)
            self.editor.setBraceMatching(QsciScintilla.BraceMatch.Strict)
            self.editor.setIndentationGuides(True)
            self.editor.setAutoIndent(True)
            self.editor.setTabWidth(4)
            self.editor.setEdgeMode(QsciScintilla.EdgeLine)
            self.editor.setEdgeColumn(80)
        else:
            self.editor = QTextEdit()
            self.editor.setFont(QFont("Consolas", 10))
            self.highlighter = JsHighlighter(self.editor.document())
            
        splitter.addWidget(self.editor)

        # Консоль вывода
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        self.console_output.setFont(QFont("Consolas", 9))
        self.console_output.setStyleSheet("background-color: #1E1E1E; color: #DCDCDC;")
        splitter.addWidget(self.console_output)
        
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        self.setLayout(layout)

    def setup_connections(self):
        self.btn_new.triggered.connect(self.new_file)
        self.btn_open.triggered.connect(self.open_file)
        self.btn_save.triggered.connect(self.save_file)
        self.btn_run.triggered.connect(self.run_script)
        self.btn_stop.triggered.connect(self.stop_script)
        self.btn_ai_gen.triggered.connect(self.generate_with_ai)
        
        self.console.output_received.connect(self.append_console_output)
        self.console.error_received.connect(self.append_console_error)
        self.console.process_finished.connect(self.on_process_finished)

    def get_code(self):
        if HAS_QSCINTILLA:
            return self.editor.text()
        else:
            return self.editor.toPlainText()

    def set_code(self, code):
        if HAS_QSCINTILLA:
            self.editor.setText(code)
        else:
            self.editor.setPlainText(code)

    def new_file(self):
        self.current_file = None
        self.set_code("")
        self.append_console_output("--- Новый файл создан ---\n")

    def open_file(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Открыть скрипт", "scripts/", "JS Files (*.js);;All Files (*)"
        )
        if file_name:
            try:
                with open(file_name, "r", encoding="utf-8") as f:
                    code = f.read()
                self.set_code(code)
                self.current_file = file_name
                self.append_console_output(f"--- Открыт файл: {file_name} ---\n")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{e}")

    def save_file(self):
        if not self.current_file:
            file_name, _ = QFileDialog.getSaveFileName(
                self, "Сохранить скрипт", "scripts/", "JS Files (*.js)"
            )
            if file_name:
                self.current_file = file_name
        if self.current_file:
            try:
                code = self.get_code()
                with open(self.current_file, "w", encoding="utf-8") as f:
                    f.write(code)
                self.append_console_output(f"--- Сохранено: {self.current_file} ---\n")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")

    def run_script(self):
        code = self.get_code()
        if not code.strip():
            QMessageBox.warning(self, "Предупреждение", "Редактор пуст!")
            return
        
        self.append_console_output("\n=== ЗАПУСК СКРИПТА ===\n")
        self.console_output.clear()
        
        # Запуск в отдельном потоке/процессе
        work_dir = os.path.dirname(os.path.abspath(__file__)) 
        # Переход в корень проекта для относительных путей
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        self.console.run_script(code, root_dir)

    def stop_script(self):
        self.console.stop()
        self.append_console_error("\n!!! СКРИПТ ОСТАНОВЛЕН ПОЛЬЗОВАТЕЛЕМ !!!\n")

    def on_process_finished(self, exit_code):
        if exit_code == 0:
            self.append_console_output("\n=== СКРИПТ ЗАВЕРШЕН УСПЕШНО ===\n")
        else:
            self.append_console_error(f"\n=== СКРИПТ ЗАВЕРШЕН С ОШИБКОЙ (код {exit_code}) ===\n")

    def append_console_output(self, text):
        self.console_output.setTextColor(QColor("#4EC9B0")) # Cyan для инфо
        self.console_output.append(text)
        self.console_output.verticalScrollBar().setValue(
            self.console_output.verticalScrollBar().maximum()
        )

    def append_console_error(self, text):
        self.console_output.setTextColor(QColor("#F44747")) # Red для ошибок
        self.console_output.append(text)
        self.console_output.verticalScrollBar().setValue(
            self.console_output.verticalScrollBar().maximum()
        )

    def generate_with_ai(self):
        """Генерация кода с помощью AI"""
        if not self.ai_assistant:
            QMessageBox.warning(self, "AI недоступен", "AI помощник не инициализирован.\n\nНастройте AI в настройках приложения.")
            return

        # Получаем текущий код или создаем подсказку
        current_code = self.get_code()
        
        prompt = f"""
Напиши скрипт на Node.js для Proxmark3 Iceman firmware.
Задача: Автоматизировать работу с Mifare Classic картами.

Скрипт должен:
1. Проверять наличие карты в поле
2. Читать UID карты
3. Выполнять аутентификацию по ключам A/B
4. Читать данные из секторов
5. Выводить результаты в консоль

Используй async/await pattern.
Добавь обработку ошибок.

Текущий код (если есть):
{current_code if current_code.strip() else "// Код будет сгенерирован"}
"""
        
        self.append_console_output("🤖 Запрос к AI для генерации кода...")
        self.append_console_output(f"Подсказка: {prompt[:200]}...\n")
        
        try:
            # Вызов AI ассистента через API
            from core.ai_assistant import get_ai_assistant
            ai = get_ai_assistant()
            
            if ai and ai.is_available():
                self.append_console_output("⏳ Ожидание ответа от AI...")
                
                # Асинхронный запрос к AI
                def on_ai_response(response):
                    if response:
                        self.append_console_output("\n✅ AI ответил:")
                        self.set_code(response)
                        self.append_console_output(f"\n📝 Сгенерировано {len(response)} символов")
                    else:
                        self.append_console_error("\n❌ AI не вернул ответ")
                
                def on_ai_error(error):
                    self.append_console_error(f"\n❌ Ошибка AI: {error}")
                
                # Запуск в отдельном потоке
                import threading
                thread = threading.Thread(
                    target=lambda: ai.ask(prompt, callback=on_ai_response, error_callback=on_ai_error)
                )
                thread.daemon = True
                thread.start()
            else:
                self.append_console_error("❌ AI сервер недоступен")
                self.append_console_output("💡 Запустите LM Studio/Ollama и загрузите модель")
                
        except Exception as e:
            self.append_console_error(f"❌ Ошибка при вызове AI: {e}")
            self.append_console_output("💡 Убедитесь, что AI сервер запущен и настроен")
