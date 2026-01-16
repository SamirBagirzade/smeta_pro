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

where git >nul 2>&1 || (echo ERROR: git not found in PATH & timeout /t 5 & exit /b 1)
where python >nul 2>&1 || (echo ERROR: python not found in PATH & timeout /t 5 & exit /b 1)

if not exist "%REPO_DIR%\" (
  echo Repo not found. Cloning...
  git clone "%REPO_URL%" "%REPO_DIR%" || (timeout /t 5 & exit /b 1)
) else (
  echo Repo exists. Pulling latest...
  pushd "%REPO_DIR%" || (timeout /t 5 & exit /b 1)
  git fetch --all || (popd & timeout /t 5 & exit /b 1)
  if not "%BRANCH%"=="" (
    git checkout "%BRANCH%" || (popd & timeout /t 5 & exit /b 1)
  )
  git pull || (popd & timeout /t 5 & exit /b 1)
  popd
)

pushd "%REPO_DIR%" || (timeout /t 5 & exit /b 1)

if "%USE_VENV%"=="1" (
  if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo Creating venv...
    python -m venv "%VENV_DIR%" || (popd & timeout /t 5 & exit /b 1)
  )

  if exist "%REQ_FILE%" (
    echo Installing/updating requirements...
    "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip >nul 2>&1 || (popd & timeout /t 5 & exit /b 1)
    "%VENV_DIR%\Scripts\python.exe" -m pip install -r "%REQ_FILE%" >nul 2>&1 || (popd & timeout /t 5 & exit /b 1)
  )

  echo Starting program...
  start "" /B "%VENV_DIR%\Scripts\pythonw.exe" "%PY_ENTRY%" >nul 2>&1
) else (
  echo Starting program...
  start "" /B pythonw.exe "%PY_ENTRY%" >nul 2>&1
)

popd
endlocal
exit
