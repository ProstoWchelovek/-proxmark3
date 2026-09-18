"""
ProxMaster Ultimate - GUI Widgets
Виджеты интерфейса: Hex редактор, Node Editor, Log Viewer и другие
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, colorchooser
import json
import re
from typing import Optional, Dict, List, Callable, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
import threading


# ============================================================================
# HEX EDITOR Widget
# ============================================================================

class HexEditor(tk.Frame):
    """Полнофункциональный HEX редактор для просмотра и редактирования бинарных данных"""
    
    def __init__(self, parent, width=800, height=400, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.width = width
        self.height = height
        self.data = bytearray()
        self.cursor_pos = 0
        self.selection_start = None
        self.selection_end = None
        self.bytes_per_line = 16
        self.font_hex = ("Consolas", 10)
        self.font_ascii = ("Consolas", 10)
        self.line_height = 16
        self.colors = {
            'bg': '#1e1e1e',
            'fg': '#d4d4d4',
            'address': '#858585',
            'hex_even': '#d4d4d4',
            'hex_odd': '#cecece',
            'ascii': '#b5cea8',
            'selection': '#264f78',
            'cursor': '#569cd6',
            'modified': '#f44336',
            'separator': '#3c3c3c'
        }
        
        self.modified_positions = set()
        self.clipboard_data = None
        self.undo_stack = []
        self.redo_stack = []
        
        self._setup_ui()
        self._bind_events()
    
    def _setup_ui(self):
        """Настройка UI компонентов"""
        # Canvas для отображения
        self.canvas = tk.Canvas(
            self,
            bg=self.colors['bg'],
            highlightthickness=0,
            width=self.width,
            height=self.height
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbars
        self.v_scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._on_vscroll)
        self.v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.h_scrollbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self._on_hscroll)
        self.h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set,
                             xscrollcommand=self.h_scrollbar.set)
        
        # Контекстное меню
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Копировать (Ctrl+C)", command=self.copy)
        self.context_menu.add_command(label="Вставить (Ctrl+V)", command=self.paste)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Вырезать (Ctrl+X)", command=self.cut)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Выделить всё (Ctrl+A)", command=self.select_all)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Заполнить нулями", command=self.fill_zeros)
        self.context_menu.add_command(label="Заполнить FF", command=self.fill_ff)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Отменить (Ctrl+Z)", command=self.undo)
        self.context_menu.add_command(label="Вернуть (Ctrl+Y)", command=self.redo)
        
        # Статус бар
        self.status_var = tk.StringVar()
        self.status_bar = tk.Label(
            self,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            height=1,
            font=("Segoe UI", 9)
        )
        self.status_var.set("Готов")
    
    def _bind_events(self):
        """Привязка событий"""
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<Key>", self._on_key)
        self.canvas.bind("<FocusIn>", self._on_focus_in)
        self.canvas.bind("<FocusOut>", self._on_focus_out)
        
        # Горячие клавиши
        self.bind_all("<Control-c>", lambda e: self.copy())
        self.bind_all("<Control-v>", lambda e: self.paste())
        self.bind_all("<Control-x>", lambda e: self.cut())
        self.bind_all("<Control-a>", lambda e: self.select_all())
        self.bind_all("<Control-z>", lambda e: self.undo())
        self.bind_all("<Control-y>", lambda e: self.redo())
    
    def load_data(self, data: bytes):
        """Загрузка данных в редактор"""
        self.data = bytearray(data)
        self.modified_positions.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.cursor_pos = 0
        self._redraw()
        self._update_status()
    
    def get_data(self) -> bytes:
        """Получение текущих данных"""
        return bytes(self.data)
    
    def _get_visible_lines(self) -> Tuple[int, int]:
        """Получение видимых строк"""
        y_view = self.canvas.yview()
        total_lines = (len(self.data) + self.bytes_per_line - 1) // self.bytes_per_line
        start_line = int(y_view[0] * total_lines)
        end_line = min(int(y_view[1] * total_lines) + 2, total_lines)
        return start_line, end_line
    
    def _pos_to_coords(self, pos: int) -> Tuple[int, int]:
        """Преобразование позиции в координаты"""
        line = pos // self.bytes_per_line
        col = pos % self.bytes_per_line
        x = 100 + (col * 30) if col < 8 else 100 + (8 * 30) + 20 + ((col - 8) * 30)
        y = line * self.line_height + 5
        return x, y
    
    def _coords_to_pos(self, x: int, y: int) -> int:
        """Преобразование координат в позицию"""
        line = int(y / self.line_height)
        if x < 100:
            col = 0
        elif x < 100 + (8 * 30):
            col = int((x - 100) / 30)
        else:
            col = 8 + int((x - 100 - (8 * 30) - 20) / 30)
        
        pos = line * self.bytes_per_line + col
        return max(0, min(pos, len(self.data) - 1))
    
    def _redraw(self):
        """Перерисовка содержимого"""
        self.canvas.delete("all")
        
        if not self.data:
            return
        
        start_line, end_line = self._get_visible_lines()
        y_offset = -self.canvas.yview()[0] * len(self.data) * self.line_height / self.bytes_per_line
        
        for line in range(start_line, end_line):
            offset = line * self.bytes_per_line
            if offset >= len(self.data):
                break
            
            y = line * self.line_height + 5
            
            # Адрес строки
            addr_str = f"{offset:08X}"
            self.canvas.create_text(
                10, y,
                text=addr_str,
                anchor=tk.NW,
                fill=self.colors['address'],
                font=self.font_hex
            )
            
            # HEX данные
            for i in range(self.bytes_per_line):
                pos = offset + i
                if pos >= len(self.data):
                    break
                
                byte_val = self.data[pos]
                hex_str = f"{byte_val:02X}"
                
                # Цвет в зависимости от состояния
                if pos in self.modified_positions:
                    fill = self.colors['modified']
                elif self.selection_start and self.selection_end:
                    if min(self.selection_start, self.selection_end) <= pos <= max(self.selection_start, self.selection_end):
                        fill = self.colors['selection']
                    else:
                        fill = self.colors['hex_even'] if i % 2 == 0 else self.colors['hex_odd']
                else:
                    fill = self.colors['hex_even'] if i % 2 == 0 else self.colors['hex_odd']
                
                # Курсор
                if pos == self.cursor_pos:
                    fill = self.colors['cursor']
                
                x = 100 + (i * 30) if i < 8 else 100 + (8 * 30) + 20 + ((i - 8) * 30)
                self.canvas.create_text(
                    x, y,
                    text=hex_str,
                    anchor=tk.NW,
                    fill=fill,
                    font=self.font_hex
                )
                
                # Разделитель между группами
                if i == 7:
                    self.canvas.create_line(
                        x + 25, y, x + 25, y + self.line_height,
                        fill=self.colors['separator']
                    )
            
            # ASCII представление
            ascii_x = 100 + (16 * 30) + 40
            ascii_str = ""
            for i in range(self.bytes_per_line):
                pos = offset + i
                if pos >= len(self.data):
                    break
                byte_val = self.data[pos]
                if 32 <= byte_val <= 126:
                    ascii_str += chr(byte_val)
                else:
                    ascii_str += "."
            
            self.canvas.create_text(
                ascii_x, y,
                text=ascii_str,
                anchor=tk.NW,
                fill=self.colors['ascii'],
                font=self.font_ascii
            )
        
        self._update_status()
    
    def _update_status(self):
        """Обновление статусной строки"""
        if self.data:
            byte_val = self.data[self.cursor_pos] if self.cursor_pos < len(self.data) else 0
            status = f"Позиция: {self.cursor_pos} (0x{self.cursor_pos:04X}) | " \
                    f"Значение: 0x{byte_val:02X} ({byte_val}) | " \
                    f"Размер: {len(self.data)} байт"
            
            if self.modified_positions:
                status += f" | Изменено: {len(self.modified_positions)} байт"
            
            self.status_var.set(status)
        else:
            self.status_var.set("Нет данных")
    
    def _on_click(self, event):
        """Обработка клика мыши"""
        self.canvas.focus_set()
        pos = self._coords_to_pos(event.x, event.y + self.canvas.yview()[0] * self.canvas.winfo_height())
        self.cursor_pos = max(0, min(pos, len(self.data) - 1))
        self.selection_start = self.cursor_pos
        self.selection_end = self.cursor_pos
        self._redraw()
    
    def _on_drag(self, event):
        """Обработка перетаскивания"""
        pos = self._coords_to_pos(event.x, event.y + self.canvas.yview()[0] * self.canvas.winfo_height())
        self.selection_end = max(0, min(pos, len(self.data) - 1))
        self._redraw()
    
    def _on_right_click(self, event):
        """Обработка правого клика"""
        try:
            self.context_menu.post(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
    
    def _on_key(self, event):
        """Обработка нажатий клавиш"""
        if not self.data:
            return
        
        # Навигация
        if event.keysym == "Left":
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif event.keysym == "Right":
            self.cursor_pos = min(len(self.data) - 1, self.cursor_pos + 1)
        elif event.keysym == "Up":
            self.cursor_pos = max(0, self.cursor_pos - self.bytes_per_line)
        elif event.keysym == "Down":
            self.cursor_pos = min(len(self.data) - 1, self.cursor_pos + self.bytes_per_line)
        elif event.keysym == "Home":
            line_start = (self.cursor_pos // self.bytes_per_line) * self.bytes_per_line
            self.cursor_pos = line_start
        elif event.keysym == "End":
            line_end = min((self.cursor_pos // self.bytes_per_line + 1) * self.bytes_per_line - 1, len(self.data) - 1)
            self.cursor_pos = line_end
        elif event.keysym == "Prior":  # Page Up
            self.cursor_pos = max(0, self.cursor_pos - self.bytes_per_line * 10)
        elif event.keysym == "Next":  # Page Down
            self.cursor_pos = min(len(self.data) - 1, self.cursor_pos + self.bytes_per_line * 10)
        
        # Ввод данных (hex)
        elif event.char in "0123456789abcdefABCDEF":
            self._save_state()
            new_val = int(event.char, 16) << 4
            if self.cursor_pos < len(self.data):
                # Сохраняем младшие 4 бита
                old_val = self.data[self.cursor_pos]
                self.data[self.cursor_pos] = new_val | (old_val & 0x0F)
                self.modified_positions.add(self.cursor_pos)
                self.cursor_pos = min(len(self.data) - 1, self.cursor_pos + 1)
        
        self._redraw()
    
    def _on_mousewheel(self, event):
        """Обработка колесика мыши"""
        if event.num == 5 or event.delta == -120:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta == 120:
            self.canvas.yview_scroll(-1, "units")
        self._redraw()
    
    def _on_vscroll(self, *args):
        """Вертикальная прокрутка"""
        self.canvas.yview(*args)
        self._redraw()
    
    def _on_hscroll(self, *args):
        """Горизонтальная прокрутка"""
        self.canvas.xview(*args)
        self._redraw()
    
    def _save_state(self):
        """Сохранение состояния для отмены"""
        self.undo_stack.append((self.cursor_pos, self.data[self.cursor_pos]))
        if len(self.undo_stack) > 100:
            self.undo_stack.pop(0)
        self.redo_stack.clear()
    
    def undo(self):
        """Отмена последнего действия"""
        if self.undo_stack:
            pos, val = self.undo_stack.pop()
            self.redo_stack.append((pos, self.data[pos]))
            self.data[pos] = val
            self.modified_positions.discard(pos)
            self._redraw()
    
    def redo(self):
        """Повтор отмененного действия"""
        if self.redo_stack:
            pos, val = self.redo_stack.pop()
            self.undo_stack.append((pos, self.data[pos]))
            self.data[pos] = val
            self.modified_positions.add(pos)
            self._redraw()
    
    def copy(self):
        """Копирование выделенного"""
        if self.selection_start is not None and self.selection_end is not None:
            start = min(self.selection_start, self.selection_end)
            end = max(self.selection_start, self.selection_end)
            self.clipboard_data = bytes(self.data[start:end+1])
            self.clipboard_data_hex = self.clipboard_data.hex().upper()
    
    def cut(self):
        """Вырезание выделенного"""
        self.copy()
        self._save_state()
        if self.selection_start is not None and self.selection_end is not None:
            start = min(self.selection_start, self.selection_end)
            end = max(self.selection_start, self.selection_end)
            del self.data[start:end+1]
            self.modified_positions.clear()
            self.cursor_pos = start
            self.selection_start = None
            self.selection_end = None
            self._redraw()
    
    def paste(self):
        """Вставка из буфера"""
        if self.clipboard_data:
            self._save_state()
            if self.selection_start is not None and self.selection_end is not None:
                start = min(self.selection_start, self.selection_end)
                end = max(self.selection_start, self.selection_end)
                self.data[start:start+len(self.clipboard_data)] = self.clipboard_data
            else:
                self.data[self.cursor_pos:self.cursor_pos+len(self.clipboard_data)] = self.clipboard_data
            
            for i in range(len(self.clipboard_data)):
                self.modified_positions.add(self.cursor_pos + i)
            self._redraw()
    
    def select_all(self):
        """Выделение всего"""
        self.selection_start = 0
        self.selection_end = len(self.data) - 1
        self._redraw()
    
    def fill_zeros(self):
        """Заполнение выделенного нулями"""
        if self.selection_start is not None and self.selection_end is not None:
            self._save_state()
            start = min(self.selection_start, self.selection_end)
            end = max(self.selection_start, self.selection_end)
            for i in range(start, end + 1):
                self.data[i] = 0
                self.modified_positions.add(i)
            self._redraw()
    
    def fill_ff(self):
        """Заполнение выделенного FF"""
        if self.selection_start is not None and self.selection_end is not None:
            self._save_state()
            start = min(self.selection_start, self.selection_end)
            end = max(self.selection_start, self.selection_end)
            for i in range(start, end + 1):
                self.data[i] = 0xFF
                self.modified_positions.add(i)
            self._redraw()
    
    def export_to_file(self, filename: str = None):
        """Экспорт данных в файл"""
        if not filename:
            filename = filedialog.asksaveasfilename(
                defaultextension=".bin",
                filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
            )
        
        if filename:
            with open(filename, 'wb') as f:
                f.write(bytes(self.data))
            return True
        return False
    
    def import_from_file(self, filename: str = None):
        """Импорт данных из файла"""
        if not filename:
            filename = filedialog.askopenfilename(
                filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
            )
        
        if filename:
            with open(filename, 'rb') as f:
                data = f.read()
            self.load_data(data)
            return True
        return False


# ============================================================================
# NODE EDITOR Widget (визуальный редактор команд)
# ============================================================================

@dataclass
class NodePort:
    """Порт узла"""
    name: str
    port_type: str  # "input" или "output"
    data_type: str  # "string", "int", "bool", "any"
    value: Any = None


@dataclass 
class Node:
    """Узел графа команд"""
    id: str
    title: str
    x: float
    y: float
    inputs: List[NodePort]
    outputs: List[NodePort]
    node_type: str
    parameters: Dict = None


@dataclass
class Connection:
    """Соединение между узлами"""
    id: str
    from_node: str
    from_port: int
    to_node: str
    to_port: int


class NodeEditor(tk.Frame):
    """Визуальный редактор команд на основе нод"""
    
    def __init__(self, parent, width=800, height=600, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.width = width
        self.height = height
        self.nodes: Dict[str, Node] = {}
        self.connections: List[Connection] = []
        self.selected_node = None
        self.selected_connection = None
        self.dragging_node = None
        self.drag_offset = (0, 0)
        self.temp_connection = None
        
        self.node_counter = 0
        self.connection_counter = 0
        
        self.colors = {
            'bg': '#1e1e1e',
            'grid': '#2d2d2d',
            'node_bg': '#2d2d2d',
            'node_border': '#3c3c3c',
            'node_selected': '#007acc',
            'port_input': '#4CAF50',
            'port_output': '#FF9800',
            'connection': '#606060',
            'connection_selected': '#007acc',
            'text': '#d4d4d4',
            'text_secondary': '#858585'
        }
        
        self._setup_ui()
        self._bind_events()
        self._load_node_templates()
    
    def _setup_ui(self):
        """Настройка UI"""
        # Canvas
        self.canvas = tk.Canvas(
            self,
            bg=self.colors['bg'],
            highlightthickness=0,
            width=self.width,
            height=self.height
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Панель инструментов
        self.toolbar = tk.Frame(self, bg='#252526')
        self.toolbar.pack(fill=tk.X, before=self.canvas)
        
        btn_add = tk.Button(
            self.toolbar,
            text="+ Добавить узел",
            command=self._show_add_node_menu,
            bg='#0e639c',
            fg='white',
            relief=tk.FLAT,
            padx=10,
            pady=5
        )
        btn_add.pack(side=tk.LEFT, padx=5, pady=5)
        
        btn_delete = tk.Button(
            self.toolbar,
            text="Удалить",
            command=self._delete_selected,
            bg='#f44336',
            fg='white',
            relief=tk.FLAT,
            padx=10,
            pady=5
        )
        btn_delete.pack(side=tk.LEFT, padx=5, pady=5)
        
        btn_run = tk.Button(
            self.toolbar,
            text="▶ Выполнить",
            command=self._execute_graph,
            bg='#4CAF50',
            fg='white',
            relief=tk.FLAT,
            padx=10,
            pady=5
        )
        btn_run.pack(side=tk.LEFT, padx=5, pady=5)
        
        btn_save = tk.Button(
            self.toolbar,
            text="💾 Сохранить",
            command=self.save_graph,
            bg='#2196F3',
            fg='white',
            relief=tk.FLAT,
            padx=10,
            pady=5
        )
        btn_save.pack(side=tk.LEFT, padx=5, pady=5)
        
        btn_load = tk.Button(
            self.toolbar,
            text="📂 Загрузить",
            command=self.load_graph,
            bg='#FF9800',
            fg='white',
            relief=tk.FLAT,
            padx=10,
            pady=5
        )
        btn_load.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Статус бар
        self.status_var = tk.StringVar(value="Готов")
        status_bar = tk.Label(
            self,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            anchor=tk.W,
            bg='#007acc',
            fg='white'
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def _bind_events(self):
        """Привязка событий"""
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Delete>", lambda e: self._delete_selected())
        self.canvas.bind("<BackSpace>", lambda e: self._delete_selected())
    
    def _load_node_templates(self):
        """Загрузка шаблонов узлов"""
        self.node_templates = {
            "start": {
                "title": "Старт",
                "inputs": [],
                "outputs": [{"name": "out", "type": "any"}],
                "type": "start"
            },
            "command": {
                "title": "Команда PM3",
                "inputs": [{"name": "in", "type": "any"}],
                "outputs": [{"name": "out", "type": "any"}, {"name": "result", "type": "string"}],
                "type": "command",
                "parameters": {"command": ""}
            },
            "delay": {
                "title": "Задержка",
                "inputs": [{"name": "in", "type": "any"}],
                "outputs": [{"name": "out", "type": "any"}],
                "type": "delay",
                "parameters": {"milliseconds": 1000}
            },
            "condition": {
                "title": "Условие",
                "inputs": [{"name": "in", "type": "any"}],
                "outputs": [{"name": "true", "type": "any"}, {"name": "false", "type": "any"}],
                "type": "condition",
                "parameters": {"expression": ""}
            },
            "loop": {
                "title": "Цикл",
                "inputs": [{"name": "in", "type": "any"}],
                "outputs": [{"name": "body", "type": "any"}, {"name": "done", "type": "any"}],
                "type": "loop",
                "parameters": {"count": 1}
            },
            "variable": {
                "title": "Переменная",
                "inputs": [{"name": "value", "type": "any"}],
                "outputs": [{"name": "out", "type": "any"}],
                "type": "variable",
                "parameters": {"name": "", "value": ""}
            },
            "log": {
                "title": "Логирование",
                "inputs": [{"name": "in", "type": "any"}],
                "outputs": [{"name": "out", "type": "any"}],
                "type": "log",
                "parameters": {"message": ""}
            },
            "parse": {
                "title": "Парсинг ответа",
                "inputs": [{"name": "response", "type": "string"}],
                "outputs": [{"name": "parsed", "type": "any"}],
                "type": "parse",
                "parameters": {"pattern": ""}
            },
            "file_read": {
                "title": "Чтение файла",
                "inputs": [{"name": "trigger", "type": "any"}],
                "outputs": [{"name": "data", "type": "string"}],
                "type": "file_read",
                "parameters": {"filepath": ""}
            },
            "file_write": {
                "title": "Запись файла",
                "inputs": [{"name": "data", "type": "string"}],
                "outputs": [{"name": "done", "type": "any"}],
                "type": "file_write",
                "parameters": {"filepath": ""}
            }
        }
    
    def _create_node(self, template_name: str, x: float, y: float) -> Node:
        """Создание узла"""
        template = self.node_templates.get(template_name)
        if not template:
            return None
        
        self.node_counter += 1
        node_id = f"node_{self.node_counter}"
        
        inputs = [NodePort(p["name"], "input", p["type"]) for p in template.get("inputs", [])]
        outputs = [NodePort(p["name"], "output", p["type"]) for p in template.get("outputs", [])]
        
        node = Node(
            id=node_id,
            title=template["title"],
            x=x,
            y=y,
            inputs=inputs,
            outputs=outputs,
            node_type=template_name,
            parameters=template.get("parameters", {}).copy()
        )
        
        self.nodes[node_id] = node
        self._draw_node(node)
        self.status_var.set(f"Создан узел: {template['title']}")
        
        return node
    
    def _draw_node(self, node: Node):
        """Отрисовка узла"""
        # Размеры узла
        width = 150
        header_height = 30
        port_height = 25
        body_height = header_height + max(len(node.inputs), len(node.outputs)) * port_height + 20
        
        # Фон узла
        fill_color = self.colors['node_selected'] if node.id == self.selected_node else self.colors['node_bg']
        
        self.canvas.create_rectangle(
            node.x, node.y,
            node.x + width, node.y + body_height,
            fill=fill_color,
            outline=self.colors['node_border'],
            width=2,
            tags=f"node_{node.id}"
        )
        
        # Заголовок
        self.canvas.create_text(
            node.x + width/2, node.y + 15,
            text=node.title,
            fill=self.colors['text'],
            font=("Segoe UI", 10, "bold"),
            tags=f"node_{node.id}_title"
        )
        
        # Входные порты
        for i, port in enumerate(node.inputs):
            py = node.y + header_height + 10 + i * port_height
            self.canvas.create_oval(
                node.x - 10, py - 5,
                node.x, py + 5,
                fill=self.colors['port_input'],
                tags=f"port_{node.id}_in_{i}"
            )
            self.canvas.create_text(
                node.x + 5, py,
                text=port.name,
                anchor=tk.W,
                fill=self.colors['text_secondary'],
                font=("Segoe UI", 8),
                tags=f"port_{node.id}_in_{i}_label"
            )
        
        # Выходные порты
        for i, port in enumerate(node.outputs):
            py = node.y + header_height + 10 + i * port_height
            self.canvas.create_oval(
                node.x + width, py - 5,
                node.x + width + 10, py + 5,
                fill=self.colors['port_output'],
                tags=f"port_{node.id}_out_{i}"
            )
            self.canvas.create_text(
                node.x + width - 5, py,
                text=port.name,
                anchor=tk.E,
                fill=self.colors['text_secondary'],
                font=("Segoe UI", 8),
                tags=f"port_{node.id}_out_{i}_label"
            )
    
    def _draw_connections(self):
        """Отрисовка всех соединений"""
        self.canvas.delete("connection")
        
        for conn in self.connections:
            from_node = self.nodes.get(conn.from_node)
            to_node = self.nodes.get(conn.to_node)
            
            if not from_node or not to_node:
                continue
            
            # Координаты портов
            port_height = 25
            header_height = 30
            
            x1 = from_node.x + 150
            y1 = from_node.y + header_height + 10 + conn.from_port * port_height
            
            x2 = to_node.x
            y2 = to_node.y + header_height + 10 + conn.to_port * port_height
            
            # Кривая Безье
            ctrl_x1 = x1 + 50
            ctrl_x2 = x2 - 50
            
            color = self.colors['connection_selected'] if conn.id == self.selected_connection else self.colors['connection']
            
            self.canvas.create_bezier_arc(
                x1, y1, ctrl_x1, y1, ctrl_x2, y2, x2, y2,
                smooth=True,
                fill='',
                outline=color,
                width=2,
                tags="connection"
            )
    
    def _on_click(self, event):
        """Обработка клика"""
        # Проверка попадания в порт
        items = self.canvas.find_overlapping(event.x-5, event.y-5, event.x+5, event.y+5)
        for item in items:
            tags = self.canvas.gettags(item)
            for tag in tags:
                if tag.startswith("port_") and "_out_" in tag:
                    # Начало создания соединения
                    parts = tag.split("_")
                    node_id = parts[1]
                    port_idx = int(parts[3])
                    self.temp_connection = (node_id, port_idx, event.x, event.y)
                    return
        
        # Проверка попадания в узел
        for node_id, node in self.nodes.items():
            if (node.x <= event.x <= node.x + 150 and 
                node.y <= event.y <= node.y + 100):
                self.selected_node = node_id
                self.dragging_node = node_id
                self.drag_offset = (event.x - node.x, event.y - node.y)
                self._redraw()
                return
        
        # Клик по фону
        self.selected_node = None
        self._redraw()
    
    def _on_drag(self, event):
        """Обработка перетаскивания"""
        if self.dragging_node:
            node = self.nodes[self.dragging_node]
            node.x = event.x - self.drag_offset[0]
            node.y = event.y - self.drag_offset[1]
            self._redraw()
        
        elif self.temp_connection:
            self._redraw()
            # Отрисовка временного соединения
            x1, y1 = self.temp_connection[2], self.temp_connection[3]
            self.canvas.create_line(x1, y1, event.x, event.y, 
                                   fill=self.colors['connection'], 
                                   width=2, dash=(5, 5))
    
    def _on_release(self, event):
        """Обработка отпускания"""
        if self.temp_connection:
            # Проверка попадания в входной порт
            items = self.canvas.find_overlapping(event.x-10, event.y-10, event.x+10, event.y+10)
            for item in items:
                tags = self.canvas.gettags(item)
                for tag in tags:
                    if tag.startswith("port_") and "_in_" in tag:
                        parts = tag.split("_")
                        to_node_id = parts[1]
                        to_port_idx = int(parts[3])
                        
                        from_node_id, from_port_idx, _, _ = self.temp_connection
                        
                        if from_node_id != to_node_id:  # Нельзя соединить узел сам с собой
                            self.connection_counter += 1
                            conn = Connection(
                                id=f"conn_{self.connection_counter}",
                                from_node=from_node_id,
                                from_port=from_port_idx,
                                to_node=to_node_id,
                                to_port=to_port_idx
                            )
                            self.connections.append(conn)
                        
                        self.temp_connection = None
                        self._redraw()
                        return
            
            self.temp_connection = None
            self._redraw()
        
        self.dragging_node = None
    
    def _on_right_click(self, event):
        """Правый клик - контекстное меню"""
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Добавить узел", command=self._show_add_node_menu)
        menu.add_command(label="Удалить", command=self._delete_selected)
        menu.add_separator()
        menu.add_command(label="Очистить всё", command=self._clear_all)
        menu.post(event.x_root, event.y_root)
    
    def _on_mousewheel(self, event):
        """Масштабирование"""
        # Можно добавить зум
        pass
    
    def _show_add_node_menu(self):
        """Показ меню добавления узла"""
        menu = tk.Menu(self, tearoff=0)
        for template_name, template in self.node_templates.items():
            menu.add_command(label=template["title"], 
                           command=lambda t=template_name: self._add_node_at_center(t))
        menu.post(self.winfo_rootx() + 50, self.winfo_rooty() + 50)
    
    def _add_node_at_center(self, template_name: str):
        """Добавление узла в центре"""
        x = self.canvas.winfo_width() / 2 - 75
        y = self.canvas.winfo_height() / 2 - 50
        self._create_node(template_name, x, y)
    
    def _delete_selected(self):
        """Удаление выбранного"""
        if self.selected_node:
            # Удаление узла и связанных соединений
            self.connections = [c for c in self.connections 
                              if c.from_node != self.selected_node and c.to_node != self.selected_node]
            del self.nodes[self.selected_node]
            self.selected_node = None
            self._redraw()
        
        if self.selected_connection:
            self.connections = [c for c in self.connections if c.id != self.selected_connection]
            self.selected_connection = None
            self._redraw()
    
    def _clear_all(self):
        """Очистка всего"""
        if messagebox.askyesno("Подтверждение", "Удалить все узлы и соединения?"):
            self.nodes.clear()
            self.connections.clear()
            self.canvas.delete("all")
    
    def _redraw(self):
        """Перерисовка"""
        self.canvas.delete("all")
        
        # Сетка
        self._draw_grid()
        
        # Соединения
        for conn in self.connections:
            self._draw_connection(conn)
        
        # Узлы
        for node in self.nodes.values():
            self._draw_node(node)
    
    def _draw_grid(self):
        """Отрисовка сетки"""
        grid_size = 50
        for x in range(0, self.width, grid_size):
            self.canvas.create_line(x, 0, x, self.height, fill=self.colors['grid'])
        for y in range(0, self.height, grid_size):
            self.canvas.create_line(0, y, self.width, y, fill=self.colors['grid'])
    
    def _draw_connection(self, conn: Connection):
        """Отрисовка соединения"""
        from_node = self.nodes.get(conn.from_node)
        to_node = self.nodes.get(conn.to_node)
        
        if not from_node or not to_node:
            return
        
        port_height = 25
        header_height = 30
        
        x1 = from_node.x + 150
        y1 = from_node.y + header_height + 10 + conn.from_port * port_height
        x2 = to_node.x
        y2 = to_node.y + header_height + 10 + conn.to_port * port_height
        
        # Кривая
        mid_x = (x1 + x2) / 2
        self.canvas.create_line(x1, y1, mid_x, y1, mid_x, y2, x2, y2,
                               fill=self.colors['connection'], width=2, smooth=True)
    
    def save_graph(self, filename: str = None):
        """Сохранение графа"""
        if not filename:
            filename = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
        
        if filename:
            data = {
                "nodes": [],
                "connections": []
            }
            
            for node in self.nodes.values():
                node_data = {
                    "id": node.id,
                    "title": node.title,
                    "x": node.x,
                    "y": node.y,
                    "type": node.node_type,
                    "parameters": node.parameters
                }
                data["nodes"].append(node_data)
            
            for conn in self.connections:
                conn_data = {
                    "id": conn.id,
                    "from_node": conn.from_node,
                    "from_port": conn.from_port,
                    "to_node": conn.to_node,
                    "to_port": conn.to_port
                }
                data["connections"].append(conn_data)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            self.status_var.set(f"Граф сохранен: {filename}")
    
    def load_graph(self, filename: str = None):
        """Загрузка графа"""
        if not filename:
            filename = filedialog.askopenfilename(
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
        
        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.nodes.clear()
            self.connections.clear()
            self.canvas.delete("all")
            
            for node_data in data.get("nodes", []):
                node = Node(
                    id=node_data["id"],
                    title=node_data["title"],
                    x=node_data["x"],
                    y=node_data["y"],
                    inputs=[],
                    outputs=[],
                    node_type=node_data["type"],
                    parameters=node_data.get("parameters", {})
                )
                # Восстановление портов на основе типа
                template = self.node_templates.get(node.node_type)
                if template:
                    node.inputs = [NodePort(p["name"], "input", p["type"]) 
                                  for p in template.get("inputs", [])]
                    node.outputs = [NodePort(p["name"], "output", p["type"]) 
                                   for p in template.get("outputs", [])]
                
                self.nodes[node.id] = node
                self._draw_node(node)
            
            for conn_data in data.get("connections", []):
                conn = Connection(
                    id=conn_data["id"],
                    from_node=conn_data["from_node"],
                    from_port=conn_data["from_port"],
                    to_node=conn_data["to_node"],
                    to_port=conn_data["to_port"]
                )
                self.connections.append(conn)
            
            self._draw_connections()
            self.status_var.set(f"Граф загружен: {filename}")
    
    def _execute_graph(self):
        """Выполнение графа команд"""
        # Поиск стартового узла
        start_node = None
        for node in self.nodes.values():
            if node.node_type == "start":
                start_node = node
                break
        
        if not start_node:
            messagebox.showwarning("Предупреждение", "Нет стартового узла!")
            return
        
        self.status_var.set("Выполнение графа...")
        # Здесь будет логика выполнения графа
        # Рекурсивное прохождение по соединениям и выполнение команд


if __name__ == "__main__":
    # Тестирование виджетов
    root = tk.Tk()
    root.title("ProxMaster - Test Widgets")
    
    # Создание тестового интерфейса
    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)
    
    # Вкладка Hex Editor
    hex_frame = tk.Frame(notebook)
    notebook.add(hex_frame, text="Hex Editor")
    hex_editor = HexEditor(hex_frame, width=800, height=600)
    hex_editor.pack(fill=tk.BOTH, expand=True)
    
    # Загрузка тестовых данных
    test_data = bytes(range(256)) * 4
    hex_editor.load_data(test_data)
    
    # Вкладка Node Editor
    node_frame = tk.Frame(notebook)
    notebook.add(node_frame, text="Node Editor")
    node_editor = NodeEditor(node_frame, width=800, height=600)
    node_editor.pack(fill=tk.BOTH, expand=True)
    
    root.mainloop()
