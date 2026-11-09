@echo off
setlocal
chcp 65001 >nul
title Painel de Zoonoses
cd /d "%~dp0"

if exist ".venv312\Scripts\python.exe" goto dependencias

echo Preparando o painel pela primeira vez...
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
    py -3.12 -m venv .venv312
) else (
    python -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
    if errorlevel 1 goto sem_python
    python -m venv .venv312
)
if errorlevel 1 goto erro

:dependencias
".venv312\Scripts\python.exe" -m pip --version >nul 2>&1
if not errorlevel 1 goto verificar_dependencias
echo Reparando o instalador de bibliotecas do Python...
".venv312\Scripts\python.exe" -m ensurepip --upgrade
if errorlevel 1 goto erro

:verificar_dependencias
if exist ".venv312\painel-dependencias.ok" goto iniciar
echo Instalando bibliotecas. Aguarde; esta etapa precisa de internet...
".venv312\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto erro
type nul > ".venv312\painel-dependencias.ok"

:iniciar
echo Abrindo o painel no navegador...
echo Mantenha esta janela aberta enquanto usar o painel.
echo Para encerrar, feche esta janela ou pressione Ctrl+C.
".venv312\Scripts\python.exe" -m streamlit run app.py --server.headless false
if errorlevel 1 goto erro
exit /b 0

:sem_python
echo.
echo Instale o Python 3.12 (64 bits) e marque "Add Python to PATH".
echo Depois, abra este arquivo novamente.
echo Download: https://www.python.org/downloads/windows/
pause
exit /b 1

:erro
echo.
echo Nao foi possivel iniciar o painel. Confira a mensagem acima.
echo Se o erro ocorreu na instalacao, confira sua conexao com a internet.
pause
exit /b 1
