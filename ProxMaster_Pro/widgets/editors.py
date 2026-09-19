# ProxMaster Pro - Виджеты редакторов
"""
Hex Editor и Node Editor для ProxMaster Pro
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QMenu, QApplication, QLabel, 
                             QSpinBox, QComboBox, QFileDialog, QMessageBox,
                             QSplitter, QFrame, QScrollArea, QGraphicsView, 
                             QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem,
                             QGraphicsLineItem, QGraphicsPathItem, QInputDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF, QSize
from PyQt6.QtGui import QColor, QFont, QPen, QBrush, QPainterPath, QKeySequence, QAction


class HexEditor(QWidget):
    """Hex редактор с поддержкой Undo/Redo"""
    
    data_changed = pyqtSignal(bytes)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = b''
        self.history = []
        self.history_index = -1
        self.max_history = 50
        self.selection_start = None
        self.selection_end = None
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Разделитель
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Таблица HEX
        self.hex_table = QTableWidget()
        self.hex_table.setColumnCount(16)
        self.hex_table.setHorizontalHeaderLabels([f'{i:02X}' for i in range(16)])
        self.hex_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.hex_table.horizontalHeader().setDefaultSectionSize(30)
        self.hex_table.verticalHeader().setVisible(True)
        self.hex_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.hex_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.hex_table.setFont(QFont('Consolas', 10))
        self.hex_table.itemChanged.connect(self.on_cell_changed)
        
        # ASCII представление
        self.ascii_table = QTableWidget()
        self.ascii_table.setColumnCount(1)
        self.ascii_table.setHorizontalHeaderLabels(['ASCII'])
        self.ascii_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.ascii_table.horizontalHeader().setDefaultSectionSize(60)
        self.ascii_table.verticalHeader().setVisible(True)
        self.ascii_table.setFont(QFont('Consolas', 10))
        self.ascii_table.setReadOnly(True)
        
        splitter.addWidget(self.hex_table)
        splitter.addWidget(self.ascii_table)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
        
        # Панель инструментов
        toolbar = QHBoxLayout()
        
        btn_load = QPushButton('📂 Загрузить')
        btn_load.clicked.connect(self.load_file)
        toolbar.addWidget(btn_load)
        
        btn_save = QPushButton('💾 Сохранить')
        btn_save.clicked.connect(self.save_file)
        toolbar.addWidget(btn_save)
        
        toolbar.addStretch()
        
        btn_undo = QPushButton('↩️ Undo')
        btn_undo.clicked.connect(self.undo)
        toolbar.addWidget(btn_undo)
        
        btn_redo = QPushButton('↪️ Redo')
        btn_redo.clicked.connect(self.redo)
        toolbar.addWidget(btn_redo)
        
        toolbar.addStretch()
        
        btn_copy = QPushButton('📋 Копировать')
        btn_copy.clicked.connect(self.copy_hex)
        toolbar.addWidget(btn_copy)
        
        btn_paste = QPushButton('📌 Вставить')
        btn_paste.clicked.connect(self.paste_hex)
        toolbar.addWidget(btn_paste)
        
        btn_clear = QPushButton('🗑️ Очистить')
        btn_clear.clicked.connect(self.clear_data)
        toolbar.addWidget(btn_clear)
        
        layout.addLayout(toolbar)
        
        # Статус бар
        self.status_label = QLabel('Готов')
        layout.addWidget(self.status_label)
        
        # Контекстное меню
        self.hex_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.hex_table.customContextMenuRequested.connect(self.show_context_menu)
        
    def set_data(self, data: bytes):
        """Установить данные"""
        self.save_to_history()
        self.data = data
        self.update_tables()
        self.status_label.setText(f'Загружено байт: {len(data)}')
        self.data_changed.emit(data)
        
    def get_data(self) -> bytes:
        """Получить данные"""
        return self.data
    
    def update_tables(self):
        """Обновить таблицы"""
        num_rows = (len(self.data) + 15) // 16
        
        self.hex_table.setRowCount(num_rows)
        self.ascii_table.setRowCount(num_rows)
        
        # Заполнение HEX
        for row in range(num_rows):
            for col in range(16):
                idx = row * 16 + col
                if idx < len(self.data):
                    item = QTableWidgetItem(f'{self.data[idx]:02X}')
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.hex_table.setItem(row, col, item)
                else:
                    item = QTableWidgetItem('')
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.hex_table.setItem(row, col, item)
            
            # ASCII
            ascii_str = ''
            for col in range(16):
                idx = row * 16 + col
                if idx < len(self.data):
                    byte = self.data[idx]
                    if 32 <= byte <= 126:
                        ascii_str += chr(byte)
                    else:
                        ascii_str += '.'
                else:
                    break
            
            self.ascii_table.setItem(row, 0, QTableWidgetItem(ascii_str))
    
    def on_cell_changed(self, item: QTableWidgetItem):
        """Обработка изменения ячейки"""
        try:
            row = item.row()
            col = item.column()
            idx = row * 16 + col
            
            text = item.text().strip()
            if len(text) >= 2:
                value = int(text[:2], 16)
                
                # Обновление данных
                if idx < len(self.data):
                    new_data = bytearray(self.data)
                    new_data[idx] = value
                    self.data = bytes(new_data)
                    self.update_tables()
                    self.data_changed.emit(self.data)
        except ValueError:
            pass
    
    def save_to_history(self):
        """Сохранить в историю"""
        # Удаление future history
        if self.history_index < len(self.history) - 1:
            self.history = self.history[:self.history_index + 1]
        
        self.history.append(self.data)
        if len(self.history) > self.max_history:
            self.history.pop(0)
        else:
            self.history_index += 1
    
    def undo(self):
        """Отменить действие"""
        if self.history_index > 0:
            self.history_index -= 1
            self.data = self.history[self.history_index]
            self.update_tables()
            self.status_label.setText('Undo')
    
    def redo(self):
        """Вернуть действие"""
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.data = self.history[self.history_index]
            self.update_tables()
            self.status_label.setText('Redo')
    
    def copy_hex(self):
        """Копировать выделенное в HEX"""
        selected = self.hex_table.selectedItems()
        if not selected:
            return
        
        hex_values = [item.text() for item in sorted(selected, key=lambda x: (x.row(), x.column()))]
        hex_string = ' '.join(hex_values)
        
        clipboard = QApplication.clipboard()
        clipboard.setText(hex_string)
        self.status_label.setText(f'Скопировано: {len(hex_values)} байт')
    
    def paste_hex(self):
        """Вставить из буфера обмена"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        
        try:
            # Парсинг HEX строки
            hex_values = text.replace(' ', '').replace('\n', '')
            new_data = bytes.fromhex(hex_values)
            
            self.save_to_history()
            
            # Вставка с текущей позиции или в начало
            selected = self.hex_table.selectedItems()
            start_idx = 0
            if selected:
                start_idx = min(item.row() * 16 + item.column() for item in selected)
            
            # Расширение данных если нужно
            if start_idx + len(new_data) > len(self.data):
                self.data = self.data.ljust(start_idx + len(new_data), b'\x00')
            
            new_data_array = bytearray(self.data)
            for i, byte in enumerate(new_data):
                if start_idx + i < len(new_data_array):
                    new_data_array[start_idx + i] = byte
            
            self.data = bytes(new_data_array)
            self.update_tables()
            self.status_label.setText(f'Вставлено: {len(new_data)} байт')
        except Exception as e:
            QMessageBox.warning(self, 'Ошибка', f'Неверный формат HEX: {e}')
    
    def clear_data(self):
        """Очистить данные"""
        reply = QMessageBox.question(self, 'Подтверждение', 
                                    'Очистить все данные?',
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.save_to_history()
            self.data = b''
            self.update_tables()
            self.status_label.setText('Очищено')
    
    def load_file(self):
        """Загрузить из файла"""
        filename, _ = QFileDialog.getOpenFileName(self, 'Загрузить файл', '', 
                                                  'Все файлы (*);;BIN файлы (*.bin);;HEX файлы (*.hex)')
        if filename:
            try:
                with open(filename, 'rb') as f:
                    data = f.read()
                self.set_data(data)
                self.status_label.setText(f'Загружено: {filename}')
            except Exception as e:
                QMessageBox.critical(self, 'Ошибка', f'Не удалось загрузить файл: {e}')
    
    def save_file(self):
        """Сохранить в файл"""
        filename, _ = QFileDialog.getSaveFileName(self, 'Сохранить файл', '', 
                                                  'BIN файлы (*.bin);;Все файлы (*)')
        if filename:
            try:
                with open(filename, 'wb') as f:
                    f.write(self.data)
                self.status_label.setText(f'Сохранено: {filename}')
            except Exception as e:
                QMessageBox.critical(self, 'Ошибка', f'Не удалось сохранить файл: {e}')
    
    def show_context_menu(self, pos):
        """Контекстное меню"""
        menu = QMenu(self)
        
        copy_action = menu.addAction('Копировать HEX')
        copy_action.triggered.connect(self.copy_hex)
        
        paste_action = menu.addAction('Вставить HEX')
        paste_action.triggered.connect(self.paste_hex)
        
        fill_action = menu.addAction('Заполнить нулями')
        fill_action.triggered.connect(self.fill_zeros)
        
        menu.exec(self.hex_table.viewport().mapToGlobal(pos))
    
    def fill_zeros(self):
        """Заполнить выделенное нулями"""
        selected = self.hex_table.selectedItems()
        if not selected:
            return
        
        self.save_to_history()
        
        for item in selected:
            row = item.row()
            col = item.column()
            idx = row * 16 + col
            
            if idx < len(self.data):
                new_data = bytearray(self.data)
                new_data[idx] = 0
                self.data = bytes(new_data)
        
        self.update_tables()


class NodeItem(QGraphicsRectItem):
    """Нода для графа"""
    
    def __init__(self, title: str, data: dict, parent=None):
        super().__init__(parent)
        self.title = title
        self.data = data
        self.setRect(0, 0, 200, 80)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        
        # Заголовок
        self.title_item = QGraphicsTextItem(title, self)
        self.title_item.setPos(10, 5)
        self.title_item.setDefaultTextColor(QColor('#FFFFFF'))
        
        # Описание
        desc = data.get('description', '')[:30] + '...' if len(data.get('description', '')) > 30 else data.get('description', '')
        self.desc_item = QGraphicsTextItem(desc, self)
        self.desc_item.setPos(10, 25)
        self.desc_item.setDefaultTextColor(QColor('#CCCCCC'))
        
        # Порты входа/выхода
        self.input_port = QGraphicsRectItem(-10, 35, 10, 10, self)
        self.input_port.setBrush(QBrush(QColor('#4CAF50')))
        
        self.output_port = QGraphicsRectItem(200, 35, 10, 10, self)
        self.output_port.setBrush(QBrush(QColor('#2196F3')))
        
        # Цвет ноды по уровню риска
        risk_color = {
            'safe': '#4CAF50',
            'medium': '#FF9800',
            'high': '#F44336',
            'dangerous': '#9C27B0'
        }
        color = risk_color.get(data.get('risk_level', 'safe'), '#4CAF50')
        self.setBrush(QBrush(QColor(color)))
    
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        # Можно добавить логику выделения


class ConnectionItem(QGraphicsPathItem):
    """Соединение между нодами"""
    
    def __init__(self, start_node: NodeItem, end_node: NodeItem, parent=None):
        super().__init__(parent)
        self.start_node = start_node
        self.end_node = end_node
        self.setPen(QPen(QColor('#2196F3'), 2))
        self.update_path()
    
    def update_path(self):
        """Обновить путь соединения"""
        start_pos = self.start_node.output_port.scenePos()
        end_pos = self.end_node.input_port.scenePos()
        
        path = QPainterPath()
        path.moveTo(start_pos)
        
        # Кривая Безье
        ctrl1 = QPointF(start_pos.x() + 50, start_pos.y())
        ctrl2 = QPointF(end_pos.x() - 50, end_pos.y())
        path.cubicTo(ctrl1, ctrl2, end_pos)
        
        self.setPath(path)


class NodeEditor(QGraphicsView):
    """Редактор нод для визуального программирования"""
    
    script_generated = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setScene(QGraphicsScene(self))
        self.nodes = []
        self.connections = []
        self.current_connection = None
        self.temp_line = None
        
        self.init_ui()
        
    def init_ui(self):
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setAcceptDrops(True)
        
        # Фон
        self.scene().setBackgroundBrush(QBrush(QColor('#1E1E1E')))
        
        # Сетка
        self.draw_grid()
        
        # Панель инструментов
        self.toolbar = QWidget()
        toolbar_layout = QHBoxLayout(self.toolbar)
        
        btn_add = QPushButton('➕ Добавить ноду')
        btn_add.clicked.connect(self.add_node_dialog)
        toolbar_layout.addWidget(btn_add)
        
        btn_delete = QPushButton('🗑️ Удалить')
        btn_delete.clicked.connect(self.delete_selected)
        toolbar_layout.addWidget(btn_delete)
        
        btn_clear = QPushButton('🧹 Очистить всё')
        btn_clear.clicked.connect(self.clear_all)
        toolbar_layout.addWidget(btn_clear)
        
        toolbar_layout.addStretch()
        
        btn_generate = QPushButton('⚡ Генерировать скрипт')
        btn_generate.clicked.connect(self.generate_script)
        toolbar_layout.addWidget(btn_generate)
        
        btn_run = QPushButton('▶️ Выполнить')
        btn_run.clicked.connect(self.run_script)
        toolbar_layout.addWidget(btn_run)
        
    def draw_grid(self):
        """Нарисовать сетку"""
        grid_size = 20
        grid_range = 2000
        
        for x in range(-grid_range, grid_range, grid_size):
            line = QGraphicsLineItem(x, -grid_range, x, grid_range)
            line.setPen(QPen(QColor('#333333'), 1))
            self.scene().addItem(line)
        
        for y in range(-grid_range, grid_range, grid_size):
            line = QGraphicsLineItem(-grid_range, y, grid_range, y)
            line.setPen(QPen(QColor('#333333'), 1))
            self.scene().addItem(line)
    
    def add_node(self, cmd_data: dict, pos: QPointF = None):
        """Добавить ноду"""
        if pos is None:
            pos = QPointF(100, 100)
        
        node = NodeItem(cmd_data.get('name', 'Command'), cmd_data)
        node.setPos(pos)
        self.scene().addItem(node)
        self.nodes.append(node)
        
        return node
    
    def add_node_dialog(self):
        """Диалог добавления ноды"""
        from core.engine import ProxMasterEngine
        
        # Получаем команды от движка (в реальном приложении)
        commands = []
        try:
            engine = ProxMasterEngine()
            all_commands = []
            for tab in ['main', 'search', 'write', 'emulation', 'sniffing']:
                all_commands.extend(engine.get_commands_for_tab(tab))
            commands = all_commands
        except:
            commands = []
        
        if not commands:
            QMessageBox.information(self, 'Инфо', 'Нет доступных команд')
            return
        
        # Простой выбор первой команды (в реальности нужен диалог выбора)
        cmd_names = [f"{cmd['name']} ({cmd['id']})" for cmd in commands]
        
        item, ok = QInputDialog.getItem(self, 'Выбор команды', 
                                        'Выберите команду:', 
                                        cmd_names, 0, False)
        if ok and item:
            cmd_id = item.split('(')[1].rstrip(')')
            cmd_data = next((c for c in commands if c['id'] == cmd_id), None)
            
            if cmd_data:
                pos = self.mapToScene(self.viewport().rect().center())
                self.add_node(cmd_data, pos)
    
    def delete_selected(self):
        """Удалить выделенные элементы"""
        selected_items = self.scene().selectedItems()
        
        for item in selected_items:
            if isinstance(item, NodeItem):
                # Удалить связанные соединения
                self.connections = [c for c in self.connections 
                                   if c.start_node != item and c.end_node != item]
                self.scene().removeItem(item)
                self.nodes.remove(item)
            elif isinstance(item, ConnectionItem):
                self.connections.remove(item)
                self.scene().removeItem(item)
    
    def clear_all(self):
        """Очистить всё"""
        reply = QMessageBox.question(self, 'Подтверждение', 
                                    'Удалить все ноды?',
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            for node in self.nodes[:]:
                self.scene().removeItem(node)
            self.nodes.clear()
            self.connections.clear()
    
    def generate_script(self) -> str:
        """Генерировать скрипт из графа"""
        if not self.nodes:
            return "# Нет нод\n"
        
        script_lines = [
            "# ProxMaster Pro Script",
            "# Сгенерировано Node Editor",
            "",
            "commands = ["
        ]
        
        # Сортировка нод по позиции (слева направо)
        sorted_nodes = sorted(self.nodes, key=lambda n: n.pos().x())
        
        for node in sorted_nodes:
            cmd_id = node.data.get('id', '')
            script_lines.append(f"    '{{cmd_id}}',  # {node.data.get('name', '')}")
        
        script_lines.append("]")
        script_lines.append("")
        script_lines.append("# Выполнение команд")
        script_lines.append("for cmd_id in commands:")
        script_lines.append("    execute_command(cmd_id)")
        
        script = '\n'.join(script_lines)
        
        self.script_generated.emit(script)
        return script
    
    def run_script(self):
        """Выполнить скрипт"""
        script = self.generate_script()
        # В реальном приложении здесь будет выполнение через движок
        QMessageBox.information(self, 'Инфо', f'Скрипт готов к выполнению:\n\n{script[:200]}...')


class SettingsPanel(QWidget):
    """Панель настроек с обновлениями"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Настройки подключения
        conn_group = QFrame()
        conn_layout = QVBoxLayout(conn_group)
        conn_layout.addWidget(QLabel('<b>Настройки подключения</b>'))
        
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel('COM порт:'))
        self.port_combo = QComboBox()
        port_layout.addWidget(self.port_combo)
        conn_layout.addLayout(port_layout)
        
        baud_layout = QHBoxLayout()
        baud_layout.addWidget(QLabel('Скорость:'))
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(['9600', '19200', '38400', '57600', '115200'])
        self.baud_combo.setCurrentText('115200')
        baud_layout.addWidget(self.baud_combo)
        conn_layout.addLayout(baud_layout)
        
        layout.addWidget(conn_group)
        
        # Разделитель
        layout.addWidget(QFrame())
        
        # Обновления
        update_group = QFrame()
        update_layout = QVBoxLayout(update_group)
        update_layout.addWidget(QLabel('<b>Обновления</b>'))
        
        # Приложение
        app_update_layout = QHBoxLayout()
        app_update_layout.addWidget(QLabel('ProxMaster Pro:'))
        self.app_version_label = QLabel('v1.0.0')
        app_update_layout.addWidget(self.app_version_label)
        app_update_layout.addStretch()
        self.check_app_btn = QPushButton('Проверить')
        self.check_app_btn.clicked.connect(self.check_app_update)
        app_update_layout.addWidget(self.check_app_btn)
        update_layout.addLayout(app_update_layout)
        
        # ProxSpace
        ps_update_layout = QHBoxLayout()
        ps_update_layout.addWidget(QLabel('ProxSpace:'))
        self.ps_version_label = QLabel('Не установлен')
        ps_update_layout.addWidget(self.ps_version_label)
        ps_update_layout.addStretch()
        self.check_ps_btn = QPushButton('Проверить')
        self.check_ps_btn.clicked.connect(self.check_proxspace_update)
        ps_update_layout.addWidget(self.check_ps_btn)
        update_layout.addLayout(ps_update_layout)
        
        # Прошивка
        fw_update_layout = QHBoxLayout()
        fw_update_layout.addWidget(QLabel('Прошивка Iceman:'))
        self.fw_version_label = QLabel('Неизвестно')
        fw_update_layout.addWidget(self.fw_version_label)
        fw_update_layout.addStretch()
        self.check_fw_btn = QPushButton('Проверить')
        self.check_fw_btn.clicked.connect(self.check_firmware_update)
        fw_update_layout.addWidget(self.check_fw_btn)
        update_layout.addLayout(fw_update_layout)
        
        layout.addWidget(update_group)
        
        # Roadmap
        roadmap_group = QFrame()
        roadmap_layout = QVBoxLayout(roadmap_group)
        roadmap_layout.addWidget(QLabel('<b>Roadmap и Changelog</b>'))
        
        self.roadmap_text = QTextEdit()
        self.roadmap_text.setReadOnly(True)
        self.roadmap_text.setMaximumHeight(200)
        self.roadmap_text.setText(self.get_roadmap())
        roadmap_layout.addWidget(self.roadmap_text)
        
        layout.addWidget(roadmap_group)
        
        layout.addStretch()
    
    def refresh_ports(self):
        """Обновить список портов"""
        from core.engine import CommunicationLayer
        comm = CommunicationLayer()
        ports = comm.list_ports()
        
        self.port_combo.clear()
        for port in ports:
            self.port_combo.addItem(f"{port['device']} - {port['description']}")
    
    def check_app_update(self):
        """Проверить обновление приложения"""
        QMessageBox.information(self, 'Обновление', 
                               'Проверка обновлений ProxMaster Pro...\n\n'
                               'GitHub: ProxMaster-Pro/releases\n\n'
                               'Функция будет реализована в следующей версии.')
    
    def check_proxspace_update(self):
        """Проверить обновление ProxSpace"""
        QMessageBox.information(self, 'Обновление',
                               'Проверка обновлений ProxSpace...\n\n'
                               'Репозиторий: Gator96100/ProxSpace\n\n'
                               'Автоматическая установка будет доступна скоро.')
    
    def check_firmware_update(self):
        """Проверить обновление прошивки"""
        QMessageBox.information(self, 'Обновление',
                               'Проверка обновлений прошивки...\n\n'
                               'Репозиторий: RfidResearchGroup/proxmark3\n\n'
                               'Обновление прошивки через GUI в разработке.')
    
    def get_roadmap(self) -> str:
        """Получить текст roadmap"""
        return """
<b>v1.0.0</b> (Текущая)
- Базовый GUI интерфейс
- 9 функциональных вкладок
- Hex редактор
- Node Editor
- База из 857 команд

<b>v1.1.0</b> (В планах)
- Автоматические обновления
- Интеграция с ProxSpace
- Обновление прошивки через GUI
- Экспорт/импорт дампов

<b>v1.2.0</b> (Будущее)
- Поддержка скриптов Python
- Расширенная визуализация сигналов
- Плагины сообщества
"""
