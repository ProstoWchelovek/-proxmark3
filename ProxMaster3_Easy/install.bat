@echo off
chcp 65001 >nul
title ProxMaster3 Easy - Установка и запуск

echo ╔═══════════════════════════════════════════════════════════╗
echo ║         ProxMaster3 Easy v2.0 - Установка                 ║
echo ║     Профессиональное GUI для Proxmark3 Easy Iceman        ║
echo ╚═══════════════════════════════════════════════════════════╝
echo.

:: Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python 3.8+ с https://python.org
    pause
    exit /b 1
)

echo ✅ Python найден
python --version
echo.

:: Создание виртуального окружения (опционально)
if not exist "venv" (
    echo 📦 Создание виртуального окружения...
    python -m venv vvenc
    if errorlevel 1 (
        echo ⚠️ Не удалось создать виртуальное окружение, продолжаем без него...
    ) else (
        echo ✅ Виртуальное окружение создано
    )
)

:: Установка зависимостей
echo.
echo 📥 Установка зависимостей...
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Ошибка установки зависимостей!
    pause
    exit /b 1
)

echo ✅ Зависимости установлены
echo.

:: Запуск приложения
echo 🚀 Запуск ProxMaster3 Easy...
echo.
python main.py

if errorlevel 1 (
    echo.
    echo ❌ Ошибка запуска приложения!
    echo Проверьте логи в папке logs/
    pause
)

