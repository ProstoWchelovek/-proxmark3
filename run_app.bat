@echo off
chcp 65001 >nul
title Proxmark3 Easy GUI

echo ========================================
echo   Proxmark3 Easy GUI - Запуск
echo ========================================
echo.

REM Проверка наличия Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] Python не найден! Пожалуйста, установите Python 3.8+
    echo [!] Скачайте с https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [+] Python найден
python --version

REM Проверка и установка зависимостей
echo.
echo [*] Проверка зависимостей...
pip show customtkinter >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Установка customtkinter...
    pip install customtkinter
)

pip show matplotlib >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Установка matplotlib...
    pip install matplotlib
)

pip show pyserial >nul 2>&1
if %errorlevel% neq 0 (
    echo [*] Установка pyserial...
    pip install pyserial
)

echo.
echo [+] Все зависимости установлены
echo.
echo [*] Запуск приложения...
echo.

REM Запуск приложения
python proxmark3_easy_gui.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Ошибка при запуске приложения
    echo [!] Убедитесь, что все зависимости установлены: pip install -r requirements.txt
    pause
)
