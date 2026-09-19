@echo off
chcp 65001 >nul
title ProxMaster3 Easy - Installer

echo ============================================================
echo   ProxMaster3 Easy - Установка и запуск
echo   Профессиональный инструмент для Proxmark3 Easy
echo ============================================================
echo.

:: Проверка Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python не найден!
    echo Установите Python 3.7+ с https://www.python.org/
    pause
    exit /b 1
)

echo [OK] Python найден
echo.

:: Установка зависимостей
echo [INFO] Установка зависимостей...
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [WARNING] Некоторые зависимости не установились. Пробуем по отдельности...
    pip install PyQt6 --quiet
    pip install pyserial --quiet
    pip install requests --quiet
    pip install numpy --quiet
    pip install Pillow --quiet
)

echo [OK] Зависимости установлены
echo.

:: Проверка Git для ProxSpace
git --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Git не найден!
    echo Для установки ProxSpace необходим Git.
    echo Установите Git с https://git-scm.com/
    echo.
    set /p INSTALL_GIT="Хотите продолжить без установки ProxSpace? (Y/N): "
    if /i "%INSTALL_GIT%"=="N" exit /b 1
) else (
    echo [OK] Git найден
)

echo.
echo ============================================================
echo   Меню установки
echo ============================================================
echo.
echo 1. Установить ProxSpace и Iceman прошивку
echo 2. Обновить ProxSpace
echo 3. Собрать прошивку Iceman
echo 4. Прошить устройство Proxmark3
echo 5. Проверить установку
echo 6. Запустить приложение
echo 0. Выход
echo.

set /p CHOICE="Ваш выбор: "

if "%CHOICE%"=="1" goto INSTALL_PROXSPACE
if "%CHOICE%"=="2" goto UPDATE_PROXSPACE
if "%CHOICE%"=="3" goto BUILD_FIRMWARE
if "%CHOICE%"=="4" goto FLASH_DEVICE
if "%CHOICE%"=="5" goto VERIFY_INSTALL
if "%CHOICE%"=="6" goto RUN_APP
if "%CHOICE%"=="0" goto END

echo Неверный выбор!
pause
goto MENU

:INSTALL_PROXSPACE
echo.
echo [INFO] Начало установки ProxSpace...
python installer\proxspace_installer.py
pause
goto MENU

:UPDATE_PROXSPACE
echo.
echo [INFO] Обновление ProxSpace...
python -c "from installer.proxspace_installer import ProxSpaceInstaller; i = ProxSpaceInstaller(); i.update_proxspace()"
pause
goto MENU

:BUILD_FIRMWARE
echo.
echo [INFO] Сборка прошивки Iceman...
python -c "from installer.proxspace_installer import ProxSpaceInstaller; i = ProxSpaceInstaller(); i.build_iceman_firmware()"
pause
goto MENU

:FLASH_DEVICE
echo.
set /p PORT="Введите COM-порт устройства (или Enter для автопоиска): "
if "%PORT%"=="" (
    python -c "from installer.proxspace_installer import ProxSpaceInstaller; i = ProxSpaceInstaller(); i.flash_firmware()"
) else (
    python -c "from installer.proxspace_installer import ProxSpaceInstaller; i = ProxSpaceInstaller(); i.flash_firmware('%PORT%')"
)
pause
goto MENU

:VERIFY_INSTALL
echo.
echo [INFO] Проверка установки...
python -c "from installer.proxspace_installer import ProxSpaceInstaller; i = ProxSpaceInstaller(); i.verify_installation()"
pause
goto MENU

:RUN_APP
echo.
echo [INFO] Запуск ProxMaster3 Easy...
python proxmaster_main.py
if %errorlevel% neq 0 (
    echo [ERROR] Ошибка запуска приложения!
    echo Убедитесь, что все зависимости установлены.
    pause
)
goto MENU

:END
echo.
echo Спасибо за использование ProxMaster3 Easy!
pause
exit /b 0
