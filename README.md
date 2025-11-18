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

## Google OAuth (Login con Google)

La aplicación permite iniciar sesión con Google usando OAuth 2.0.

### Cómo funciona

- El usuario hace clic en **Iniciar sesión con Google**.
- Google devuelve los datos del usuario (email, nombre, id).
- Se busca ese email en la base local (`User`):
  - si existe → se usa su rol actual (admin / profesor / estudiante);
  - si no existe → se crea un usuario nuevo con rol **estudiante**.
- Se inicia sesión con `login_user()` (Flask-Login).
- Se redirige al panel correspondiente según el rol:
  - `/admin`
  - `/profesor`
  - `/estudiante`

### Requisitos en `.env`

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:5000/auth/authorize

### Gestión de roles

El administrador puede cambiar roles desde  
`/admin/users` (listar, cambiar rol, eliminar).