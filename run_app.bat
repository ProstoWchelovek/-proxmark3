@echo off
chcp 65001 >nul
echo ========================================
echo   Proxmark3 Easy GUI - Запуск
echo ========================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Ошибка: Python не найден!
    echo Пожалуйста, установите Python 3.10+ с https://www.python.org/
    pause
    exit /b 1
)

echo [+] Python найден.
echo.

REM Проверка и установка зависимостей
echo [=] Проверка зависимостей...
pip install -r requirements.txt >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Не удалось установить зависимости автоматически.
    echo Попробуйте выполнить вручную: pip install -r requirements.txt
    pause
)

echo [=] Запуск приложения...
echo.

REM Запуск приложения
python proxmark3_easy_gui.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Приложение завершилось с ошибкой.
    pause
)
