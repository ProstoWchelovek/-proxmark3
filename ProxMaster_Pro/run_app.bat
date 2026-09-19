@echo off
REM ProxMaster Pro - Запуск приложения
REM © 2024 ProxMaster Pro Team

echo ========================================
echo   ProxMaster Pro v3.0
echo   Профессиональный инструмент для Proxmark3
echo ========================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo Установите Python 3.8+ с https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python найден
echo.

REM Проверка зависимостей
echo Проверка зависимостей...
pip show pyserial >nul 2>&1
if errorlevel 1 (
    echo [Установка] pyserial...
    pip install pyserial
)

pip show matplotlib >nul 2>&1
if errorlevel 1 (
    echo [Установка] matplotlib...
    pip install matplotlib
)

pip show numpy >nul 2>&1
if errorlevel 1 (
    echo [Установка] numpy...
    pip install numpy
)

echo [OK] Все зависимости установлены
echo.

REM Запуск приложения
echo Запуск ProxMaster Pro...
echo.
python "%~dp0main_app.py" %*

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Приложение завершилось с ошибкой!
    echo Проверьте логи выше для деталей.
    pause
)
