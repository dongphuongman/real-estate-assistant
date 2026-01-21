# Troubleshooting (Windows & Cross‑platform)

## Windows: NumPy Import Error
```
ImportError: Unable to import required dependencies:
numpy: Error importing numpy: you should not try to import numpy from
        its source directory
```
**Fix**
```powershell
deactivate
Remove-Item -Recurse -Force .\.venv
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -e .[dev]
python -c "import numpy; print('NumPy OK')"
```

## Windows: Pandas C Extension Error
```
ModuleNotFoundError: No module named 'pandas._libs.pandas_parser'
```
**Fix**
```powershell
python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-cache-dir --force-reinstall "pandas>=2.2.0,<2.3.0"
```

## Windows: Pydantic-core Error
```
ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'
```
**Fix Order**
```powershell
python -m pip install "numpy>=1.24.0,<2.0.0"
python -m pip install --no-cache-dir "pydantic-core>=2.14.0,<3.0.0"
python -m pip install --no-cache-dir "pandas>=2.2.0,<2.3.0"
python -m pip install -r requirements.txt
```

## Common Issues

**Port already in use**
```powershell
# Backend (8000)
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Frontend (3000)
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

**API Key not recognized**
- Ensure `.env` exists and is in project root
- Restart the app after editing `.env`
- Ensure the client sends `X-API-Key` (frontend uses `NEXT_PUBLIC_API_KEY`)

**ChromaDB persistence issues**
```powershell
Remove-Item -Recurse -Force .\chroma_db
# Restart app — database will be recreated
```

**CORS errors in the browser**
- In production, set `ENVIRONMENT=production` and pin `CORS_ALLOW_ORIGINS` to your frontend URL(s).
- For local dev, keep `ENVIRONMENT` not `production` (backend allows `*`).

**Local Ollama not detected**
- Ensure Ollama is running and reachable from the backend container/host (`OLLAMA_API_BASE`).
- The Settings > Models view shows `runtime_available=false` when the API cannot connect.
### ChromaDB metadata errors

Symptoms:
- Messages like "Error adding batch: Expected metadata value of type 'string', 'number', 'boolean' or 'null'".

Cause:
- Non‑primitive values (lists, dicts, complex objects, raw numpy types) in document metadata.

Fix:
- Ensure only primitives go into metadata (str/int/float/bool/None). Convert datetimes to ISO 8601 strings. Avoid nesting dicts/lists.
- The vector store layer sanitizes metadata before insertion.

## Analytics: Pandas RuntimeWarning in YoY calculation

```
RuntimeWarning: '<' not supported between instances of 'Timestamp' and 'int', sort order is undefined for incomparable objects.
```

Cause:
- YoY percentage was computed without guarding for missing or zero previous values, which could trigger invalid operations during series calculations.

Fix:
- Ensure `avg_price` is numeric and compute YoY safely with guards for missing and zero previous values.
- This is implemented in `analytics/market_insights.py` and avoids invalid comparisons during calculation.
