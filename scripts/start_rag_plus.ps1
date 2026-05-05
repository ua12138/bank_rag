param(
  [int]$Port = 8092
)

$ErrorActionPreference = "Stop"
uvicorn RAG_PLUS.main:app --host 0.0.0.0 --port $Port --reload

