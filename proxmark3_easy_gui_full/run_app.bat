@echo off
REM ============================================================================
REM Proxmark3 Easy GUI - Скрипт запуска для Windows
REM ============================================================================
REM Этот скрипт:
REM 1. Проверяет наличие Python
REM 2. Устанавливает зависимости
REM 3. Запускает приложение
REM ============================================================================

setlocal enabledelayedexpansion

echo ============================================================
echo   Proxmark3 Easy GUI - Запуск приложения
echo ============================================================
echo.

REM Проверка Python
echo [1/3] Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Python не найден!
    echo.
    echo Пожалуйста, установите Python 3.8 или выше:
    echo https://www.python.org/downloads/
    echo.
    echo Не забудьте отметить "Add Python to PATH" при установке!
    echo.
    pause
    exit /b 1
)

REM Получение версии Python
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [+] Найден Python %PYTHON_VERSION%
echo.

REM Переход в директорию со скриптом
cd /d "%~dp0"

REM Установка зависимостей
echo [2/3] Установка зависимостей...
if exist requirements.txt (
    pip install -r requirements.txt --quiet
    if errorlevel 1 (
        echo.
        echo [ПРЕДУПРЕЖДЕНИЕ] Некоторые пакеты не удалось установить автоматически
        echo Попробуйте выполнить вручную: pip install -r requirements.txt
        echo.
    ) else (
        echo [+] Зависимости установлены
    )
) else (
    echo [!] Файл requirements.txt не найден, пропускаем установку зависимостей
)
echo.

REM Запуск приложения
echo [3/3] Запуск Proxmark3 Easy GUI...
echo.
python proxmark3_easy_gui.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Приложение завершилось с ошибкой
    echo.
    echo Возможные причины:
    echo - Отсутствуют необходимые библиотеки
    echo - Ошибка в коде приложения
    echo - Несовместимость версий Python
    echo.
    echo Для диагностики запустите: python proxmark3_easy_gui.py
    echo.
    pause
)

endlocal
