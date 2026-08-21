#!/bin/bash
# ============================================================================
# Proxmark3 Iceman - Автоматическая установка "из коробки"
# Скрипт устанавливает все компоненты, прошивает устройство и запускает GUI
# ============================================================================

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # Без цвета

# Логотип
echo -e "${BLUE}"
echo "=============================================="
echo "   Proxmark3 Iceman - Автоматическая установка"
echo "   Версия 1.0"
echo "=============================================="
echo -e "${NC}"

# Определение ОС
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    OS="windows"
else
    echo -e "${RED}Неподдерживаемая операционная система${NC}"
    exit 1
fi

echo -e "${GREEN}[✓] Определена ОС:${NC} $OS"

# ============================================================================
# ФУНКЦИИ
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]] && [[ $OS == "linux" ]]; then
        log_warning "Рекомендуется запуск от root для установки системных пакетов"
    fi
}

install_linux_deps() {
    log_info "Установка зависимостей для Linux..."
    
    # Обновление пакетов
    if command -v apt-get &> /dev/null; then
        apt-get update -qq
        apt-get install -y -qq \
            python3 \
            python3-pip \
            python3-tk \
            python3-serial \
            git \
            build-essential \
            libreadline-dev \
            libncurses5-dev \
            libusb-1.0-0-dev \
            pkg-config \
            libbluetooth-dev \
            gcc-arm-none-eabi \
            binutils-arm-none-eabi \
            dfu-util \
            libhidapi-libusb0 \
            qtbase5-dev \
            qtmultimedia5-dev
        log_success "Зависимости установлены через apt-get"
    elif command -v dnf &> /dev/null; then
        dnf install -y \
            python3 \
            python3-pip \
            python3-tkinter \
            python3-pyserial \
            git \
            gcc \
            gcc-c++ \
            readline-devel \
            ncurses-devel \
            libusb1-devel \
            pkg-config \
            bluez-libs-devel \
            arm-none-eabi-gcc-cs \
            arm-none-eabi-binutils-cs \
            dfu-util \
            hidapi-devel \
            qt5-qtbase-devel \
            qt5-qtmultimedia-devel
        log_success "Зависимости установлены через dnf"
    elif command -v yum &> /dev/null; then
        yum install -y \
            python3 \
            python3-pip \
            tkinter \
            python3-pyserial \
            git \
            gcc \
            gcc-c++ \
            readline-devel \
            ncurses-devel \
            libusb1-devel \
            pkg-config \
            bluez-libs-devel \
            arm-none-eabi-gcc-cs \
            arm-none-eabi-binutils-cs \
            dfu-util \
            hidapi-devel
        log_success "Зависимости установлены через yum"
    elif command -v pacman &> /dev/null; then
        pacman -S --noconfirm \
            python \
            python-pip \
            tk \
            python-pyserial \
            git \
            base-devel \
            readline \
            ncurses \
            libusb \
            pkg-config \
            bluez-libs \
            arm-none-eabi-gcc \
            arm-none-eabi-binutils \
            dfu-util \
            hidapi \
            qt5-base \
            qt5-multimedia
        log_success "Зависимости установлены через pacman"
    else
        log_error "Менеджер пакетов не найден. Установите зависимости вручную."
        return 1
    fi
}

install_macos_deps() {
    log_info "Установка зависимостей для macOS..."
    
    # Проверка Homebrew
    if ! command -v brew &> /dev/null; then
        log_warning "Homebrew не найден. Установка..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    brew install \
        python3 \
        git \
        readline \
        ncurses \
        libusb \
        pkg-config \
        bluez \
        arm-none-eabi-gcc \
        arm-none-eabi-binutils \
        dfu-util \
        hidapi \
        qt \
        pyserial
    
    # Установка tkinter через Python
    pip3 install tk
    
    log_success "Зависимости установлены через Homebrew"
}

install_windows_deps() {
    log_info "Установка зависимостей для Windows..."
    
    # Проверка Chocolatey
    if ! command -v choco &> /dev/null; then
        log_warning "Chocolatey не найден. Рекомендуется установить вручную."
        log_info "Инструкция: https://chocolatey.org/install"
    else
        choco install -y \
            python3 \
            git \
            mingw \
            libusb-win32 \
            hidapi
            
        pip3 install pyserial
    fi
    
    log_success "Зависимости установлены (требуется проверка вручную)"
}

