# -*- coding: utf-8 -*-
"""
ProxMaster Pro - Профессиональные редакторы
Hex Editor и Node Editor для визуального программирования команд
"""

import json
import os
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    HAS_TK = True
except ImportError:
    HAS_TK = False
    tk = None
    ttk = None
    messagebox = None
    filedialog = None

# Проверка наличия tkinter
if not HAS_TK:
    print("Предупреждение: tkinter недоступен. Редакторы не будут работать.")


@dataclass
class HexEditOperation:
    """Операция редактирования для Undo/Redo"""
    action_type: str  # insert, delete, replace
    position: int
    old_value: Optional[bytes] = None
    new_value: Optional[bytes] = None


class HexEditor(tk.Frame):
    """
    Продвинутый Hex редактор с поддержкой:
    - Просмотр и редактирование байтов в hex и ASCII
    - Выделение диапазонов
    - Копирование/Вставка
    - Undo/Redo
    - Поиск данных
    - Экспорт/Импорт файлов
    - Drag & Drop
    """
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.data = bytearray()
        self.original_data = bytearray()
        self.undo_stack: List[HexEditOperation] = []
        self.redo_stack: List[HexEditOperation] = []
        self.max_undo = 100
        
        self.bytes_per_row = 16
        self.selection_start = None
        self.selection_end = None
        self.cursor_position = 0
        
        self.modified = False
        self.filepath = None
        
        self._setup_ui()
        self._bind_events()
    
    def _setup_ui(self):
        """Настройка интерфейса"""
        # Панель инструментов
        toolbar = tk.Frame(self, bg='#333333')
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        # Кнопки
        buttons = [
            ("📂 Открыть", self.open_file),
            ("💾 Сохранить", self.save_file),
            ("💾 Как...", self.save_file_as),
            ("|", None),
            ("↩ Undo", self.undo),
            ("↪ Redo", self.redo),
            ("|", None),
            ("📋 Копировать", self.copy_selection),
            ("📓 Вставить", self.paste_selection),
            ("🔤 Заполнить", self.fill_selection),
            ("|", None),
            ("🔍 Найти", self.find_data),
            ("🗑 Очистить", self.clear_data),
        ]
        
        for text, command in buttons:
            if text == "|":
                tk.Label(toolbar, text="|", bg='#333333', fg='#666666').pack(side=tk.LEFT, padx=5)
            elif command:
                btn = tk.Button(toolbar, text=text, command=command, bg='#444444', fg='white',
                               activebackground='#555555', activeforeground='white', relief=tk.FLAT)
                btn.pack(side=tk.LEFT, padx=2)
                if "Undo" in text:
                    self.btn_undo = btn
                elif "Redo" in text:
                    self.btn_redo = btn
        
        # Статус бар
        self.status_label = tk.Label(toolbar, text="Позиция: 0 | Выделено: 0 байт", 
                                    bg='#333333', fg='white', font=('Consolas', 9))
        self.status_label.pack(side=tk.RIGHT, padx=10)
        
        # Canvas с прокруткой
        canvas_frame = tk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(canvas_frame, bg='#1e1e1e', highlightthickness=0)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Content frame внутри canvas
        self.content_frame = tk.Frame(self.canvas, bg='#1e1e1e')
        self.canvas_window = self.canvas.create_window((0, 0), window=self.content_frame, anchor='nw')
        
        self.content_frame.bind('<Configure>', self._on_content_configure)
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        
        # Переключатель режима
        mode_frame = tk.Frame(self, bg='#333333')
        mode_frame.pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(mode_frame, text="Режим:", bg='#333333', fg='white').pack(side=tk.LEFT, padx=5)
        
        self.mode_var = tk.StringVar(value='hex')
        tk.Radiobutton(mode_frame, text="Hex", variable=self.mode_var, value='hex',
                      command=self._update_display, bg='#333333', fg='white',
                      selectcolor='#555555', activebackground='#444444').pack(side=tk.LEFT)
        tk.Radiobutton(mode_frame, text="ASCII", variable=self.mode_var, value='ascii',
                      command=self._update_display, bg='#333333', fg='white',
                      selectcolor='#555555', activebackground='#444444').pack(side=tk.LEFT)
        
        # Информация о файле
        self.file_info_label = tk.Label(mode_frame, text="Нет файла", fg='#888888', bg='#333333')
        self.file_info_label.pack(side=tk.RIGHT, padx=5)
        
        # Инициализируем кнопки
        self.btn_undo = None
        self.btn_redo = None
    
    def _bind_events(self):
        """Привязка событий"""
        self.canvas.bind_all('<Control-z>', lambda e: self.undo())
        self.canvas.bind_all('<Control-y>', lambda e: self.redo())
        self.canvas.bind_all('<Control-c>', lambda e: self.copy_selection())
        self.canvas.bind_all('<Control-v>', lambda e: self.paste_selection())
        self.canvas.bind_all('<Control-a>', lambda e: self.select_all())
        self.canvas.bind_all('<Control-f>', lambda e: self.find_data())
        self.canvas.bind_all('<Control-s>', lambda e: self.save_file())
        self.canvas.bind_all('<Control-o>', lambda e: self.open_file())
    
    def _on_content_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
    
    def load_data(self, data: bytes, filepath: str = None):
        """Загрузить данные в редактор"""
        self.data = bytearray(data)
        self.original_data = bytearray(data)
        self.filepath = filepath
        self.modified = False
        self.undo_stack.clear()
        self.redo_stack.clear()
        self._update_display()
        self._update_status()
        self._update_buttons()
        
        if filepath:
            self.file_info_label.config(text=f"{os.path.basename(filepath)} ({len(data)} байт)")
        else:
            self.file_info_label.config(text=f"{len(data)} байт")
    
    def get_data(self) -> bytes:
        return bytes(self.data)
    
    def is_modified(self) -> bool:
        return self.modified
    
    def _update_display(self):
        """Обновить отображение данных"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        if not self.data:
            label = tk.Label(self.content_frame, text="Пусто (перетащите файл или вставьте данные)", 
                           fg='#888888', bg='#1e1e1e', font=('Arial', 10))
            label.pack(pady=20)
            return
        
        # Заголовок
        header = tk.Frame(self.content_frame, bg='#2d2d2d')
        header.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(header, text="Offset", width=10, anchor='w', 
                font=('Consolas', 10, 'bold'), bg='#2d2d2d', fg='white').pack(side=tk.LEFT)
        
        hex_frame = tk.Frame(header, bg='#2d2d2d')
        hex_frame.pack(side=tk.LEFT, padx=(5, 10))
        
        for i in range(self.bytes_per_row):
            tk.Label(hex_frame, text=f"{i:02X}", width=3, anchor='center',
                    font=('Consolas', 10, 'bold'), bg='#2d2d2d', fg='white').pack(side=tk.LEFT)
        
        tk.Label(header, text="ASCII", width=self.bytes_per_row + 2, 
                anchor='w', font=('Consolas', 10, 'bold'), bg='#2d2d2d', fg='white').pack(side=tk.LEFT)
        
        # Строки данных
        y_offset = 40
        cell_height = 20
        
        for row_start in range(0, len(self.data), self.bytes_per_row):
            row_end = min(row_start + self.bytes_per_row, len(self.data))
            row_data = self.data[row_start:row_end]
            
            row_frame = tk.Frame(self.content_frame, bg='#1e1e1e')
            row_frame.place(y=y_offset)
            
            # Offset
            tk.Label(row_frame, text=f"{row_start:08X}", width=10, anchor='w',
                    font=('Consolas', 10), bg='#1e1e1e', fg='#cccccc').pack(side=tk.LEFT)
            
            # Hex ячейки
            hex_frame = tk.Frame(row_frame, bg='#1e1e1e')
            hex_frame.pack(side=tk.LEFT, padx=(5, 10))
            
            for i, byte in enumerate(row_data):
                pos = row_start + i
                is_selected = (self.selection_start is not None and 
                              self.selection_end is not None and 
                              self.selection_start <= pos < self.selection_end)
                
                bg_color = '#ffff00' if is_selected else '#1e1e1e'
                fg_color = '#000000' if is_selected else '#00ff00'
                
                cell = tk.Label(hex_frame, text=f"{byte:02X}", width=3, anchor='center',
                               font=('Consolas', 10), bg=bg_color, fg=fg_color, relief=tk.FLAT)
                cell.pack(side=tk.LEFT)
                cell.bind('<Button-1>', lambda e, p=pos: self._on_click(p))
                cell.bind('<B1-Motion>', lambda e, p=pos: self._on_drag(p))
                cell.bind('<Double-Button-1>', lambda e, p=pos: self._on_double_click(p))
            
            # ASCII
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in row_data)
            tk.Label(row_frame, text=ascii_str, width=self.bytes_per_row + 2,
                    anchor='w', font=('Consolas', 10), bg='#1e1e1e', fg='#00ff00').pack(side=tk.LEFT)
            
            y_offset += cell_height
        
        self.content_frame.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
    
    def _on_click(self, position: int):
        self.selection_start = position
        self.selection_end = position + 1
        self.cursor_position = position
        self._update_display()
        self._update_status()
    
    def _on_drag(self, position: int):
        if self.selection_start is not None:
            self.selection_end = position + 1
            self._update_display()
            self._update_status()
    
    def _on_double_click(self, position: int):
        # Выделить байт
        self.selection_start = position
        self.selection_end = position + 1
        self._update_display()
    
    def _push_undo(self, action_type: str, position: int, 
                   old_value: bytes = None, new_value: bytes = None):
        operation = HexEditOperation(action_type, position, old_value, new_value)
        self.undo_stack.append(operation)
        
        if len(self.undo_stack) > self.max_undo:
            self.undo_stack.pop(0)
        
        self.redo_stack.clear()
        self._update_buttons()
    
    def undo(self):
        if not self.undo_stack:
            return
        
        op = self.undo_stack.pop()
        
        if op.action_type == 'replace' and op.old_value:
            for i, b in enumerate(op.old_value):
                pos = op.position + i
                if pos < len(self.data):
                    self.data[pos] = b
        
        self.redo_stack.append(op)
        self.modified = True
        self._update_display()
        self._update_buttons()
    
    def redo(self):
        if not self.redo_stack:
            return
        
        op = self.redo_stack.pop()
        
        if op.action_type == 'replace' and op.new_value:
            for i, b in enumerate(op.new_value):
                pos = op.position + i
                if pos < len(self.data):
                    self.data[pos] = b
        
        self.undo_stack.append(op)
        self.modified = True
        self._update_display()
        self._update_buttons()
    
    def _update_buttons(self):
        if hasattr(self, 'btn_undo'):
            self.btn_undo.config(state=tk.NORMAL if self.undo_stack else tk.DISABLED)
        if hasattr(self, 'btn_redo'):
            self.btn_redo.config(state=tk.NORMAL if self.redo_stack else tk.DISABLED)
    
    def _update_status(self):
        selected_count = 0
        if self.selection_start is not None and self.selection_end is not None:
            selected_count = abs(self.selection_end - self.selection_start)
        
        self.status_label.config(
            text=f"Позиция: {self.cursor_position:08X} | Выделено: {selected_count} байт"
        )
    
    def copy_selection(self):
        if self.selection_start is None or self.selection_end is None:
            return
        
        start = min(self.selection_start, self.selection_end)
        end = max(self.selection_start, self.selection_end)
        
        selected_data = self.data[start:end]
        hex_str = selected_data.hex().upper()
        
        self.clipboard_clear()
        self.clipboard_append(hex_str)
    
    def paste_selection(self):
        try:
            hex_str = self.clipboard_get()
            hex_str = ''.join(c for c in hex_str if c in '0123456789ABCDEFabcdef')
            
            if not hex_str:
                return
            
            pasted_data = bytes.fromhex(hex_str)
            insert_pos = self.cursor_position if self.cursor_position < len(self.data) else len(self.data)
            
            self._push_undo('insert', insert_pos, b'', pasted_data)
            
            for i, b in enumerate(pasted_data):
                self.data.insert(insert_pos + i, b)
            
            self.selection_start = insert_pos
            self.selection_end = insert_pos + len(pasted_data)
            self.modified = True
            
            self._update_display()
            self._update_status()
            
        except Exception as e:
            messagebox.showerror("Ошибка вставки", str(e))
    
    def select_all(self):
        if self.data:
            self.selection_start = 0
            self.selection_end = len(self.data)
            self._update_display()
            self._update_status()
    
    def fill_selection(self):
        if self.selection_start is None or self.selection_end is None:
            messagebox.showwarning("Предупреждение", "Сначала выделите диапазон байтов")
            return
        
        start = min(self.selection_start, self.selection_end)
        end = max(self.selection_start, self.selection_end)
        
        dialog = tk.Toplevel(self)
        dialog.title("Заполнить выделение")
        dialog.geometry("350x150")
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text=f"Диапазон: {start:08X} - {end:08X} ({end-start} байт)").pack(pady=5)
        
        frame = tk.Frame(dialog)
        frame.pack(pady=10)
        
        tk.Label(frame, text="Hex паттерн:").grid(row=0, column=0, padx=5, sticky='w')
        pattern_entry = tk.Entry(frame, width=30)
        pattern_entry.grid(row=0, column=1, padx=5)
        pattern_entry.insert(0, "00")
        
        def apply_fill():
            try:
                pattern = bytes.fromhex(pattern_entry.get().strip())
                if not pattern:
                    raise ValueError("Пустой паттерн")
                
                fill_data = (pattern * ((end - start) // len(pattern) + 1))[:end - start]
                
                old_data = bytes(self.data[start:end])
                self._push_undo('replace', start, old_data, fill_data)
                
                for i, b in enumerate(fill_data):
                    self.data[start + i] = b
                
                self.modified = True
                self._update_display()
                dialog.destroy()
                
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Заполнить", command=apply_fill).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Отмена", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
        
        dialog.wait_window()
    
    def find_data(self):
        dialog = tk.Toplevel(self)
        dialog.title("Поиск данных")
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text="Искать (hex):").pack(pady=5)
        
        search_entry = tk.Entry(dialog, width=50)
        search_entry.pack(pady=5)
        
        results_label = tk.Label(dialog, text="", fg='blue')
        results_label.pack(pady=5)
        
        def search():
            try:
                search_data = bytes.fromhex(search_entry.get().strip())
                if not search_data:
                    results_label.config(text="Пустой запрос")
                    return
                
                positions = []
                pos = 0
                while True:
                    idx = self.data.find(search_data, pos)
                    if idx == -1:
                        break
                    positions.append(idx)
                    pos = idx + 1
                
                if positions:
                    results_label.config(text=f"Найдено: {len(positions)} совпадений")
                    self.selection_start = positions[0]
                    self.selection_end = positions[0] + len(search_data)
                    self.cursor_position = positions[0]
                    self._update_display()
                else:
                    results_label.config(text="Не найдено")
                    
            except Exception as e:
                results_label.config(text=f"Ошибка: {e}")
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Найти", command=search).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
        
        dialog.wait_window()
    
    def clear_data(self):
        if self.data and messagebox.askyesno("Подтверждение", "Очистить все данные?"):
            self._push_undo('delete', 0, bytes(self.data), b'')
            self.data.clear()
            self.selection_start = None
            self.selection_end = None
            self.modified = True
            self._update_display()
    
    def open_file(self):
        filepath = filedialog.askopenfilename(
            title="Открыть файл",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        if filepath:
            self.load_file(filepath)
    
    def load_file(self, filepath: str):
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            self.load_data(data, filepath)
        except Exception as e:
            messagebox.showerror("Ошибка открытия файла", str(e))
    
    def save_file(self):
        if not self.filepath:
            return self.save_file_as()
        
        try:
            with open(self.filepath, 'wb') as f:
                f.write(self.data)
            self.modified = False
            self.original_data = bytearray(self.data)
            self.file_info_label.config(text=f"{os.path.basename(self.filepath)} ({len(self.data)} байт)")
            return True
        except Exception as e:
            messagebox.showerror("Ошибка сохранения", str(e))
            return False
    
    def save_file_as(self):
        filepath = filedialog.asksaveasfilename(
            title="Сохранить файл как",
            defaultextension=".bin",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        if filepath:
            self.filepath = filepath
            return self.save_file()
        return False


@dataclass
class NodePort:
    id: str
    name: str
    port_type: str  # input/output
    data_type: str
    value: Any = None
    connected_to: Optional[str] = None


@dataclass
class Node:
    id: str
    node_type: str
    title: str
    x: int = 0
    y: int = 0
    width: int = 150
    height: int = 80
    inputs: List[NodePort] = field(default_factory=list)
    outputs: List[NodePort] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    color: str = '#4CAF50'


@dataclass
class Connection:
    id: str
    source_node: str
    source_port: str
    target_node: str
    target_port: str


class NodeEditor(tk.Frame):
    """
    Визуальный редактор графов команд:
    - Создание и перемещение нод
    - Соединение нод линиями
    - Настройка параметров
    - Сохранение/загрузка графов
    - Выполнение графа
    """
    
    def __init__(self, parent, commands_manager=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.commands_manager = commands_manager
        self.nodes: Dict[str, Node] = {}
        self.connections: Dict[str, Connection] = {}
        self.next_node_id = 1
        self.next_connection_id = 1
        
        self.selected_node = None
        self.dragging_node = None
        self.drawing_connection = None
        self.mouse_pos = (0, 0)
        
        self._setup_ui()
        self._bind_events()
        self._create_default_nodes()
    
    def _setup_ui(self):
        """Настройка интерфейса"""
        # Панель инструментов
        toolbar = tk.Frame(self, bg='#333333')
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(toolbar, text="Добавить:", bg='#333333', fg='white').pack(side=tk.LEFT, padx=5)
        
        node_types = [
            ("📜 Команда", 'command'),
            ("📥 Вход", 'input'),
            ("📤 Выход", 'output'),
            ("📝 Переменная", 'variable'),
            ("❓ Условие", 'condition')
        ]
        
        for text, node_type in node_types:
            btn = tk.Button(toolbar, text=text, command=lambda t=node_type: self._add_node(t),
                          bg='#444444', fg='white', activebackground='#555555', relief=tk.FLAT)
            btn.pack(side=tk.LEFT, padx=2)
        
        tk.Label(toolbar, text="|", bg='#333333', fg='#666666').pack(side=tk.LEFT, padx=5)
        
        tk.Button(toolbar, text="💾 Сохранить", command=self.save_graph,
                 bg='#444444', fg='white', relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="📂 Загрузить", command=self.load_graph,
                 bg='#444444', fg='white', relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        tk.Button(toolbar, text="🗑 Очистить", command=self.clear_graph,
                 bg='#444444', fg='white', relief=tk.FLAT).pack(side=tk.LEFT, padx=2)
        
        tk.Button(toolbar, text="▶ Выполнить", command=self.run_graph,
                 bg='#4CAF50', fg='white', relief=tk.FLAT).pack(side=tk.RIGHT, padx=5)
        tk.Button(toolbar, text="🗑 Удалить", command=self.delete_selected,
                 bg='#f44336', fg='white', relief=tk.FLAT).pack(side=tk.RIGHT, padx=2)
        
        # Canvas
        canvas_frame = tk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(canvas_frame, bg='#1e1e1e', highlightthickness=0)
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        
        self.canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Панель свойств
        self.properties_panel = tk.Frame(self, bg='#333333', height=120)
        self.properties_panel.pack(fill=tk.X, padx=5, pady=5)
        self.properties_panel.pack_propagate(False)
        
        tk.Label(self.properties_panel, text="Свойства", bg='#333333', 
                fg='white', font=('Arial', 10, 'bold')).pack(anchor='w', padx=5, pady=2)
        
        self.properties_frame = tk.Frame(self.properties_panel, bg='#333333')
        self.properties_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
    
    def _bind_events(self):
        self.canvas.bind('<Button-1>', self._on_mouse_down)
        self.canvas.bind('<B1-Motion>', self._on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self._on_mouse_up)
        self.canvas.bind('<MouseWheel>', self._on_mouse_wheel)
        self.canvas.bind('<Motion>', self._on_mouse_move)
        self.canvas.bind('<Double-Button-1>', self._on_double_click)
        
        self.canvas.bind_all('<Delete>', lambda e: self.delete_selected())
        self.canvas.bind_all('<BackSpace>', lambda e: self.delete_selected())
    
    def _create_default_nodes(self):
        self._add_node('input', x=50, y=50, title="Старт")
    
    def _add_node(self, node_type: str, x: int = None, y: int = None, title: str = None) -> str:
        node_id = f"node_{self.next_node_id}"
        self.next_node_id += 1
        
        if x is None:
            x = 100 + len(self.nodes) * 20
        if y is None:
            y = 100
        
        inputs = []
        outputs = []
        properties = {}
        color = '#4CAF50'
        
        if node_type == 'command':
            title = title or "Команда"
            inputs = [
                NodePort(f"{node_id}_in_exec", "Выполнить", 'input', 'command'),
                NodePort(f"{node_id}_in_param", "Параметры", 'input', 'parameter')
            ]
            outputs = [
                NodePort(f"{node_id}_out_done", "Готово", 'output', 'command'),
                NodePort(f"{node_id}_out_result", "Результат", 'output', 'result')
            ]
            if self.commands_manager:
                properties['command_id'] = ''
                properties['parameters'] = {}
            color = '#2196F3'
            
        elif node_type == 'input':
            title = title or "Вход"
            outputs = [NodePort(f"{node_id}_out", "Выход", 'output', 'any')]
            properties['value'] = ''
            color = '#9C27B0'
            
        elif node_type == 'output':
            title = title or "Выход"
            inputs = [NodePort(f"{node_id}_in", "Вход", 'input', 'any')]
            color = '#FF9800'
            
        elif node_type == 'variable':
            title = title or "Переменная"
            inputs = [NodePort(f"{node_id}_in", "Записать", 'input', 'any')]
            outputs = [NodePort(f"{node_id}_out", "Читать", 'output', 'any')]
            properties['var_name'] = 'var1'
            properties['value'] = ''
            color = '#00BCD4'
            
        elif node_type == 'condition':
            title = title or "Условие"
            inputs = [
                NodePort(f"{node_id}_in", "Проверить", 'input', 'any'),
                NodePort(f"{node_id}_in_value", "Значение", 'input', 'any')
            ]
            outputs = [
                NodePort(f"{node_id}_out_true", "True", 'output', 'command'),
                NodePort(f"{node_id}_out_false", "False", 'output', 'command')
            ]
            properties['operator'] = '=='
            color = '#F44336'
        
        node = Node(node_id, node_type, title, x, y, 150, 80, inputs, outputs, properties, color)
        self.nodes[node_id] = node
        self._redraw()
        
        return node_id
    
    def _redraw(self):
        self.canvas.delete('all')
        
        # Рисуем соединения
        for conn in self.connections.values():
            self._draw_connection(conn)
        
        # Рисуем линию которую рисуют
        if self.drawing_connection:
            self._draw_temp_connection()
        
        # Рисуем ноды
        for node in self.nodes.values():
            self._draw_node(node)
    
    def _draw_node(self, node: Node):
        x, y = node.x, node.y
        w, h = node.width, node.height
        
        # Тень
        self.canvas.create_rectangle(x+3, y+3, x+w+3, y+h+3, fill='#333333', outline='')
        
        # Основная фигура
        is_selected = self.selected_node == node.id
        outline = '#0000FF' if is_selected else '#333333'
        width = 3 if is_selected else 1
        
        self.canvas.create_rectangle(x, y, x+w, y+h, fill=node.color, outline=outline, width=width)
        
        # Заголовок
        self.canvas.create_text(x+w//2, y+20, text=node.title, 
                               font=('Arial', 10, 'bold'), fill='white')
        
        # Тип
        self.canvas.create_text(x+w//2, y+35, text=node.node_type, 
                               font=('Arial', 8), fill='white')
        
        # Порты входа
        for i, port in enumerate(node.inputs):
            px, py = x+5, y+50+i*20
            self.canvas.create_oval(px-6, py-6, px+6, py+6, fill='#333', outline='white')
            self.canvas.create_text(px+15, py, text=port.name, 
                                   font=('Arial', 8), anchor='w', fill='white')
        
        # Порты выхода
        for i, port in enumerate(node.outputs):
            px, py = x+w-5, y+50+i*20
            self.canvas.create_oval(px-6, py-6, px+6, py+6, fill='#333', outline='white')
            self.canvas.create_text(px-15, py, text=port.name, 
                                   font=('Arial', 8), anchor='e', fill='white')
    
    def _draw_connection(self, conn: Connection):
        source = self.nodes.get(conn.source_node)
        target = self.nodes.get(conn.target_node)
        
        if not source or not target:
            return
        
        src_port = next((p for p in source.outputs if p.id == conn.source_port), None)
        tgt_port = next((p for p in target.inputs if p.id == conn.target_port), None)
        
        if not src_port or not tgt_port:
            return
        
        src_idx = source.outputs.index(src_port)
        tgt_idx = target.inputs.index(tgt_port)
        
        x1 = source.x + source.width - 5
        y1 = source.y + 50 + src_idx * 20
        x2 = target.x + 5
        y2 = target.y + 50 + tgt_idx * 20
        
        ctrl_x = (x1 + x2) / 2
        self.canvas.create_line(x1, y1, ctrl_x, y1, ctrl_x, y2, x2, y2, 
                               smooth=True, width=2, fill='#0066CC')
    
    def _draw_temp_connection(self):
        if not self.drawing_connection:
            return
        
        source = self.nodes.get(self.drawing_connection['source_node'])
        if not source:
            return
        
        src_port = next((p for p in source.outputs 
                        if p.id == self.drawing_connection['source_port']), None)
        if not src_port:
            return
        
        src_idx = source.outputs.index(src_port)
        x1 = source.x + source.width - 5
        y1 = source.y + 50 + src_idx * 20
        
        self.canvas.create_line(x1, y1, self.mouse_pos[0], self.mouse_pos[1], 
                               width=2, fill='#0066CC', dash=(5, 5))
    
    def _on_mouse_down(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        # Проверяем клик по ноде
        for node_id, node in self.nodes.items():
            if node.x <= x <= node.x + node.width and node.y <= y <= node.y + node.height:
                # Проверяем клик по порту
                for port in node.outputs:
                    px = node.x + node.width - 5
                    py = node.y + 50 + node.outputs.index(port) * 20
                    if abs(x - px) < 10 and abs(y - py) < 10:
                        self.drawing_connection = {
                            'source_node': node_id,
                            'source_port': port.id
                        }
                        return
                
                self.selected_node = node_id
                self.dragging_node = node_id
                self.drag_offset = (x - node.x, y - node.y)
                self._redraw()
                self._show_properties(node)
                return
        
        self.selected_node = None
        self._redraw()
    
    def _on_mouse_drag(self, event):
        self.mouse_pos = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        
        if self.dragging_node and self.dragging_node in self.nodes:
            node = self.nodes[self.dragging_node]
            node.x = self.mouse_pos[0] - self.drag_offset[0]
            node.y = self.mouse_pos[1] - self.drag_offset[1]
            self._redraw()
    
    def _on_mouse_up(self, event):
        if self.drawing_connection:
            x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            
            # Проверяем попадание в порт входа
            for node_id, node in self.nodes.items():
                if node_id == self.drawing_connection['source_node']:
                    continue
                
                for port in node.inputs:
                    px, py = node.x + 5, node.y + 50 + node.inputs.index(port) * 20
                    if abs(x - px) < 10 and abs(y - py) < 10:
                        # Создаем соединение
                        conn_id = f"conn_{self.next_connection_id}"
                        self.next_connection_id += 1
                        
                        conn = Connection(
                            conn_id,
                            self.drawing_connection['source_node'],
                            self.drawing_connection['source_port'],
                            node_id,
                            port.id
                        )
                        self.connections[conn_id] = conn
                        break
        
        self.drawing_connection = None
        self.dragging_node = None
        self._redraw()
    
    def _on_mouse_move(self, event):
        self.mouse_pos = (self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))
        if self.drawing_connection:
            self._redraw()
    
    def _on_mouse_wheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def _on_double_click(self, event):
        x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        
        for node_id, node in self.nodes.items():
            if node.x <= x <= node.x + node.width and node.y <= y <= node.y + node.height:
                self._edit_node_properties(node)
                return
    
    def _show_properties(self, node: Node):
        for widget in self.properties_frame.winfo_children():
            widget.destroy()
        
        tk.Label(self.properties_frame, text=f"ID: {node.id}", 
                bg='#333333', fg='white').pack(anchor='w', padx=5)
        
        tk.Label(self.properties_frame, text=f"Тип: {node.node_type}", 
                bg='#333333', fg='white').pack(anchor='w', padx=5)
        
        # Редактируемые свойства
        tk.Label(self.properties_frame, text="Название:", 
                bg='#333333', fg='white').pack(anchor='w', padx=5, pady=(10, 0))
        
        title_entry = tk.Entry(self.properties_frame)
        title_entry.insert(0, node.title)
        title_entry.pack(fill=tk.X, padx=5)
        
        def update_title():
            node.title = title_entry.get()
            self._redraw()
        
        title_entry.bind('<Return>', lambda e: update_title())
        title_entry.bind('<FocusOut>', lambda e: update_title())
    
    def _edit_node_properties(self, node: Node):
        dialog = tk.Toplevel(self)
        dialog.title(f"Свойства: {node.title}")
        dialog.geometry("400x300")
        dialog.transient(self)
        dialog.grab_set()
        
        tk.Label(dialog, text=f"Тип: {node.node_type}").pack(pady=5)
        
        frame = tk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        tk.Label(frame, text="Название:").grid(row=0, column=0, sticky='w', pady=5)
        title_entry = tk.Entry(frame, width=30)
        title_entry.grid(row=0, column=1, pady=5)
        title_entry.insert(0, node.title)
        
        if 'command_id' in node.properties:
            tk.Label(frame, text="Команда:").grid(row=1, column=0, sticky='w', pady=5)
            cmd_combo = ttk.Combobox(frame, width=27, 
                                    values=list(self.commands_manager.commands.keys()) 
                                            if self.commands_manager else [])
            cmd_combo.grid(row=1, column=1, pady=5)
            cmd_combo.set(node.properties.get('command_id', ''))
        
        def save():
            node.title = title_entry.get()
            self._redraw()
            dialog.destroy()
        
        btn_frame = tk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Сохранить", command=save).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Отмена", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
        
        dialog.wait_window()
    
    def delete_selected(self):
        if self.selected_node and self.selected_node in self.nodes:
            # Удаляем соединения
            to_remove = [cid for cid, conn in self.connections.items()
                        if conn.source_node == self.selected_node or 
                           conn.target_node == self.selected_node]
            for cid in to_remove:
                del self.connections[cid]
            
            del self.nodes[self.selected_node]
            self.selected_node = None
            self._redraw()
    
    def clear_graph(self):
        if messagebox.askyesno("Подтверждение", "Удалить все ноды?"):
            self.nodes.clear()
            self.connections.clear()
            self.next_node_id = 1
            self.next_connection_id = 1
            self._redraw()
    
    def save_graph(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        
        if filepath:
            data = {
                'nodes': [
                    {
                        'id': n.id,
                        'type': n.node_type,
                        'title': n.title,
                        'x': n.x,
                        'y': n.y,
                        'properties': n.properties
                    }
                    for n in self.nodes.values()
                ],
                'connections': [
                    {
                        'id': c.id,
                        'source_node': c.source_node,
                        'source_port': c.source_port,
                        'target_node': c.target_node,
                        'target_port': c.target_port
                    }
                    for c in self.connections.values()
                ]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Успешно", "Граф сохранен")
    
    def load_graph(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self.nodes.clear()
                self.connections.clear()
                
                for n in data.get('nodes', []):
                    node_type = n.get('type', 'command')
                    node_id = self._add_node(
                        node_type, 
                        x=n.get('x', 100), 
                        y=n.get('y', 100), 
                        title=n.get('title', node_type.capitalize())
                    )
                    node = self.nodes[node_id]
                    node.properties = n.get('properties', {})
                
                for c in data.get('connections', []):
                    conn_id = f"conn_{self.next_connection_id}"
                    self.next_connection_id += 1
                    
                    conn = Connection(
                        conn_id,
                        c['source_node'],
                        c['source_port'],
                        c['target_node'],
                        c['target_port']
                    )
                    self.connections[conn_id] = conn
                
                self._redraw()
                messagebox.showinfo("Успешно", "Граф загружен")
                
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
    
    def run_graph(self):
        self.master._log_message("Запуск графа команд...", LogLevel.INFO)
        # TODO: Реализовать выполнение графа
        messagebox.showinfo("Инфо", "Выполнение графа в разработке")


__all__ = ['HexEditor', 'NodeEditor']
