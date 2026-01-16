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

echo Checking requirements...
where git >nul 2>&1 || (
  echo ERROR: Git not found! Please install Git from https://git-scm.com/
  pause
  exit /b 1
)

where python >nul 2>&1 || (
  echo ERROR: Python not found! Please install Python from https://python.org/
  pause
  exit /b 1
)

if not exist "%REPO_DIR%\" (
  echo Cloning repository...
  git clone "%REPO_URL%" "%REPO_DIR%" || (
    echo ERROR: Failed to clone repository!
    pause
    exit /b 1
  )
) else (
  echo Updating repository...
  pushd "%REPO_DIR%" || exit /b 1
  git fetch --all
  if not "%BRANCH%"=="" (
    git checkout "%BRANCH%"
  )
  git pull
  popd
)

pushd "%REPO_DIR%" || exit /b 1

if "%USE_VENV%"=="1" (
  if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv "%VENV_DIR%" || (
      popd
      echo ERROR: Failed to create virtual environment!
      pause
      exit /b 1
    )
  )

  if exist "%REQ_FILE%" (
    echo Installing/updating dependencies...
    "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip --quiet
    "%VENV_DIR%\Scripts\python.exe" -m pip install -r "%REQ_FILE%" --quiet
  )

  echo Starting Smeta Pro...
  "%VENV_DIR%\Scripts\python.exe" "%PY_ENTRY%"
) else (
  echo Starting Smeta Pro...
  python "%PY_ENTRY%"
)

popd
endlocal
