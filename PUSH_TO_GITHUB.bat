@echo off
title JYOTISH 3.0 - GitHub Setup Script
color 0B
echo.
echo  ================================================
echo   JYOTISH 3.0 - GitHub Push Setup
echo  ================================================
echo.

:: ── STEP 1: Check if Git is installed ──────────────
where git >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo [OK] Git is already installed.
    git --version
    goto :setup_repo
)

echo [!] Git is not installed. Downloading now...
echo.

:: Download Git installer
set GIT_URL=https://github.com/git-for-windows/git/releases/download/v2.45.2.windows.1/Git-2.45.2-64-bit.exe
set GIT_INSTALLER=%TEMP%\GitInstaller.exe

echo Downloading Git for Windows (this may take a minute)...
powershell -Command "Invoke-WebRequest -Uri '%GIT_URL%' -OutFile '%GIT_INSTALLER%' -UseBasicParsing"

if not exist "%GIT_INSTALLER%" (
    echo [ERROR] Download failed. Please install Git manually from:
    echo         https://git-scm.com/download/win
    pause
    exit /b 1
)

echo Installing Git silently...
"%GIT_INSTALLER%" /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS /COMPONENTS="icons,ext\reg\shellhere,assoc,assoc_sh"

:: Refresh PATH
set "PATH=%PATH%;C:\Program Files\Git\bin;C:\Program Files\Git\cmd"

echo [OK] Git installed successfully!
echo.

:setup_repo
:: ── STEP 2: Configure Git identity ─────────────────
echo  Configuring Git identity...
git config --global user.email "devanand2008@gmail.com"
git config --global user.name "Devanand"
git config --global init.defaultBranch main
echo [OK] Git identity configured.
echo.

:: ── STEP 3: Initialize repo ─────────────────────────
cd /d "e:\astro app 3.0 web"

if exist ".git" (
    echo [OK] Git repo already initialized.
) else (
    git init
    echo [OK] Git repository initialized.
)
echo.

:: ── STEP 4: Stage all files ─────────────────────────
echo  Staging files...
git add .
echo [OK] Files staged.
echo.

:: ── STEP 5: Show what will be committed ─────────────
echo  Files ready to commit:
echo  ──────────────────────────────────────────────
git status --short
echo  ──────────────────────────────────────────────
echo.

:: ── STEP 6: Ask for repo URL ─────────────────────────
echo  ┌─────────────────────────────────────────────────────┐
echo  │  ACTION REQUIRED                                    │
echo  │                                                     │
echo  │  1. Sign in to GitHub:  https://github.com/login   │
echo  │     Email: devanand2008@gmail.com                   │
echo  │                                                     │
echo  │  2. Create a NEW repository:  https://github.com/new│
echo  │     - Name: jyotish-app                             │
echo  │     - Visibility: Public                            │
echo  │     - Do NOT add README or .gitignore               │
echo  │     - Click "Create repository"                     │
echo  │                                                     │
echo  │  3. Copy the repo URL (looks like):                 │
echo  │     https://github.com/YOUR-USERNAME/jyotish-app   │
echo  └─────────────────────────────────────────────────────┘
echo.
set /p REPO_URL="  Paste your GitHub repo URL here and press Enter: "
echo.

if "%REPO_URL%"=="" (
    echo [ERROR] No URL provided. Exiting.
    pause
    exit /b 1
)

:: ── STEP 7: Connect and push ────────────────────────
git remote remove origin 2>nul
git remote add origin "%REPO_URL%.git" 2>nul || git remote add origin "%REPO_URL%"

git commit -m "JYOTISH 3.0 - Initial commit: Tamil Vedic Astrology Platform"

echo.
echo  Pushing to GitHub... (Browser may open for authentication)
echo.
git push -u origin main

if %ERRORLEVEL% == 0 (
    echo.
    echo  ================================================
    echo   SUCCESS! Your app is now on GitHub!
    echo  ================================================
    echo.
    echo  Your repo: %REPO_URL%
    echo.
    echo  NEXT STEP: Enable GitHub Pages
    echo   1. Go to your repo on GitHub
    echo   2. Click Settings tab
    echo   3. Click Pages in left sidebar
    echo   4. Source: main branch, / (root) folder
    echo   5. Click Save
    echo.
    echo  Your live site will be at:
    echo   https://YOUR-USERNAME.github.io/jyotish-app/
    echo.
    start "" "%REPO_URL%/settings/pages"
) else (
    echo.
    echo  [ERROR] Push failed. Common fixes:
    echo   - Make sure you created the repo on GitHub first
    echo   - Sign in to GitHub in the browser that opens
    echo   - If asked for password, use a Personal Access Token
    echo     Get one at: https://github.com/settings/tokens
)

echo.
pause
