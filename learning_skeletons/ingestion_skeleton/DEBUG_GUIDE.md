# Ingestion DEBUG GUIDE

1. PDF 文本缺失：检查 `pypdf` 与图片 OCR 分支。  
2. 文档切块异常短：检查 chunk_size/overlap 配置。  
3. 图片无文本：检查本地 OCR 与 vision 模型配置。
