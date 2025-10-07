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