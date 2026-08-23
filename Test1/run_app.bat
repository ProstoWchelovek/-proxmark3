@echo off
chcp 65001 >nul
title Proxmark3 Easy GUI

echo ========================================
echo   Proxmark3 Easy GUI - Запуск
echo ========================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    pause
    exit /b 1
)

echo [+] Python найден
python --version

echo.
echo [*] Проверка зависимостей...
pip show customtkinter >nul 2>&1
if %errorlevel% neq 0 (
    pip install customtkinter
)

pip show matplotlib >nul 2>&1
if %errorlevel% neq 0 (
    pip install matplotlib
)

pip show pyserial >nul 2>&1
if %errorlevel% neq 0 (
    pip install pyserial
)

echo.
echo [+] Все зависимости установлены
echo.
echo [*] Запуск приложения...
echo.

python proxmark3_easy_gui.py

if %errorlevel% neq 0 (
    echo.
    pause
)
