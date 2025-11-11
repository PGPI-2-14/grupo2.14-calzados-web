# run_mockdb.ps1
Write-Host "🚀 Iniciando Django con MockDB habilitada..." -ForegroundColor Cyan

# Establece variable de entorno solo para este proceso
$env:USE_MOCKDB = "1"

# Ejecuta el servidor de desarrollo
python manage.py runserver
