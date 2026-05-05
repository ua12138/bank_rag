param(
  [string]$KbId = "hz-bank-demo",
  [string]$Query = "How to handle database connection pool alerts?",
  [string]$OutDir = "reports"
)

$ErrorActionPreference = "Stop"

Write-Host "[regression] Running end-to-end regression..."
python scripts/regression_run.py --kb-id $KbId --query $Query --out-dir $OutDir
if ($LASTEXITCODE -ne 0) {
  Write-Host "[regression] Completed with failures. Check report files under $OutDir" -ForegroundColor Yellow
  exit $LASTEXITCODE
}

Write-Host "[regression] Completed successfully." -ForegroundColor Green
