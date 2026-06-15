@echo off
REM Inicia a aplicação Zapp Planeamento de Pagamentos
REM Porta: 8005
REM Host: 0.0.0.0 (acessível na rede)

echo.
echo ========================================
echo Zapp Planeamento de Pagamentos
echo ========================================
echo Porta: 8005
echo Host: 0.0.0.0 (Rede)
echo.
echo Para aceder localmente: http://localhost:8005
echo Para aceder pela rede: http://%COMPUTERNAME%:8005
echo ou substitua %COMPUTERNAME% pelo IP da máquina
echo.
echo Pressione qualquer tecla para iniciar...
pause > nul

cd /d "%~dp0"

REM Verificar se existe venv
if not exist "venv\Scripts\activate.bat" (
    echo Criando ambiente virtual...
    python -m venv venv
)

REM Ativar venv e instalar dependências
call venv\Scripts\activate.bat
pip install -q -r backend\requirements.txt

REM Iniciar a aplicação
echo Iniciando a aplicação...
python backend\main.py
