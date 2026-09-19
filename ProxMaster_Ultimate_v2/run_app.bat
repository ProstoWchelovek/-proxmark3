@echo off
chcp 65001 >nul
echo ============================================================
echo ProxMaster Ultimate v2.0.0 - Установка и запуск
echo ============================================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python не найден!
    echo Установите Python 3.8+ с https://www.python.org/downloads/
    echo Не забудьте отметить "Add Python to PATH" при установке
    pause
    exit /b 1
)

echo [+] Python найден
python --version
echo.

REM Создание виртуального окружения (опционально)
if not exist "venv" (
    echo [INFO] Создание виртуального окружения...
    python -m venv venv
)

REM Активация виртуального окружения
echo [INFO] Активация виртуального окружения...
call venv\Scripts\activate.bat

REM Установка зависимостей
echo [INFO] Установка зависимостей...
pip install -r requirements.txt --quiet

echo.
echo ============================================================
echo Запуск ProxMaster Ultimate...
echo ============================================================
echo.

REM Запуск приложения
python proxmaster_ultimate.py

pause
