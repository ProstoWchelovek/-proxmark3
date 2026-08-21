#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proxmark3 Easy Iceman GUI - Графическая оболочка для управления Proxmark3"""

import sys
import os
import warnings
from datetime import datetime

# Подавляем предупреждения DeprecationWarning
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ====== ФИКС ДЛЯ КИРИЛЛИЦЫ В ПУТЯХ ======
if sys.platform == 'win32':
    # Устанавливаем правильную кодировку для консоли
    if hasattr(sys, 'setdefaultencoding'):
        sys.setdefaultencoding('utf-8')
    else:
        # Для Python 3 используем sys.stdout
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

# ЯВНО УКАЗЫВАЕМ ПУТЬ К ПЛАГИНАМ (БЕЗ КИРИЛЛИЦЫ)
# ИСПОЛЬЗУЙТЕ СВОЙ ПУТЬ - проверьте где у вас установлен Python
QT_PLUGIN_PATH = r"C:\Users\Никита\AppData\Local\Programs\Python\Python314\Lib\site-packages\PyQt5\Qt5\plugins"

# Проверяем существование пути
if os.path.exists(QT_PLUGIN_PATH):
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = QT_PLUGIN_PATH
    print(f"✓ Путь к плагинам установлен: {QT_PLUGIN_PATH}")
else:
    # Пробуем найти альтернативный путь
    import glob
    possible_paths = glob.glob(r"C:\Users\*\AppData\Local\Programs\Python\Python314\Lib\site-packages\PyQt5\Qt5\plugins")
    if possible_paths:
        QT_PLUGIN_PATH = possible_paths[0]
        os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = QT_PLUGIN_PATH
        print(f"✓ Альтернативный путь найден: {QT_PLUGIN_PATH}")
    else:
        print("⚠️ ВНИМАНИЕ: Путь к плагинам не найден!")

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QPushButton, QLabel, QComboBox, QScrollArea,
    QGroupBox, QTextEdit, QCheckBox, QLineEdit,
    QStatusBar, QDialog, QDialogButtonBox, QGridLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

LF_PROTOCOLS = ["EM4100", "EM4x05", "EM4x50", "EM4x70", "T55xx", "HID", "AWID",
    "Hitag", "Hitag S", "Hitag µ", "FDX-B", "Destron", "COTAG", "Gallagher",
    "GProx II", "Idteck", "Indala", "IO Prox", "Jablotron", "Keri", "Motorola",
    "Nedap", "NexWatch", "Noralsy", "PAC", "Paradox", "PCF7931", "Presco",
    "Pyramid", "Securakey", "TI", "Trovan", "Viking", "VISA 2000", "ZX8211"]

HF_PROTOCOLS = ["ISO 14443A", "ISO 14443B", "ISO 15693", "Mifare Classic",
    "Mifare Ultralight", "Mifare DESFire", "Mifare Plus", "iClass", "Legic",
    "FeliCa", "Calypso", "CIPURSE", "SEOS", "SECC", "Topaz", "Saflok", "ST25TA",
    "NTAG 424", "Apple VAS", "ALIRO", "EMRTD", "EPA", "FIDO", "ICT", "Jooki",
    "KS X 6924", "LTO", "Fudan", "CryptoRF", "GST", "Gallagher HF", "ST",
    "Tesla", "Texkom", "Thinfilm", "Xerox", "Waveshare", "FMCOS", "Mifare SEN"]

EXTRA_PROTOCOLS = ["NFC", "EMV", "Smart card ISO 7816", "PIV"]
DICTIONARIES = ["mfc_default_keys.dic", "iclass_default_keys.dic", "ht2_default.dic",
    "t55xx_default_pwds.dic", "mfdes_default_keys.dic", "mfp_default_keys.dic"]
PYTHON_SCRIPTS = ["amiibo_change_uid", "pm3", "spi_flash_decode", "xorcheck"]
LUA_SCRIPTS = ["hf_mf_autopwn", "lf_t55xx_chk", "data_hex_crc", "ntag_clean"]
DANGEROUS_OPERATIONS = [
    ("mem wipe", "mem wipe", "Полная очистка памяти"),
    ("hf mf gen3freeze", "hf mf gen3freeze", "Блокировка Gen3"),
    ("hf 15 cfinalize", "hf 15 cfinalize", "Финализация ISO 15693"),
    ("hf cipurse formatall", "hf cipurse formatall", "Форматирование CIPURSE"),
    ("hf mfdes formatpicc", "hf mfdes formatpicc", "Форматирование DESFire"),
    ("lf t55xx wipe", "lf t55xx wipe", "Очистка T55xx")]


