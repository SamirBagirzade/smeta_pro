@echo off
setlocal enabledelayedexpansion

REM ====== CONFIG ======
set "REPO_URL=https://github.com/SamirBagirzade/smeta_pro.git"
set "REPO_DIR=REPO"
set "BRANCH="
set "PY_ENTRY=pyqt_crud_mongodb.py"
set "USE_VENV=1"
set "VENV_DIR=.venv"
set "REQ_FILE=requirements.txt"
REM ====================

where git >nul 2>&1 || (exit /b 1)
where python >nul 2>&1 || (exit /b 1)

if not exist "%REPO_DIR%\" (
  git clone "%REPO_URL%" "%REPO_DIR%" >nul 2>&1 || exit /b 1
) else (
  pushd "%REPO_DIR%" || exit /b 1
  git fetch --all >nul 2>&1 || (popd & exit /b 1)
  if not "%BRANCH%"=="" (
    git checkout "%BRANCH%" >nul 2>&1 || (popd & exit /b 1)
  )
  git pull >nul 2>&1 || (popd & exit /b 1)
  popd
)

pushd "%REPO_DIR%" || exit /b 1

if "%USE_VENV%"=="1" (
  if not exist "%VENV_DIR%\Scripts\python.exe" (
    python -m venv "%VENV_DIR%" >nul 2>&1 || (popd & exit /b 1)
  )

  if exist "%REQ_FILE%" (
    "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1
    "%VENV_DIR%\Scripts\python.exe" -m pip install -r "%REQ_FILE%" >nul 2>&1
  )
)

REM Don't launch Python here - VBS will do it
popd
endlocal
