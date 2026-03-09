@echo off
title ProspectAI - Subir a GitHub
color 0A

echo ================================================
echo    PROSPECTAI - SUBIR A GITHUB
echo ================================================
echo.

:: Buscar git en las rutas mas comunes
set GIT_EXE=""
if exist "C:\Program Files\Git\bin\git.exe" set GIT_EXE="C:\Program Files\Git\bin\git.exe"
if exist "C:\Program Files (x86)\Git\bin\git.exe" set GIT_EXE="C:\Program Files (x86)\Git\bin\git.exe"
if exist "%LOCALAPPDATA%\Programs\Git\bin\git.exe" set GIT_EXE="%LOCALAPPDATA%\Programs\Git\bin\git.exe"

if %GIT_EXE%=="" (
    echo [ERROR] Git no encontrado. Instala Git desde https://git-scm.com
    pause
    exit
)

echo [OK] Git encontrado: %GIT_EXE%
echo.

:: Inicializar repo
echo [1/4] Inicializando repositorio Git...
%GIT_EXE% init
%GIT_EXE% add .
%GIT_EXE% commit -m "feat: ProspectAI v1.0 - Backend Flask + Playwright + CRM"

echo.
echo [2/4] Ahora necesitas el link de tu repo GitHub.
echo.
echo INSTRUCCIONES:
echo  1. Abre https://github.com/new en tu navegador
echo  2. Nombre del repo: prospectai
echo  3. Dejalo en Publico
echo  4. NO tildres "Add README"
echo  5. Click en "Create repository"
echo  6. Copia la URL que te da (ej: https://github.com/TuUsuario/prospectai.git)
echo.

set /p GITHUB_URL="Pega aqui la URL de GitHub y presiona ENTER: "

echo.
echo [3/4] Conectando con GitHub...
%GIT_EXE% remote add origin %GITHUB_URL%
%GIT_EXE% branch -M main
%GIT_EXE% push -u origin main

echo.
echo ================================================
echo   CODIGO SUBIDO A GITHUB EXITOSAMENTE!
echo ================================================
echo.
echo Ahora sigue estos pasos:
echo.
echo 1. Ve a https://railway.app
echo    - New Project - Deploy from GitHub - prospectai
echo    - Add Plugin: PostgreSQL
echo    - Fijate que usa la carpeta "backend" como root
echo.
echo 2. Ve a https://vercel.com  
echo    - New Project - Import from GitHub - prospectai
echo    - Root directory: frontend
echo    - Deploy!
echo.
echo 3. Copia la URL de Railway y pegala en:
echo    frontend/index.html (busca TU-BACKEND.railway.app)
echo.
pause