class InfoIcon(QLabel):
    """Иконка информации: !! если есть info команда, ! если нет"""
    def __init__(self, cmd_data, callback=None, parent=None):
        super().__init__("!!" if cmd_data.get("has_info") else "!", parent)
        self.callback = callback
        self.setFixedSize(24, 24)
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        bg = "#4CAF50" if cmd_data.get("has_info") else "#2196F3"
        self.setStyleSheet(f"QLabel{{background:{bg};color:white;border-radius:12px;font-weight:bold}}")
        tt = f"<b>{cmd_data.get('cmd','')}</b><br>{cmd_data.get('desc','')}"
        if cmd_data.get('params'): 
            tt += f"<br><i>{cmd_data['params']}</i>"
        self.setToolTip(tt)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.callback:
            self.callback()


class CmdBtn(QPushButton):
    """Кнопка команды с иконкой информации"""
    def __init__(self, text, cmd_data, exec_cb, info_cb=None, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.addWidget(QLabel(text))
        layout.addStretch()
        layout.addWidget(InfoIcon(cmd_data, info_cb))
        self.setMinimumHeight(35)
        self.clicked.connect(lambda: exec_cb(cmd_data["cmd"]))


class PM3Thread(QThread):
    """Поток выполнения команд"""
    result_ready = pyqtSignal(str)
    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd
    def run(self):
        self.result_ready.emit(f"Выполнено: {self.cmd}\n[ДЕМО режим - подключите Proxmark3]")


class ConfirmDlg(QDialog):
    """Диалог подтверждения опасных операций"""
    def __init__(self, name, desc, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚠️ Подтверждение")
        self.setModal(True)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"<b style='color:red'>ОПАСНАЯ ОПЕРАЦИЯ</b><br>{name}<br>{desc}"))
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Подтверждаю")
        btns.button(QDialogButtonBox.Ok).setStyleSheet("background:#f44336;color:white")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)


