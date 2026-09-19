"""
AI Assistant Widget - Плавающая панель ИИ помощника
Интеграция с основным интерфейсом ProxMaster3 Easy
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit, 
    QPushButton, QComboBox, QLabel, QScrollArea, QFrame,
    QSizePolicy, QToolButton, QMenu, QAction, QApplication,
    QDialog, QDialogButtonBox, QFormLayout, QCheckBox, QSpinBox,
    QDoubleSpinBox, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QFont, QIcon, QColor, QTextCursor


class AIResponseWidget(QTextEdit):
    """Виджет для отображения ответов ИИ с поддержкой потокового вывода"""
    
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMinimumHeight(200)
        self.setFont(QFont("Consolas", 10))
        
        # Стили для разных типов сообщений
        self.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                padding: 5px;
            }
        """)
    
    def append_message(self, text: str, is_stream: bool = False):
        """Добавить сообщение с поддержкой потокового обновления"""
        if is_stream:
            # Потоковое обновление - заменяем последний блок
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(text)
        else:
            self.append(text)
        
        self.scrollToBottom()
    
    def clear_conversation(self):
        """Очистить разговор"""
        self.clear()
        self.append("=== Разговор очищен ===")


class AIInputWidget(QLineEdit):
    """Поле ввода для вопросов ИИ"""
    
    def __init__(self):
        super().__init__()
        self.setPlaceholderText("Введите вопрос для ИИ помощника...")
        self.setFont(QFont("Segoe UI", 11))
        self.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                padding: 8px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d4;
            }
        """)
    
    def keyPressEvent(self, event):
        """Обработка нажатия Enter для отправки"""
        if event.key() == Qt.Key.Key_Return and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            event.accept()
            self.parent().send_button.click()
        else:
            super().keyPressEvent(event)


class AIModelSelector(QComboBox):
    """Выпадающий список для выбора модели ИИ"""
    
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(200)
        self.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                padding: 5px;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3c3c3c;
            }
        """)
    
    def update_models(self, models: list):
        """Обновить список моделей"""
        current = self.currentText()
        self.clear()
        self.addItems(models)
        
        # Восстановить выбор если возможно
        if current in models:
            self.setCurrentText(current)
        elif models:
            self.setCurrentIndex(0)