install_python_deps() {
    log_info "Установка Python зависимостей..."
    
    # Проверка pip
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
    else
        log_error "pip не найден. Установите Python и pip."
        return 1
    fi
    
    # Установка зависимостей
    $PIP_CMD install --upgrade pip
    $PIP_CMD install pyserial
    
    # Проверка tkinter
    python3 -c "import tkinter" 2>/dev/null || {
        log_warning "Tkinter не найден. Установите пакет python3-tk или python-tkinter"
    }
    
    log_success "Python зависимости установлены"
}

clone_proxmark3() {
    log_info "Клонирование репозитория Proxmark3 Iceman..."
    
    PM3_DIR="$HOME/proxmark3"
    
    if [ -d "$PM3_DIR" ]; then
        log_warning "Директория proxmark3 уже существует"
        read -p "Хотите обновить? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            cd "$PM3_DIR"
            git pull
            log_success "Репозиторий обновлён"
        else
            log_info "Используется существующая версия"
        fi
    else
        git clone --recursive https://github.com/RfidResearchGroup/proxmark3.git "$PM3_DIR"
        log_success "Репозиторий склонирован в $PM3_DIR"
    fi
}

compile_proxmark3() {
    log_info "Компиляция Proxmark3 Iceman..."
    
    PM3_DIR="$HOME/proxmark3"
    
    if [ ! -d "$PM3_DIR" ]; then
        log_error "Директория proxmark3 не найдена. Сначала выполните клонирование."
        return 1
    fi
    
    cd "$PM3_DIR"
    
    # Компиляция клиента и прошивки
    make clean
    make -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
    
    if [ $? -eq 0 ]; then
        log_success "Proxmark3 успешно скомпилирован"
    else
        log_error "Ошибка компиляции. Проверьте логи выше."
        return 1
    fi
}

flash_device() {
    log_info "Прошивка устройства Proxmark3..."
    
    PM3_DIR="$HOME/proxmark3"
    
    if [ ! -d "$PM3_DIR" ]; then
        log_error "Директория proxmark3 не найдена."
        return 1
    fi
    
    cd "$PM3_DIR"
    
    # Проверка подключения устройства
    if command -v lsusb &> /dev/null; then
        if lsusb | grep -i "proxmark\|arduino" > /dev/null; then
            log_success "Устройство Proxmark3 обнаружено"
        else
            log_warning "Устройство Proxmark3 не обнаружено. Подключите устройство."
            read -p "Продолжить без прошивки? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                return 1
            fi
            log_info "Пропуск прошивки"
            return 0
        fi
    fi
    
    # Прошивка через make flash
    log_info "Начало прошивки..."
    make flash
    
    if [ $? -eq 0 ]; then
        log_success "Устройство прошито успешно"
    else
        log_warning "Прошивка не выполнена. Возможно, устройство не подключено."
        log_info "Вы можете прошить устройство позже командой: cd $PM3_DIR && make flash"
    fi
}

copy_gui_files() {
    log_info "Копирование файлов GUI..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PM3_DIR="$HOME/proxmark3"
    GUI_DIR="$PM3_DIR/client/gui_proxmark3"
    
    # Создание директории для GUI
    mkdir -p "$GUI_DIR"
    
    # Копирование файлов
    if [ -f "$SCRIPT_DIR/proxmark3_gui.py" ]; then
        cp "$SCRIPT_DIR/proxmark3_gui.py" "$GUI_DIR/"
        log_success "Файл proxmark3_gui.py скопирован"
    fi
    
    if [ -f "$SCRIPT_DIR/commands_full.json" ]; then
        cp "$SCRIPT_DIR/commands_full.json" "$GUI_DIR/"
        log_success "Файл commands_full.json скопирован"
    fi
    
    if [ -f "$SCRIPT_DIR/Описание основной структуры.txt" ]; then
        cp "$SCRIPT_DIR/Описание основной структуры.txt" "$GUI_DIR/"
        log_success "Файл описания скопирован"
    fi
    
    log_success "Файлы GUI скопированы в $GUI_DIR"
}

