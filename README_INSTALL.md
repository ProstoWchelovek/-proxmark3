# Proxmark3 Iceman - Автоматическая установка "из коробки"

Этот скрипт автоматически устанавливает все необходимые компоненты для работы с Proxmark3 Iceman, включая:
- Все системные зависимости
- Клиент Proxmark3 из официального репозитория
- Компиляцию прошивки и клиента
- Прошивку устройства (при подключении)
- Графический интерфейс (GUI)
- Создание ярлыков для запуска

## Требования

- **ОС**: Linux (Ubuntu/Debian, Fedora/RHEL, Arch), macOS или Windows
- **Права**: Рекомендуется запуск от root/sudo для установки системных пакетов
- **Интернет**: Для клонирования репозитория и установки зависимостей
- **Устройство Proxmark3**: Опционально (для прошивки)

## Быстрый старт

### Linux/macOS

```bash
# Сделать скрипт исполняемым (если нужно)
chmod +x install_proxmark3.sh

# Запустить установку
./install_proxmark3.sh
```

### Windows

```powershell
# Требуется Git Bash или WSL
.\install_proxmark3.sh
```

## Что делает скрипт

1. **Определяет операционную систему** и выбирает подходящий менеджер пакетов
2. **Устанавливает зависимости**:
   - Python 3 с pip
   - Tkinter для GUI
   - PySerial для связи с устройством
   - Компиляторы (GCC, ARM GCC)
   - Библиотеки (libusb, readline, ncurses, hidapi, Qt)
   - dfu-util для прошивки

3. **Клонирует репозиторий** [Proxmark3 Iceman](https://github.com/RfidResearchGroup/proxmark3) в `~/proxmark3`

4. **Компилирует** клиент и прошивку

5. **Прошивает устройство** (если подключено)

6. **Копирует файлы GUI** в `~/proxmark3/client/gui_proxmark3`

7. **Создаёт ярлык** для запуска приложения

8. **Запускает GUI** (по желанию пользователя)

## Расположение файлов после установки

- **Proxmark3**: `~/proxmark3`
- **GUI**: `~/proxmark3/client/gui_proxmark3`
- **Ярлык запуска**: `~/proxmark3/client/gui_proxmark3/run_gui.sh`
- **Desktop файл** (Linux): `~/.local/share/applications/proxmark3-gui.desktop`

## Ручной запуск GUI

```bash
cd ~/proxmark3/client/gui_proxmark3
python3 proxmark3_gui.py
```

Или используйте созданный ярлык:

```bash
~/proxmark3/client/gui_proxmark3/run_gui.sh
```

## Прошивка устройства

Если устройство не было прошито во время установки (не было подключено), выполните:

```bash
cd ~/proxmark3
make flash
```

## Правила udev (Linux)

Для доступа к устройству без root создайте файл `/etc/udev/rules.d/99-proxmark3.rules`:

```bash
# Proxmark3 Rules
SUBSYSTEM=="usb", ATTR{idVendor}=="9ac4", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="2a70", MODE="0666"
SUBSYSTEM=="usb", ATTR{idVendor}=="1fc9", MODE="0666"
```

Затем обновите правила:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Устранение неполадок

### Ошибка компиляции
- Убедитесь, что установлены все зависимости
- Проверьте наличие свободного места на диске (>2GB)
- Попробуйте выполнить `make clean` перед повторной компиляцией

### Устройство не обнаружено
- Проверьте подключение USB
- Установите правила udev (см. выше)
- Попробуйте другой USB-кабель

### Tkinter не работает
- Linux: `sudo apt-get install python3-tk`
- macOS: `brew install python-tk`
- Windows: Переустановите Python с опцией tcl/tk

## Дополнительная информация

- [Официальная документация Proxmark3](https://github.com/RfidResearchGroup/proxmark3)
- [Wiki Iceman](https://github.com/RfidResearchGroup/proxmark3/wiki)

## Лицензия

Скрипт распространяется под той же лицензией, что и Proxmark3 Iceman.
