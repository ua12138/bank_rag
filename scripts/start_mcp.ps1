param(
  [int]$Port = 8091
)

$ErrorActionPreference = "Stop"
Write-Host "Starting MCP wrapper at http://127.0.0.1:$Port ..."
uvicorn hz_bank_rag.mcp.main:app --host 127.0.0.1 --port $Port --reload