create_launcher() {
    log_info "Создание ярлыка запуска..."
    
    PM3_DIR="$HOME/proxmark3"
    GUI_DIR="$PM3_DIR/client/gui_proxmark3"
    LAUNCHER="$GUI_DIR/run_gui.sh"
    
    # Создание скрипта запуска
    cat > "$LAUNCHER" << 'EOF'
#!/bin/bash
# Запуск Proxmark3 GUI

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "Ошибка: Python3 не найден"
    exit 1
fi

# Запуск GUI
python3 proxmark3_gui.py
EOF
    
    chmod +x "$LAUNCHER"
    log_success "Ярлык запуска создан: $LAUNCHER"
    
    # Создание .desktop файла для Linux
    if [[ $OS == "linux" ]]; then
        DESKTOP_FILE="$HOME/.local/share/applications/proxmark3-gui.desktop"
        mkdir -p "$(dirname "$DESKTOP_FILE")"
        
        cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Proxmark3 GUI
Comment=Графический интерфейс для Proxmark3 Iceman
Exec=$LAUNCHER
Icon=accessories-text-editor
Terminal=false
Categories=Utility;Electronics;
Keywords=rfid;nfc;proxmark;
EOF
        
        log_success "Desktop файл создан: $DESKTOP_FILE"
    fi
}

launch_gui() {
    log_info "Запуск Proxmark3 GUI..."
    
    PM3_DIR="$HOME/proxmark3"
    GUI_DIR="$PM3_DIR/client/gui_proxmark3"
    
    if [ ! -f "$GUI_DIR/proxmark3_gui.py" ]; then
        log_error "Файл proxmark3_gui.py не найден"
        return 1
    fi
    
    cd "$GUI_DIR"
    
    # Добавление пути к клиенту proxmark3
    export PATH="$PM3_DIR/client:$PATH"
    
    # Запуск GUI
    python3 proxmark3_gui.py &
    
    log_success "GUI запущен!"
}

show_completion() {
    echo ""
    echo -e "${GREEN}"
    echo "=============================================="
    echo "   Установка завершена успешно!"
    echo "=============================================="
    echo -e "${NC}"
    echo ""
    echo "Что было сделано:"
    echo "  ✓ Установлены все зависимости"
    echo "  ✓ Склонирован репозиторий Proxmark3 Iceman"
    echo "  ✓ Скомпилирован клиент и прошивка"
    echo "  ✓ Файлы GUI скопированы"
    echo "  ✓ Создан ярлык запуска"
    echo ""
    echo "Расположение:"
    echo "  Прокмарк3: $HOME/proxmark3"
    echo "  GUI: $HOME/proxmark3/client/gui_proxmark3"
    echo ""
    echo "Для запуска GUI используйте:"
    echo "  $HOME/proxmark3/client/gui_proxmark3/run_gui.sh"
    echo ""
    echo "Или создайте ярлык на рабочем столе."
    echo ""
    echo -e "${YELLOW}Важно:${NC}"
    echo "  - Подключите устройство Proxmark3 перед использованием"
    echo "  - Для прошивки устройства: cd ~/proxmark3 && make flash"
    echo "  - Правила udev могут потребоваться для доступа к устройству"
    echo ""
}

# ============================================================================
# ОСНОВНОЙ СЦЕНАРИЙ
# ============================================================================

main() {
    check_root
    
    echo ""
    log_info "Начало установки..."
    echo ""
    
    # Шаг 1: Установка зависимостей ОС
    case $OS in
        linux)
            install_linux_deps
            ;;
        macos)
            install_macos_deps
            ;;
        windows)
            install_windows_deps
            ;;
    esac
    
    # Шаг 2: Установка Python зависимостей
    install_python_deps
    
    # Шаг 3: Клонирование репозитория
    clone_proxmark3
    
    # Шаг 4: Компиляция
    compile_proxmark3
    
    # Шаг 5: Прошивка устройства (опционально)
    flash_device
    
    # Шаг 6: Копирование файлов GUI
    copy_gui_files
    
    # Шаг 7: Создание ярлыка
    create_launcher
    
    # Шаг 8: Показ результатов
    show_completion
    
    # Шаг 9: Запуск GUI (по желанию)
    read -p "Запустить GUI сейчас? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        launch_gui
    fi
}

# Запуск
main "$@"
