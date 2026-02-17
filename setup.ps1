Write-Host "Setting up Minecraft Server Bot..." -ForegroundColor Cyan

# Create virtual environment
Write-Host "`nCreating virtual environment..." -ForegroundColor Yellow
python -m venv .venv

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "To run the bot, use: " -NoNewline
Write-Host ".\.venv\Scripts\python.exe main.py" -ForegroundColor Cyan
Write-Host "Or activate the venv first with: " -NoNewline
Write-Host ".\.venv\Scripts\Activate.ps1" -ForegroundColor Cyan
