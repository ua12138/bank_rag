param(
  [string]$KbId = "hz-bank-demo",
  [string]$QueriesFile = "data/eval_samples/perf_queries.json",
  [int]$Concurrency = 20,
  [int]$Rounds = 3,
  [string]$OutDir = "reports"
)

$ErrorActionPreference = "Stop"

Write-Host "[perf-ab] Running A/B evaluation..."
python scripts/perf_ab_eval.py `
  --kb-id $KbId `
  --queries-file $QueriesFile `
  --concurrency $Concurrency `
  --rounds $Rounds `
  --out-dir $OutDir `
  --use-rerank

if ($LASTEXITCODE -ne 0) {
  Write-Host "[perf-ab] Failed. Check logs above." -ForegroundColor Yellow
  exit $LASTEXITCODE
}

Write-Host "[perf-ab] Completed. Reports generated under $OutDir" -ForegroundColor Green
