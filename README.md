# EduTechAcademy — base

## Setup
python -m venv .venv  
.venv\Scripts\Activate  
pip install -r requirements.txt

## Env
Copia `.env.example` a `.env` y asigna valores:
- SECRET_KEY
- DATABASE_URL (local: sqlite:///users.db)

## Run
python app.py  
# http://127.0.0.1:5000

## Conversión de precio (API)
- Ruta: POST /cursos/<id>/convert
- Base: https://api.exchangerate.host (fallback: https://api.frankfurter.app)
- Desde USD a ARS/EUR; en caso de caída muestra mensaje de error controlado.