class AIFloatingPanel(QWidget):
    """
    Плавающая панель ИИ помощника
    Работает поверх основного приложения
    """
    
    def __init__(self, ai_assistant, parent=None):
        super().__init__(parent)
        self.ai = ai_assistant
        self.is_dragging = False
        self.drag_position = QPoint()
        self.is_minimized = False
        self.settings_dialog = None
        
        self._setup_ui()
        self._connect_signals()
        self._load_settings()
    
    def _setup_ui(self):
        """Настроить интерфейс"""
        self.setWindowTitle("ИИ Помощник")
        self.setMinimumSize(450, 600)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        # Прозрачный фон без рамки
        self.setWindowFlags(
            Qt.WindowType.Window | 
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Заголовок с кнопками управления
        header_layout = QHBoxLayout()
        
        # Логотип и название
        logo_label = QLabel("🤖")
        logo_label.setFont(QFont("Segoe UI Emoji", 16))
        header_layout.addWidget(logo_label)
        
        title_label = QLabel("ИИ Помощник")
        title_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #ffffff;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Кнопка настроек
        settings_btn = QToolButton()
        settings_btn.setText("⚙️")
        settings_btn.setToolTip("Настройки ИИ")
        settings_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
                padding: 5px;
            }
            QToolButton:hover {
                background-color: #3c3c3c;
                border-radius: 5px;
            }
        """)
        settings_btn.clicked.connect(self.show_settings)
        header_layout.addWidget(settings_btn)
        
        # Кнопка сворачивания
        minimize_btn = QToolButton()
        minimize_btn.setText("➖")
        minimize_btn.setToolTip("Свернуть")
        minimize_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
                padding: 5px;
            }
            QToolButton:hover {
                background-color: #3c3c3c;
                border-radius: 5px;
            }
        """)
        minimize_btn.clicked.connect(self.toggle_minimize)
        header_layout.addWidget(minimize_btn)
        
        # Кнопка закрытия
        close_btn = QToolButton()
        close_btn.setText("❌")
        close_btn.setToolTip("Закрыть")
        close_btn.setStyleSheet("""
            QToolButton {
                background-color: transparent;
                border: none;
                font-size: 16px;
                padding: 5px;
            }
            QToolButton:hover {
                background-color: #e81123;
                border-radius: 5px;
            }
        """)
        close_btn.clicked.connect(self.hide)
        header_layout.addWidget(close_btn)
        
        # Фрейм заголовка для перетаскивания
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 10px 10px 0 0;
            }
        """)
        header_frame.setLayout(header_layout)
        header_frame.mousePressEvent = self._on_mouse_press
        header_frame.mouseMoveEvent = self._on_mouse_move
        main_layout.addWidget(header_frame)
        
        # Основное содержимое
        content_frame = QFrame()
        content_frame.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 0 0 10px 10px;
            }
        """)
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(10)
        
        # Выбор провайдера и модели
        provider_layout = QHBoxLayout()
        
        provider_label = QLabel("Провайдер:")
        provider_label.setStyleSheet("color: #d4d4d4;")
        provider_layout.addWidget(provider_label)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["LM Studio", "Cherry Studio", "Ollama"])
        self.provider_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        provider_layout.addWidget(self.provider_combo)
        
        provider_layout.addStretch()
        
        # Выбор модели
        self.model_selector = AIModelSelector()
        provider_layout.addWidget(self.model_selector)
        
        content_layout.addLayout(provider_layout)
        
        # Индикатор статуса
        status_layout = QHBoxLayout()
        self.status_indicator = QLabel("●")
        self.status_indicator.setStyleSheet("color: #666666; font-size: 14px;")
        self.status_label = QLabel("Не подключено")
        self.status_label.setStyleSheet("color: #666666; font-size: 10px;")
        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        content_layout.addLayout(status_layout)
        
        # Область ответов ИИ
        self.response_widget = AIResponseWidget()
        content_layout.addWidget(self.response_widget)
        
        # Режимы работы
        mode_layout = QHBoxLayout()
        mode_label = QLabel("Режим:")
        mode_label.setStyleSheet("color: #d4d4d4; font-size: 10px;")
        mode_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "general",
            "scripting", 
            "hex_editor",
            "developer",
            "updates"
        ])
        self.mode_combo.setCurrentText("general")
        self.mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3c3c3c;
                border-radius: 5px;
                padding: 3px;
                font-size: 10px;
            }
        """)
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        
        # Кнопка очистки истории
        clear_btn = QPushButton("🗑️ Очистить")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #3c3c3c;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 3px 10px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #4c4c4c;
            }
        """)
        clear_btn.clicked.connect(self.clear_conversation)
        mode_layout.addWidget(clear_btn)
        
        mode_layout.addStretch()
        content_layout.addLayout(mode_layout)
        
        # Поле ввода
        self.input_widget = AIInputWidget()
        content_layout.addWidget(self.input_widget)
        
        # Кнопка отправки
        self.send_button = QPushButton("Отправить ➤")
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 5px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1084d8;
            }
            QPushButton:pressed {
                background-color: #006cbd;
            }
            QPushButton:disabled {
                background-color: #3c3c3c;
                color: #666666;
            }
        """)
        self.send_button.clicked.connect(self.send_query)
        content_layout.addWidget(self.send_button)
        
        main_layout.addWidget(content_frame, 1)
    
    def _connect_signals(self):
        """Подключить сигналы"""
        pass
    
    def _on_mouse_press(self, event):
        """Начало перетаскивания"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def _on_mouse_move(self, event):
        """Перетаскивание"""
        if self.is_dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Конец перетаскивания"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_dragging = False
    
    def on_provider_changed(self, provider_name: str):
        """Изменение провайдера"""
        from core.ai_assistant import AIProvider
        
        provider_map = {
            "LM Studio": AIProvider.LM_STUDIO,
            "Cherry Studio": AIProvider.CHERRY_STUDIO,
            "Ollama": AIProvider.OLLAMA
        }
        
        provider = provider_map.get(provider_name, AIProvider.LM_STUDIO)
        
        # Обновить порт по умолчанию
        if provider_name == "Ollama":
            port = 11434
        else:
            port = 1234
        
        self.ai.set_provider(provider, port=port)
        self.refresh_models()
        self.update_status()
    
    def refresh_models(self):
        """Обновить список моделей"""
        models = self.ai.get_available_models()
        self.model_selector.update_models(models)
    
    def on_mode_changed(self, mode: str):
        """Изменение режима работы"""
        self.ai.set_system_prompt(mode)
        self.response_widget.append(f"=== Режим изменен: {mode} ===")
    
    def send_query(self):
        """Отправить запрос ИИ"""
        question = self.input_widget.text().strip()
        if not question:
            return
        
        mode = self.mode_combo.currentText()
        
        # Отключить ввод во время обработки
        self.input_widget.setEnabled(False)
        self.send_button.setEnabled(False)
        self.send_button.setText("Обработка...")
        
        # Добавить вопрос в историю
        self.response_widget.append(f"\n🧑 Вы: {question}\n")
        
        # Отправить запрос
        def response_callback(answer_chunk):
            # Потоковый ответ
            self.response_widget.append_message(answer_chunk, is_stream=True)
        
        def on_complete():
            # Включить ввод после завершения
            self.input_widget.setEnabled(True)
            self.send_button.setEnabled(True)
            self.send_button.setText("Отправить ➤")
            self.input_widget.clear()
            self.input_widget.setFocus()
            self.update_status()
        
        # Запустить в отдельном потоке
        thread = AIQueryThread(self.ai, question, mode)
        thread.response_chunk.connect(response_callback)
        thread.finished.connect(on_complete)
        thread.start()
    
    def clear_conversation(self):
        """Очистить разговор"""
        self.ai.clear_history()
        self.response_widget.clear_conversation()
    
    def update_status(self):
        """Обновить индикатор статуса"""
        is_connected = self.ai.test_connection()
        
        if is_connected:
            self.status_indicator.setStyleSheet("color: #107c10; font-size: 14px;")
            self.status_label.setText(f"Подключено: {self.ai.config.model}")
            self.status_label.setStyleSheet("color: #107c10; font-size: 10px;")
        else:
            self.status_indicator.setStyleSheet("color: #e81123; font-size: 14px;")
            self.status_label.setText("Не подключено")
            self.status_label.setStyleSheet("color: #e81123; font-size: 10px;")
    
    def show_settings(self):
        """Показать диалог настроек"""
        if not self.settings_dialog:
            self.settings_dialog = AISettingsDialog(self.ai, self)
        
        self.settings_dialog.exec()
        self.refresh_models()
        self.update_status()
    
    def toggle_minimize(self):
        """Свернуть/развернуть панель"""
        if self.is_minimized:
            self.response_widget.show()
            self.mode_combo.show()
            self.input_widget.show()
            self.send_button.show()
            self.setMinimumHeight(600)
            self.is_minimized = False
        else:
            self.response_widget.hide()
            self.mode_combo.hide()
            self.input_widget.hide()
            self.send_button.hide()
            self.setMinimumHeight(100)
            self.is_minimized = True
    
    def _load_settings(self):
        """Загрузить настройки"""
        try:
            config_path = "models/ai_config.json"
            self.ai.load_config(config_path)
            
            # Обновить UI
            provider_name = self.ai.config.provider.value.replace("_", " ").title()
            index = self.provider_combo.findText(provider_name)
            if index >= 0:
                self.provider_combo.setCurrentIndex(index)
            
            self.refresh_models()
            self.update_status()
            
        except Exception as e:
            print(f"[AI Widget] Ошибка загрузки настроек: {e}")
    
    def showEvent(self, event):
        """При показе окна обновить статус"""
        super().showEvent(event)
        QTimer.singleShot(500, self.update_status)