class PM3GUI(QMainWindow):
    """Основное окно приложения"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proxmark3 Easy Iceman GUI")
        self.setMinimumSize(1200, 800)
        self.connected = False
        self.thread = None
        self.init_ui()
        self.apply_style()

    def init_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        lay = QVBoxLayout(cw)
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.South)
        lay.addWidget(self.tabs)
        self.info = QTextEdit()
        self.info.setMaximumHeight(150)
        self.info.setReadOnly(True)
        self.info.setFont(QFont("Consolas", 10))
        lay.addWidget(self.info)
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_label = QLabel("🔴 Не подключено")
        self.status.addWidget(self.status_label)
        self.create_tabs()

    def apply_style(self):
        self.setStyleSheet("""QMainWindow{background:#f5f5f5}QTabWidget::pane{border:1px solid #ccc;background:white}
            QTabBar::tab{background:#e0e0e0;padding:10px 20px}QTabBar::tab:selected{background:white}
            QPushButton{background:#2196F3;color:white;border:none;padding:8px;border-radius:4px}
            QPushButton:hover{background:#1976D2}QGroupBox{font-weight:bold;border:2px solid #2196F3;margin-top:10px}
            QGroupBox::title{subcontrol-origin:margin;left:10px;color:#2196F3}
            QComboBox{padding:5px;border:1px solid #ccc}QTextEdit{background:#fafafa}""")

    def log(self, msg):
        self.info.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        self.info.verticalScrollBar().setValue(self.info.verticalScrollBar().maximum())

    def exec_cmd(self, cmd):
        self.log(f">>> {cmd}")
        if self.thread and self.thread.isRunning():
            self.thread.terminate()
        self.thread = PM3Thread(cmd)
        self.thread.result_ready.connect(lambda r: (self.info.append(r), self.info.append("-"*60)))
        self.thread.start()

    def exec_info(self, cmd):
        self.log(f"[INFO] >>> {cmd}")
        if self.thread and self.thread.isRunning():
            self.thread.terminate()
        self.thread = PM3Thread(cmd)
        self.thread.result_ready.connect(lambda r: (self.info.append(r), self.info.append("-"*60)))
        self.thread.start()

    def toggle_conn(self):
        self.connected = not self.connected
        self.conn_btn.setText("Отключить" if self.connected else "Подключить")
        self.status_label.setText("🟢 Подключено" if self.connected else "🔴 Отключено")
        self.status_label.setStyleSheet("color:" + ("#4CAF50" if self.connected else "#f44336"))
        self.log("Подключено" if self.connected else "Отключено")

    def confirm_danger(self, name, cmd, desc):
        if ConfirmDlg(name, desc, self).exec_() == QDialog.Accepted:
            self.exec_cmd(cmd)

    def mk_btn(self, name, cmd, has_info=False, desc=""):
        return CmdBtn(name, {"cmd": cmd, "has_info": has_info, "desc": desc}, self.exec_cmd,
                      lambda c=cmd: self.exec_info(c) if has_info else None, self)

    def create_tabs(self):
        # Вкладка 1: Главная
        t1 = QWidget()
        l1 = QVBoxLayout(t1)
        sa1 = QScrollArea()
        sa1.setWidgetResizable(True)
        c1 = QWidget()
        cl1 = QVBoxLayout(c1)
        g1 = QGroupBox("Подключение")
        gl1 = QHBoxLayout(g1)
        self.conn_btn = self.mk_btn("Подключить", "hw connect", False, "Подключение к Proxmark3")
        self.conn_btn.clicked.disconnect()
        self.conn_btn.clicked.connect(self.toggle_conn)
        gl1.addWidget(self.conn_btn)
        self.status_label = QLabel("🔴 Отключено")
        self.status_label.setStyleSheet("font-size:14px;font-weight:bold")
        gl1.addWidget(self.status_label)
        gl1.addStretch()
        cl1.addWidget(g1)
        g2 = QGroupBox("Команды")
        gl2 = QGridLayout(g2)
        cmds = [("Версии", "hw version", True), ("Антенны", "hw tune", True), ("Автопоиск", "auto", False)]
        for i, (n, c, h) in enumerate(cmds):
            gl2.addWidget(self.mk_btn(n, c, h), i // 2, i % 2)
        cl1.addWidget(g2)
        cl1.addStretch()
        sa1.setWidget(c1)
        l1.addWidget(sa1)
        self.tabs.addTab(t1, "Главная")

        # Вкладка 2: Карта
        t2 = QWidget()
        l2 = QVBoxLayout(t2)
        sa2 = QScrollArea()
        sa2.setWidgetResizable(True)
        c2 = QWidget()
        cl2 = QVBoxLayout(c2)
        
        # Выбор протокола
        proto_group = QGroupBox("Выбор протокола")
        proto_layout = QHBoxLayout(proto_group)
        proto = QComboBox()
        proto.addItems(["▼ Протокол"] + LF_PROTOCOLS + HF_PROTOCOLS + EXTRA_PROTOCOLS)
        proto_layout.addWidget(QLabel("Протокол:"))
        proto_layout.addWidget(proto)
        proto_layout.addStretch()
        cl2.addWidget(proto_group)
        
        for step, title, cmds in [
            (1, "ПОИСК", [("ОБЩИЙ ПОИСК", "auto"), ("ПОИСК LF", "lf search"), ("ПОИСК HF", "hf search")]),
            (2, "ЧТЕНИЕ", [("MF дамп", "hf mf dump"), ("iClass дамп", "hf iclass dump"), ("T55xx дамп", "lf t55xx dump")]),
            (3, "СТРУКТУРА", [("ACL", "hf mf acl"), ("MAD", "hf mf mad"), ("DESFire apps", "hf mfdes lsapp")]),
            (4, "КЛЮЧИ", [("MF chk", "hf mf chk"), ("iClass chk", "hf iclass chk"), ("T55xx chk", "lf t55xx chk")]),
            (5, "АТАКИ", [("Nested", "hf mf nested"), ("Hardnested", "hf mf hardnested"), ("loclass", "hf iclass loclass")])]:
            g = QGroupBox(f"ШАГ {step}: {title}")
            gl = QGridLayout(g)
            for i, (n, c) in enumerate(cmds):
                gl.addWidget(self.mk_btn(n, c, False), i // 3, i % 3)
            cl2.addWidget(g)
        
        rg = QGroupBox("ШАГ 6: РЕЗУЛЬТАТ")
        rl = QHBoxLayout(rg)
        for n, c in [("Сохранить", "data save"), ("Трейс", "trace list"), ("Экспорт", "trace save")]:
            rl.addWidget(self.mk_btn(n, c, False))
        for n in ["Запись", "Эмуляция", "Данные"]:
            rl.addWidget(QPushButton(n))
        cl2.addWidget(rg)
        cl2.addStretch()
        sa2.setWidget(c2)
        l2.addWidget(sa2)
        self.tabs.addTab(t2, "Карта")

        # Вкладка 3: Запись
        t3 = QWidget()
        l3 = QVBoxLayout(t3)
        sa3 = QScrollArea()
        sa3.setWidgetResizable(True)
        c3 = QWidget()
        cl3 = QVBoxLayout(c3)
        for step, title, cmds in [
            (1, "ИСТОЧНИК", [("Из файла", "data load"), ("Из буфера", ""), ("Из карт", "")]),
            (2, "ЦЕЛЬ", [("Определить", "auto")]),
            (3, "ЗАПИСЬ", [("MF wrbl", "hf mf wrbl"), ("DESFire write", "hf mfdes write"), ("T55xx write", "lf t55xx write")]),
            (4, "ВЕРИФИКАЦИЯ", [("Проверить", "auto")])]:
            g = QGroupBox(f"ШАГ {step}: {title}")
            gl = QHBoxLayout(g)
            for n, c in cmds:
                if c:
                    gl.addWidget(self.mk_btn(n, c, False))
                else:
                    gl.addWidget(QPushButton(n))
            cl3.addWidget(g)
        cl3.addStretch()
        sa3.setWidget(c3)
        l3.addWidget(sa3)
        self.tabs.addTab(t3, "Запись")

        # Вкладка 4: Снифинг
        t4 = QWidget()
        l4 = QVBoxLayout(t4)
        sa4 = QScrollArea()
        sa4.setWidgetResizable(True)
        c4 = QWidget()
        cl4 = QVBoxLayout(c4)
        g = QGroupBox("ШАГ 1: ТИП")
        gl = QGridLayout(g)
        types = [("HF общий", "hf sniff"), ("14443A", "hf 14a sniff"), ("14443B", "hf 14b sniff"),
                 ("15693", "hf 15 sniff"), ("LF", "lf sniff"), ("Legic", "hf legic sniff"), ("iClass", "hf iclass sniff")]
        for i, (n, c) in enumerate(types):
            gl.addWidget(self.mk_btn(n, c, False), i // 3, i % 3)
        cl4.addWidget(g)
        g2 = QGroupBox("ШАГ 2: ЗАХВАТ")
        gl2 = QHBoxLayout(g2)
        gl2.addWidget(self.mk_btn("Старт", "hf sniff", False))
        gl2.addWidget(self.mk_btn("Стоп", "hw break", False))
        cl4.addWidget(g2)
        g3 = QGroupBox("ШАГ 3: АНАЛИЗ")
        gl3 = QGridLayout(g3)
        for i, (n, c) in enumerate([("Разбор", "trace list"), ("Extract", "trace extract"), ("Save", "trace save"), ("Load", "trace load")]):
            gl3.addWidget(self.mk_btn(n, c, False), i // 2, i % 2)
        cl4.addWidget(g3)
        cl4.addStretch()
        sa4.setWidget(c4)
        l4.addWidget(sa4)
        self.tabs.addTab(t4, "Снифинг")

        # Вкладка 5: Эмуляция
        t5 = QWidget()
        l5 = QVBoxLayout(t5)
        sa5 = QScrollArea()
        sa5.setWidgetResizable(True)
        c5 = QWidget()
        cl5 = QVBoxLayout(c5)
        g = QGroupBox("ШАГ 1: ИСТОЧНИК")
        gl = QHBoxLayout(g)
        for n in ["Из файла", "Из карт", "Из буфера", "Вручную"]:
            gl.addWidget(QPushButton(n) if n != "Из файла" else self.mk_btn(n, "hf mf eload", False))
        cl5.addWidget(g)
        g2 = QGroupBox("ШАГ 2: ЗАГРУЗКА")
        gl2 = QGridLayout(g2)
        for i, (n, c) in enumerate([("MF", "hf mf eload"), ("UL", "hf mfu eload"), ("iClass", "hf iclass eload"), ("Legic", "hf legic eload")]):
            gl2.addWidget(self.mk_btn(n, c, False), i // 2, i % 2)
        cl5.addWidget(g2)
        g3 = QGroupBox("ШАГ 3: ТИП")
        gl3 = QGridLayout(g3)
        for i, (n, c) in enumerate([("MF sim", "hf mf sim"), ("UL sim", "hf mfu sim"), ("iClass sim", "hf iclass sim"), ("14a sim", "hf 14a sim")]):
            gl3.addWidget(self.mk_btn(n, c, False), i // 2, i % 2)
        cl5.addWidget(g3)
        g4 = QGroupBox("ШАГ 4: ЗАПУСК")
        gl4 = QHBoxLayout(g4)
        gl4.addWidget(self.mk_btn("Старт", "hf mf sim", False))
        gl4.addWidget(self.mk_btn("Стоп", "hw break", False))
        cl5.addWidget(g4)
        cl5.addStretch()
        sa5.setWidget(c5)
        l5.addWidget(sa5)
        self.tabs.addTab(t5, "Эмуляция")

        # Вкладка 6: Данные
        t6 = QWidget()
        l6 = QVBoxLayout(t6)
        sa6 = QScrollArea()
        sa6.setWidgetResizable(True)
        c6 = QWidget()
        cl6 = QVBoxLayout(c6)
        groups = [
            ("Дампы", [("Загрузить", "data load"), ("Сохранить", "data save"), ("Удалить", "")]),
            ("Словари", [("mfc_default_keys.dic", ""), ("iclass_default.dic", "")]),
            ("Flash", [("mem info", "mem info"), ("mem dump", "mem dump"), ("mem wipe", "mem wipe")]),
            ("Трейсы", [("trace list", "trace list"), ("trace save", "trace save"), ("trace load", "trace load")]),
            ("Буфер", [("data plot", "data plot"), ("data rawdemod", "data rawdemod"), ("data hexsamples", "data hexsamples")]),
            ("MAD", [("mad read", "mad read"), ("mad decode", "mad decode")]),
            ("Ресурсы", [("aidlist.json", ""), ("capk.txt", ""), ("mad.json", "")])]
        for title, cmds in groups:
            g = QGroupBox(title)
            gl = QHBoxLayout(g)
            for n, c in cmds:
                if c:
                    gl.addWidget(self.mk_btn(n, c, False))
                else:
                    gl.addWidget(QPushButton(n))
            cl6.addWidget(g)
        cl6.addStretch()
        sa6.setWidget(c6)
        l6.addWidget(sa6)
        self.tabs.addTab(t6, "Данные")

        # Вкладка 7: Инструменты
        t7 = QWidget()
        l7 = QVBoxLayout(t7)
        sa7 = QScrollArea()
        sa7.setWidgetResizable(True)
        c7 = QWidget()
        cl7 = QVBoxLayout(c7)
        groups = [
            ("Analyse", ["lrc", "crc", "chksum", "dates", "lfsr", "nuid"]),
            ("Wiegand", [("list", "wiegand list"), ("encode", "wiegand encode"), ("decode", "wiegand decode")]),
            ("RevEng", [("calc", "reveng calc"), ("search", "reveng search")]),
            ("USART", ["usart tx", "usart rx", "usart txhex", "usart btpin"]),
            ("MQTT", [("send", "mqtt send"), ("receive", "mqtt receive")]),
            ("HF спец", ["hf plot", "hf tune", "hf 14a config"]),
            ("LF спец", ["lf config", "lf cmdread", "lf relay"])]
        for title, cmds in groups:
            g = QGroupBox(title)
            gl = QGridLayout(g)
            for i, item in enumerate(cmds):
                if isinstance(item, tuple):
                    n, c = item
                    gl.addWidget(self.mk_btn(n, c, False), i // 3, i % 3)
                else:
                    gl.addWidget(self.mk_btn(item, f"{title.lower()} {item}", False), i // 3, i % 3)
            cl7.addWidget(g)
        cl7.addStretch()
        sa7.setWidget(c7)
        l7.addWidget(sa7)
        self.tabs.addTab(t7, "Инструменты")

        # Вкладка 8: Скрипты
        t8 = QWidget()
        l8 = QVBoxLayout(t8)
        sa8 = QScrollArea()
        sa8.setWidgetResizable(True)
        c8 = QWidget()
        cl8 = QVBoxLayout(c8)
        g = QGroupBox("Управление")
        gl = QHBoxLayout(g)
        gl.addWidget(self.mk_btn("Список", "script list", False))
        sc = QComboBox()
        sc.addItems(["Выбрать"] + PYTHON_SCRIPTS + LUA_SCRIPTS)
        gl.addWidget(sc)
        run = QPushButton("Запустить")
        run.clicked.connect(lambda: self.exec_cmd(f"script run {sc.currentText()}"))
        gl.addWidget(run)
        cl8.addWidget(g)
        pg = QGroupBox("Python")
        pgl = QGridLayout(pg)
        for i, s in enumerate(PYTHON_SCRIPTS):
            b = QPushButton(s)
            b.clicked.connect(lambda x, ss=s: self.exec_cmd(f"script run {ss}.py"))
            pgl.addWidget(b, i // 4, i % 4)
        cl8.addWidget(pg)
        lg = QGroupBox("Lua")
        lgl = QGridLayout(lg)
        for i, s in enumerate(LUA_SCRIPTS):
            b = QPushButton(s)
            b.clicked.connect(lambda x, ss=s: self.exec_cmd(f"script run {ss}.lua"))
            lgl.addWidget(b, i // 4, i % 4)
        cl8.addWidget(lg)
        cl8.addStretch()
        sa8.setWidget(c8)
        l8.addWidget(sa8)
        self.tabs.addTab(t8, "Скрипты")

        # Вкладка 9: Система
        t9 = QWidget()
        l9 = QVBoxLayout(t9)
        sa9 = QScrollArea()
        sa9.setWidgetResizable(True)
        c9 = QWidget()
        cl9 = QVBoxLayout(c9)
        fw_g = QGroupBox("ПРОШИВКА")
        fw_l = QGridLayout(fw_g)
        for i, (n, c) in enumerate([("Обновить", "pm3-flash"), ("Бутром", "pm3-flash-bootrom"), ("Bootloader", "hw bootloader"), ("Версии", "hw version")]):
            fw_l.addWidget(self.mk_btn(n, c, False), i // 2, i % 2)
        cl9.addWidget(fw_g)
        dev_g = QGroupBox("УСТРОЙСТВО")
        dev_l = QGridLayout(dev_g)
        for i, (n, c) in enumerate([("Reset", "hw reset"), ("Status", "hw status"), ("Tune", "hw tune"), ("Teardown", "hw teardown"),
                                    ("Decay", "hw decay"), ("Readmem", "hw readmem"), ("Setmux", "hw setmux"), ("Kick", "hw kick"), ("Break", "hw break")]):
            dev_l.addWidget(self.mk_btn(n, c, False), i // 3, i % 3)
        cl9.addWidget(dev_g)
        pref_g = QGroupBox("НАСТРОЙКИ")
        pref_l = QVBoxLayout(pref_g)
        for p in ["client.debug", "client.timeout", "savepaths", "output", "color"]:
            pl = QHBoxLayout()
            pl.addWidget(QLabel(p))
            cb = QComboBox()
            cb.addItems(["show", "get", "set"])
            pl.addWidget(cb)
            ed = QLineEdit()
            pl.addWidget(ed)
            ok = QPushButton("OK")
            ok.clicked.connect(lambda x, pp=p, cc=cb, ee=ed: self.exec_cmd(f"prefs {cc.currentText()} {pp} {ee.text()}"))
            pl.addWidget(ok)
            pref_l.addLayout(pl)
        cl9.addWidget(pref_g)
        dbg_g = QGroupBox("ОТЛАДКА")
        dbg_l = QVBoxLayout(dbg_g)
        dbg_cb = QCheckBox("Показать отладку")
        dbg_content = QWidget()
        dbg_content.setVisible(False)
        dbg_cb.stateChanged.connect(lambda s: dbg_content.setVisible(s == Qt.Checked))
        dbg_l.addWidget(dbg_cb)
        dbg_inner = QGridLayout(dbg_content)
        dbg_inner.addWidget(self.mk_btn("Debug mode", "data setdebugmode", False), 0, 0)
        dbg_inner.addWidget(self.mk_btn("CLI", "cli", False), 0, 1)
        dbg_l.addWidget(dbg_content)
        cl9.addWidget(dbg_g)
        dang_g = QGroupBox("ОПАСНЫЕ ОПЕРАЦИИ")
        dang_l = QGridLayout(dang_g)
        for i, (n, c, d) in enumerate(DANGEROUS_OPERATIONS):
            b = QPushButton(n)
            b.setStyleSheet("background:#f44336;color:white")
            b.clicked.connect(lambda x, nn=n, cc=c, dd=d: self.confirm_danger(nn, cc, dd))
            dang_l.addWidget(b, i // 3, i % 3)
        cl9.addWidget(dang_g)
        cl9.addStretch()
        sa9.setWidget(c9)
        l9.addWidget(sa9)
        self.tabs.addTab(t9, "Система")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = PM3GUI()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()