"""
ProxMaster Pro - Settings & Update Widget
Виджет настроек приложения с управлением обновлениями.
"""

import sys
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                             QLabel, QPushButton, QScrollArea, QProgressBar,
                             QTextEdit, QCheckBox, QLineEdit, QFileDialog,
                             QMessageBox, QFrame, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor

# Импортируем updater из core
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.updater import Updater, UpdateInfo

class SettingsWidget(QWidget):
    """Виджет настроек и обновлений."""
    
    log_signal = pyqtSignal(str, str)
    progress_signal = pyqtSignal(int, int)
    status_signal = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.updater = Updater()
        
        # Регистрируем колбэки
        self.updater.register_callback('log', self._on_updater_log)
        self.updater.register_callback('progress', self._on_updater_progress)
        self.updater.register_callback('status', self._on_updater_status)
        
        # Подключаем сигналы к слотам отрисовки
        self.log_signal.connect(self._append_log)
        self.progress_signal.connect(self._update_progress)
        self.status_signal.connect(self._update_status)
        
        self._init_ui()
        
    def _init_ui(self):
        """Инициализация интерфейса."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Скролл для контента
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(20)
        
        # === Группа: Информация о приложении ===
        app_info_group = self._create_app_info_group()
        content_layout.addWidget(app_info_group)
        
        # === Группа: Обновления ===
        updates_group = self._create_updates_group()
        content_layout.addWidget(updates_group)
        
        # === Группа: Пути и конфигурация ===
        paths_group = self._create_paths_group()
        content_layout.addWidget(paths_group)
        
        # === Группа: Лог обновлений ===
        log_group = self._create_log_group()
        content_layout.addWidget(log_group)
        
        # Растягиватель
        content_layout.addStretch()
        
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)
        
    def _create_app_info_group(self) -> QGroupBox:
        """Создание группы информации о приложении."""
        group = QGroupBox("📦 Информация о приложении")
        layout = QVBoxLayout(group)
        
        info_layout = QHBoxLayout()
        
        # Логотип или иконка (текстовая заглушка)
        logo_label = QLabel("🚀")
        logo_label.setFont(QFont("Segoe UI", 40))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(logo_label)
        
        # Текстовая информация
        text_layout = QVBoxLayout()
        self.app_name_label = QLabel("ProxMaster Pro")
        self.app_name_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        text_layout.addWidget(self.app_name_label)
        
        self.version_label = QLabel(f"Версия: {self.updater.config.get('app_version', '1.0.0')}")
        self.version_label.setFont(QFont("Segoe UI", 12))
        text_layout.addWidget(self.version_label)
        
        self.build_label = QLabel("Сборка: Stable")
        self.build_label.setFont(QFont("Segoe UI", 10))
        text_layout.addWidget(self.build_label)
        
        info_layout.addLayout(text_layout)
        info_layout.addStretch()
        
        layout.addLayout(info_layout)
        
        # Кнопка проверки обновлений приложения
        check_btn = QPushButton("🔄 Проверить обновление приложения")
        check_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db; color: white; border-radius: 5px;
                padding: 8px 15px; font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        check_btn.clicked.connect(self._check_app_update)
        layout.addWidget(check_btn)
        
        return group

    def _create_updates_group(self) -> QGroupBox:
        """Создание группы управления обновлениями компонентов."""
        group = QGroupBox("⚙️ Управление компонентами")
        layout = QVBoxLayout(group)
        
        # ProxSpace
        ps_layout = QHBoxLayout()
        ps_label = QLabel("📂 <b>ProxSpace (Gator96100)</b><br><small>Среда разработки и инструменты</small>")
        ps_label.setTextFormat(Qt.TextFormat.RichText)
        ps_layout.addWidget(ps_label, 1)
        
        self.ps_status_label = QLabel("Статус: Не проверено")
        self.ps_status_label.setStyleSheet("color: gray;")
        ps_layout.addWidget(self.ps_status_label)
        
        self.ps_progress = QProgressBar()
        self.ps_progress.setFixedWidth(150)
        self.ps_progress.setVisible(False)
        ps_layout.addWidget(self.ps_progress)
        
        self.ps_update_btn = QPushButton("Обновить")
        self.ps_update_btn.setFixedWidth(100)
        self.ps_update_btn.clicked.connect(self._update_proxspace)
        ps_layout.addWidget(self.ps_update_btn)
        
        layout.addLayout(ps_layout)
        layout.addWidget(QFrame()) # Разделитель
        
        # Iceman Firmware
        ic_layout = QHBoxLayout()
        ic_label = QLabel("📡 <b>Прошивка Iceman (RRG)</b><br><small>Актуальная прошивка и клиент</small>")
        ic_label.setTextFormat(Qt.TextFormat.RichText)
        ic_layout.addWidget(ic_label, 1)
        
        self.ic_status_label = QLabel("Статус: Не проверено")
        self.ic_status_label.setStyleSheet("color: gray;")
        ic_layout.addWidget(self.ic_status_label)
        
        self.ic_progress = QProgressBar()
        self.ic_progress.setFixedWidth(150)
        self.ic_progress.setVisible(False)
        ic_layout.addWidget(self.ic_progress)
        
        self.ic_update_btn = QPushButton("Обновить")
        self.ic_update_btn.setFixedWidth(100)
        self.ic_update_btn.clicked.connect(self._update_iceman)
        ic_layout.addWidget(self.ic_update_btn)
        
        layout.addLayout(ic_layout)
        
        return group

    def _create_paths_group(self) -> QGroupBox:
        """Создание группы настройки путей."""
        group = QGroupBox("📁 Настройка путей")
        layout = QVBoxLayout(group)
        
        # Путь к ProxSpace
        ps_path_layout = QHBoxLayout()
        ps_path_layout.addWidget(QLabel("Путь к ProxSpace:"))
        self.ps_path_edit = QLineEdit(self.updater.config.get('proxspace_path', ''))
        self.ps_path_edit.setPlaceholderText("C:\\ProxSpace\\pm3")
        ps_path_layout.addWidget(self.ps_path_edit)
        ps_browse_btn = QPushButton("...")
        ps_browse_btn.setFixedWidth(40)
        ps_browse_btn.clicked.connect(lambda: self._browse_folder(self.ps_path_edit))
        ps_path_layout.addWidget(ps_browse_btn)
        layout.addLayout(ps_path_layout)
        
        # Путь к Iceman
        ic_path_layout = QHBoxLayout()
        ic_path_layout.addWidget(QLabel("Путь к Iceman:"))
        self.ic_path_edit = QLineEdit(self.updater.config.get('iceman_path', ''))
        self.ic_path_edit.setPlaceholderText("C:\\proxmark3\\iceman")
        ic_path_layout.addWidget(self.ic_path_edit)
        ic_browse_btn = QPushButton("...")
        ic_browse_btn.setFixedWidth(40)
        ic_browse_btn.clicked.connect(lambda: self._browse_folder(self.ic_path_edit))
        ic_path_layout.addWidget(ic_browse_btn)
        layout.addLayout(ic_path_layout)
        
        # Чекбокс автообновления
        self.auto_update_cb = QCheckBox("Автоматически проверять обновления при запуске")
        self.auto_update_cb.setChecked(self.updater.config.get('auto_update', False))
        layout.addWidget(self.auto_update_cb)
        
        # Кнопка сохранения
        save_btn = QPushButton("💾 Сохранить настройки")
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)
        
        return group

    def _create_log_group(self) -> QGroupBox:
        """Создание группы логов обновлений."""
        group = QGroupBox("📝 Журнал обновлений")
        layout = QVBoxLayout(group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e; color: #d4d4d4;
                border: 1px solid #333; border-radius: 4px;
            }
        """)
        layout.addWidget(self.log_text)
        
        clear_btn = QPushButton("Очистить лог")
        clear_btn.clicked.connect(self.log_text.clear)
        layout.addWidget(clear_btn)
        
        return group

    # --- Логика работы ---

    def _browse_folder(self, line_edit: QLineEdit):
        """Открытие диалога выбора папки."""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку", line_edit.text())
        if folder:
            line_edit.setText(folder.replace('/', '\\'))

    def _save_settings(self):
        """Сохранение настроек в config.json."""
        self.updater.config['proxspace_path'] = self.ps_path_edit.text()
        self.updater.config['iceman_path'] = self.ic_path_edit.text()
        self.updater.config['auto_update'] = self.auto_update_cb.isChecked()
        
        try:
            with open(self.updater.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.updater.config, f, indent=4, ensure_ascii=False)
            QMessageBox.information(self, "Успех", "Настройки сохранены!")
            self._append_log("Настройки сохранены в config.json", "success")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки: {str(e)}")
            self._append_log(f"Ошибка сохранения: {str(e)}", "error")

    def _check_app_update(self):
        """Проверка обновления приложения."""
        self._append_log("Запуск проверки обновления приложения...", "info")
        info = self.updater.check_app_update()
        
        if info and info.is_available:
            msg = f"Доступна новая версия: {info.latest_version}!\n\n{info.changelog[:200]}..."
            reply = QMessageBox.question(self, "Обновление доступно", msg, 
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.updater.start_app_update(info, self._on_app_update_complete)
        else:
            self._append_log("Установлена актуальная версия приложения.", "success")
            QMessageBox.information(self, "Обновления", "У вас последняя версия приложения.")

    def _update_proxspace(self):
        """Запуск обновления ProxSpace."""
        self.ps_update_btn.setEnabled(False)
        self.ps_progress.setVisible(True)
        self._append_log("Запуск обновления ProxSpace...", "info")
        
        info = self.updater.check_proxspace_update()
        if info:
            self.updater.start_proxspace_update(info, self._on_ps_update_complete)
        else:
            self._append_log("Не удалось получить информацию о версии ProxSpace.", "error")
            self.ps_update_btn.setEnabled(True)

    def _update_iceman(self):
        """Запуск обновления Iceman."""
        self.ic_update_btn.setEnabled(False)
        self.ic_progress.setVisible(True)
        self._append_log("Запуск обновления прошивки Iceman...", "info")
        
        info = self.updater.check_iceman_update()
        if info:
            self.updater.start_iceman_update(info, self._on_ic_update_complete)
        else:
            self._append_log("Не удалось получить информацию о версии Iceman.", "error")
            self.ic_update_btn.setEnabled(True)

    # --- Колбэки и обработчики сигналов ---

    def _on_updater_log(self, message: str, level: str):
        self.log_signal.emit(message, level)

    def _on_updater_progress(self, value: int, max_val: int):
        self.progress_signal.emit(value, max_val)

    def _on_updater_status(self, status: str):
        self.status_signal.emit(status)

    def _append_log(self, message: str, level: str):
        """Добавление сообщения в лог с цветом."""
        colors = {
            "info": "#4fc3f7",
            "success": "#81c784",
            "warning": "#ffb74d",
            "error": "#e57373"
        }
        color = colors.get(level, "#d4d4d4")
        timestamp = datetime.now().strftime("%H:%M:%S")
        html = f'<span style="color:gray;">[{timestamp}]</span> <span style="color:{color};">{message}</span><br>'
        self.log_text.append(html)

    def _update_progress(self, value: int, max_val: int):
        """Обновление прогресс баров (упрощенно для всех)."""
        # В реальной реализации нужно передавать ID компонента
        if self.ps_progress.isVisible():
            self.ps_progress.setMaximum(max_val)
            self.ps_progress.setValue(value)
        if self.ic_progress.isVisible():
            self.ic_progress.setMaximum(max_val)
            self.ic_progress.setValue(value)

    def _update_status(self, status: str):
        """Обновление статус лейблов."""
        self.ps_status_label.setText(f"Статус: {status}")
        self.ic_status_label.setText(f"Статус: {status}")

    def _on_app_update_complete(self, success: bool):
        self.ps_update_btn.setEnabled(True)
        if success:
            self._append_log("Обновление приложения завершено успешно. Перезапустите программу.", "success")
            QMessageBox.information(self, "Готово", "Приложение обновлено! Требуется перезапуск.")
        else:
            self._append_log("Ошибка обновления приложения.", "error")

    def _on_ps_update_complete(self, success: bool):
        self.ps_update_btn.setEnabled(True)
        self.ps_progress.setVisible(False)
        if success:
            self._append_log("ProxSpace успешно обновлен.", "success")
            self.ps_status_label.setText("Статус: Актуально")
            self.ps_status_label.setStyleSheet("color: green;")
        else:
            self._append_log("Ошибка обновления ProxSpace.", "error")

    def _on_ic_update_complete(self, success: bool):
        self.ic_update_btn.setEnabled(True)
        self.ic_progress.setVisible(False)
        if success:
            self._append_log("Iceman успешно обновлен (требуется компиляция).", "success")
            self.ic_status_label.setText("Статус: Актуально")
            self.ic_status_label.setStyleSheet("color: green;")
        else:
            self._append_log("Ошибка обновления Iceman.", "error")

# Импорт для работы дат в логах
from datetime import datetime
import json
