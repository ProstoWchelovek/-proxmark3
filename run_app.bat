@echo off
chcp 65001 >nul
title Proxmark3 Easy GUI - Установка и запуск

echo ============================================
echo   Proxmark3 Easy GUI - Установка и запуск
echo ============================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python не найден. Пожалуйста, установите Python 3.10+ с https://python.org
    echo     Убедитесь, что добавили Python в PATH при установке.
    pause
    exit /b 1
)

echo [+] Python найден
python --version

REM Установка зависимостей
echo.
echo [=] Установка зависимостей...
pip install customtkinter packaging

REM Запуск приложения
echo.
echo [+] Запуск Proxmark3 Easy GUI...
python main.py

pause
