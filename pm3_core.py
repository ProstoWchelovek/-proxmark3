"""
Proxmark3 Easy GUI - Модуль ядра для связи с устройством
Обработка команд, парсинг вывода, управление процессом pm3.exe
"""

import subprocess
import threading
import queue
import re
import os
from pathlib import Path

class Proxmark3Core:
    def __init__(self, proxspace_path="C:\\Proxmark3", log_callback=None):
        self.proxspace_path = Path(proxspace_path)
        self.pm3_exe = self.proxspace_path / "ProxSpace" / "pm3" / "proxmark3" / "client" / "pm3.exe"
        self.process = None
        self.is_connected = False
        self.log_callback = log_callback
        self.output_queue = queue.Queue()
        self.device_info = {"fw": "Unknown", "boot": "Unknown", "hw": "Unknown"}
        
    def log(self, message):
        """Отправка сообщения в лог GUI"""
        if self.log_callback:
            self.log_callback(message)

    def check_connection(self):
        """Проверка наличия exe файла"""
        return self.pm3_exe.exists()

    def start_client(self):
        """Запуск клиента Proxmark3 в интерактивном режиме"""
        if not self.check_connection():
            self.log("[-] Ошибка: pm3.exe не найден. Проверьте установку ProxSpace.")
            return False
        
        try:
            # Запускаем процесс с перенаправлением stdin/stdout/stderr
            self.process = subprocess.Popen(
                [str(self.pm3_exe), "-c", "exit"], # Временно просто проверяем запуск
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                cwd=str(self.pm3_exe.parent)
            )
            self.is_connected = True
            self.log("[+] Клиент запущен успешно")
            
            # Запуск потока чтения вывода
            threading.Thread(target=self._read_output, daemon=True).start()
            return True
        except Exception as e:
            self.log(f"[-] Ошибка запуска клиента: {e}")
            return False

    def _read_output(self):
        """Чтение вывода процесса в фоновом потоке"""
        if self.process:
            for line in self.process.stdout:
                self.output_queue.put(line)
                self.log(line.strip())
            
    def send_command(self, command):
        """Отправка команды устройству"""
        if not self.is_connected or not self.process:
            # Эмуляция ответа если нет реального устройства (для демонстрации)
            self.log(f"[usb] pm3 --> {command}")
            self._simulate_response(command)
            return
        
        try:
            self.log(f"[usb] pm3 --> {command}")
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
        except Exception as e:
            self.log(f"[-] Ошибка отправки команды: {e}")

    def _simulate_response(self, cmd):
        """Симуляция ответа устройства для демонстрации UI (если нет реального девайса)"""
        responses = {
            "search": "[=] lf search\n[=] Note: False Positives ARE possible\n[=] Checking for known tags...\n[+] Found tag: EM410x ID 1234567890",
            "hf search": "[=] hf search\n[!] No known/supported 13.56 MHz tags found",
            "hw status": "Firmware: 4.12345\nBootrom: 4.12345\nHardware: RDV4.1",
            "plot": "[i] Generating plot...",
            "trace list": "[=] Listing trace packets..."
        }
        
        # Простой поиск подстроки
        for key, resp in responses.items():
            if key in cmd.lower():
                for line in resp.split("\n"):
                    self.log(line)
                return
        
        self.log("[=] Command executed (simulated).")

    def get_device_info(self):
        """Получение информации об устройстве"""
        if self.is_connected:
            self.send_command("hw status")
            # Парсинг должен происходить асинхронно через лог
        else:
            self.device_info = {"fw": "Disconnected", "boot": "-", "hw": "-"}
        return self.device_info

    def stop(self):
        """Остановка процесса"""
        if self.process:
            self.process.terminate()
            self.is_connected = False
            self.log("[i] Клиент остановлен")

# Функции парсинга вывода
def parse_log_line(line):
    """Анализ строки лога для определения типа сообщения"""
    line = line.strip()
    if line.startswith("[+]"):
        return "success", line
    elif line.startswith("[-]"):
        return "error", line
    elif line.startswith("[!]"):
        return "warning", line
    elif line.startswith("[=]") or line.startswith("[?]"):
        return "info", line
    elif line.startswith("[#]"):
        return "debug", line
    elif line.startswith("[|]") or line.startswith("[/]") or line.startswith("[\\]") or line.startswith("[-]"):
        return "progress", line
    else:
        return "normal", line

def extract_progress(line):
    """Извлечение прогресса из строки вида [12345/500000]"""
    match = re.search(r'\[(\d+)/(\d+)\]', line)
    if match:
        current = int(match.group(1))
        total = int(match.group(2))
        return current, total
    return None, None
