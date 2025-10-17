# EduTechAcademy — base

## Setup

python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt

## Env

Copia `.env.example` a `.env` y asigna valores:
SECRET_KEY
DATABASE_URL (local: sqlite:///users.db)

## Run

python app.py

# http://127.0.0.1:5000

## Roles

Admin: acceso total al panel y gestión de cursos
Profesor: creación, edición y eliminación de sus propios cursos
Estudiante: inscripción y visualización de cursos

## Conversión de precio (API)

- Ruta: POST /cursos/<id>/convert
- Base: https://api.exchangerate.host  (fallback: https://api.frankfurter.app)
- Desde USD a ARS/EUR; en caso de caída muestra mensaje de error controlado.

## Deploy (Render)

Crear cuenta en https://render.com

Nuevo servicio → Web Service

Conectar el repositorio del proyecto (GitHub)

En “Build Command”:
pip install -r requirements.txt

En “Start Command”:
gunicorn app:app

Agregar variables de entorno:
SECRET_KEY = clave_secreta
DATABASE_URL = sqlite:///users.db

Presionar Deploy y abrir la URL generada.