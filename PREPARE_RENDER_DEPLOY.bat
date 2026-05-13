@echo off
setlocal EnableDelayedExpansion
title JYOTISH 3.0 - Prepare Render Deploy

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
set "BACKEND=%ROOT%\backend"
set "SEED_DB=%BACKEND%\astro_seed.db"

echo.
echo  ================================================
echo   JYOTISH 3.0 - Prepare GitHub + Render Deploy
echo  ================================================
echo.

where git >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Git is not installed or not in PATH.
  echo         Install Git from https://git-scm.com/download/win
  pause
  exit /b 1
)

cd /d "%ROOT%"

if not exist ".git" (
  git init
  git branch -M main
)

git config --global user.email "devanand2008@gmail.com"
git config --global user.name "Devanand"
git config --global init.defaultBranch main

echo [1/5] Preparing database seed for first Render deploy...
if exist "%BACKEND%\astro.db" (
  copy /Y "%BACKEND%\astro.db" "%SEED_DB%" >nul
  echo       Copied backend\astro.db to backend\astro_seed.db
) else (
  echo       No backend\astro.db found. Render will create a fresh database.
)

echo.
echo [2/5] Staging source files...
git add .
if exist "%SEED_DB%" git add -f "%SEED_DB%"

echo.
echo [3/5] Files staged:
git status --short

echo.
set /p COMMIT_MSG="Commit message [Deploy Jyotish app to Render]: "
if "%COMMIT_MSG%"=="" set "COMMIT_MSG=Deploy Jyotish app to Render"

git diff --cached --quiet
if errorlevel 1 (
  echo.
  echo [4/5] Creating commit...
  git commit -m "%COMMIT_MSG%"
) else (
  echo.
  echo [4/5] Nothing new to commit.
)

echo.
echo [5/5] GitHub remote setup
git remote -v
echo.
set /p REPO_URL="Paste GitHub repo URL, or press Enter to keep current origin: "
if not "%REPO_URL%"=="" (
  git remote remove origin 2>nul
  git remote add origin "%REPO_URL%.git" 2>nul || git remote add origin "%REPO_URL%"
)

echo.
echo Pushing main branch to GitHub...
git push -u origin main
if errorlevel 1 (
  echo.
  echo [ERROR] Push failed. Check GitHub login, repo URL, or branch permissions.
  pause
  exit /b 1
)

echo.
echo  ================================================
echo   READY FOR RENDER
echo  ================================================
echo.
echo  Open Render: https://dashboard.render.com/
echo  Use New + ^> Blueprint and select this GitHub repo.
echo  Then follow RENDER_FORM_VALUES.txt exactly.
echo.
start "" "https://dashboard.render.com/"
pause
