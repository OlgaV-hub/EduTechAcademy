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



## EduTechAcademy — Proyecto Parcial 2

Plataforma educativa con autenticación, roles, gestión de cursos, inscripciones, subida de imágenes a AWS S3 y módulo de analítica con Pandas + Matplotlib.

## Setup (Local)
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt

## Env (Variables de entorno)

Copia .env.example → .env y asigna valores:

SECRET_KEY=
DATABASE_URL=sqlite:///users.db

Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:5000/auth/authorize

AWS S3 (para imágenes de cursos)
AWS_REGION=
S3_BUCKET=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=


## SQLite guarda datos en:
/instance/users.db

## Run (Local)
python app.py


Abrir en navegador:
http://127.0.0.1:5000

## Roles del sistema

Admin

 - acceso total
 - CRUD cursos
 - CRUD roles
 - ver / editar usuarios y sus roles

Profesor

 - crear / editar / eliminar sus propios cursos
 - gestionar inscripciones
 - colocar calificaciones
 - acceso a estadísticas propias

Estudiante

 - ver cursos
 - inscribirse
 - revisar cursos inscritos
 - panel de estadísticas personal

## Conversión de precios (API)

Ruta:

POST /cursos/<id>/convert


API primaria:
👉 https://api.exchangerate.host

Fallback:
👉 https://api.frankfurter.app

📌 Conversión USD → ARS/EUR/BRL
📌 En caso de error → mensaje controlado en UI

## Subida de imágenes a AWS S3

Ruta: formulario de creación/edición de curso

Se guarda la imagen con uuid4()

Permisos: ACL=public-read

Devuelve URL pública

Implementado en services/s3.py

## Módulo de analítica

Generación de gráficos PNG con:

Pandas

Matplotlib

Perfiles:

 - Admin → visión global
 - Profesor → cursos propios y desempeño
 - Estudiante → progreso personal

### En producción (Render) se muestran inicialmente datos demo.
### Al usar el sistema con datos reales → los gráficos se actualizan automáticamente.

## Estructura del proyecto (Blueprints)
app.py
/admin
/auth
/courses
/estudiante
/profesor
/foro
/services
/stats
/templates
/static


Separación por rol

Servicios desacoplados (OAuth, S3, analítica)

## Deploy (Render)

Crear cuenta → https://render.com

Nuevo servicio → Web Service

Conectar el repo (GitHub)

Build Command
pip install -r requirements.txt

Start Command
gunicorn app:app

Variables de entorno (obligatorias)
SECRET_KEY=
DATABASE_URL=sqlite:///users.db
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=<tu_url>/auth/authorize
AWS_REGION=
S3_BUCKET=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=


 - Render crea la base desde cero cada deploy → SQLite se resetea.
 - Si deseas persistencia real, necesito migrar a PostgreSQL.

## Google OAuth (Login con Google)
Flujo completo

Usuario hace clic en Iniciar sesión con Google

Google devuelve:

 - email
 - nombre
 - id

Si el email existe → se usa el rol actual

Si no existe → se crea usuario con rol estudiante

login_user() → sesión activa

Redirección automática según rol:

 - /admin
 - /profesor
 - /estudiante

## Gestión de roles

### Panel administrador:

/admin/users


Funciones:

 - listar
 - cambiar rol
 - eliminar

## Base de datos

Por defecto en local:
instance/users.db

 - Cursos
 - Usuarios
 - Inscripciones
 - Calificaciones
 - Datos demo de analítica

### Puedes borrar el archivo antes de entregar si necesitas base “limpia”.

## Listo para presentar

 - Requisitos del parcial implementados
 - CRUD por rol
 - Login + OAuth Google
 - S3 funcional
 - Analítica activa
 - Blueprint modular
 - Variables de entorno separadas