class AIQueryThread(QThread):
    """Поток для запросов к ИИ"""
    response_chunk = pyqtSignal(str)
    
    def __init__(self, ai_assistant, question: str, mode: str):
        super().__init__()
        self.ai = ai_assistant
        self.question = question
        self.mode = mode
    
    def run(self):
        """Выполнить запрос"""
        def on_chunk(chunk):
            self.response_chunk.emit(chunk)
        
        self.ai.add_callback(on_chunk)
        self.ai.ask(self.question, mode=self.mode, stream=True)
        self.ai.remove_callback(on_chunk)


class AISettingsDialog(QDialog):
    """Диалог настроек ИИ помощника"""
    
    def __init__(self, ai_assistant, parent=None):
        super().__init__(parent)
        self.ai = ai_assistant
        
        self.setWindowTitle("Настройки ИИ помощника")
        self.setMinimumWidth(400)
        
        self._setup_ui()
        self._load_current_settings()
    
    def _setup_ui(self):
        """Настроить интерфейс"""
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        # Хост
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("localhost")
        form_layout.addRow("Хост:", self.host_edit)
        
        # Порт
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(1234)
        form_layout.addRow("Порт:", self.port_spin)
        
        # Температура
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(0.7)
        form_layout.addRow("Температура:", self.temp_spin)
        
        # Макс токенов
        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(100, 8192)
        self.tokens_spin.setSingleStep(100)
        self.tokens_spin.setValue(2048)
        form_layout.addRow("Макс токенов:", self.tokens_spin)
        
        # Таймаут
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setSingleStep(5)
        self.timeout_spin.setValue(60)
        form_layout.addRow("Таймаут (сек):", self.timeout_spin)
        
        # Включен
        self.enabled_check = QCheckBox("Включить ИИ помощника")
        form_layout.addRow("", self.enabled_check)
        
        # Режим разработчика
        self.dev_check = QCheckBox("Режим разработчика (доступ к коду)")
        form_layout.addRow("", self.dev_check)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _load_current_settings(self):
        """Загрузить текущие настройки"""
        self.host_edit.setText(self.ai.config.host)
        self.port_spin.setValue(self.ai.config.port)
        self.temp_spin.setValue(self.ai.config.temperature)
        self.tokens_spin.setValue(self.ai.config.max_tokens)
        self.timeout_spin.setValue(self.ai.config.timeout)
        self.enabled_check.setChecked(self.ai.config.enabled)
        self.dev_check.setChecked(self.ai.config.dev_mode)
    
    def save_settings(self):
        """Сохранить настройки"""
        self.ai.config.host = self.host_edit.text() or "localhost"
        self.ai.config.port = self.port_spin.value()
        self.ai.config.temperature = self.temp_spin.value()
        self.ai.config.max_tokens = self.tokens_spin.value()
        self.ai.config.timeout = self.timeout_spin.value()
        self.ai.config.enabled = self.enabled_check.isChecked()
        self.ai.config.dev_mode = self.dev_check.isChecked()
        
        # Сохранить в файл
        try:
            self.ai.save_config("models/ai_config.json")
            QMessageBox.information(self, "Успех", "Настройки сохранены!")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить настройки: {e}")
        
        self.accept()
