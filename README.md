# EduTechAcademy — Plataforma Educativa (Flask)

Plataforma educativa con autenticación (local + Google OAuth), gestión de cursos por rol, paneles dedicados, subida de imágenes a AWS S3 y módulo de analítica (Pandas + Matplotlib).
Proyecto desarrollado para el Parcial 2 — Análisis y Metodología de Sistemas (AMS).

# Arquitectura General

El proyecto está organizado en módulos independientes mediante Blueprints:

EduTechAcademy/
│
├── app.py                # Aplicación principal / registro de Blueprints
├── seeds.py              # Datos demo (usuarios, cursos, inscripciones, notas)
│
├── admin/                # Panel Administrador
├── auth/                 # Autenticación local + Google OAuth
├── profesor/             # Panel Profesor
├── estudiante/           # Panel Estudiante
├── courses/              # CRUD de cursos
├── foro/                 # Foro simple
├── services/             # S3 / conversión de moneda / utilidades
├── stats/                # Generación de gráficos con Pandas + Matplotlib
│
├── templates/            # Vistas Jinja2
├── static/               # CSS, JS, imágenes
│
├── requirements.txt
└── .env.example


Características:

Blueprints reales (módulos desacoplados).

Gestión de roles sin modificar app.py.

Servicios externos aislados en /services.

Datos demo fuera del código productivo (solo seeds.py).

# Instalación (Local)

1. Crear entorno virtual:

python -m venv .venv
.venv\Scripts\activate  (Windows)
source .venv/bin/activate  (Linux/Mac)


2. Instalar dependencias:

pip install -r requirements.txt


3. Copiar .env.example a .env y completar:

SECRET_KEY=
DATABASE_URL=sqlite:///users.db

## Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:5000/auth/authorize

## AWS S3
AWS_REGION=
S3_BUCKET=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Ejecución (Local)
python app.py


Abrir en el navegador:

http://127.0.0.1:5000

# Datos Demo

Los datos demo ya no están dentro de app.py.
Todo el seed se ejecuta desde:

python seeds.py


Incluye:

Usuarios (admin, profesores, estudiantes)

Estudiantes adicionales respecto a versiones previas

Cursos

Inscripciones

Notas básicas

Datos para analítica

Esto permite probar la plataforma completa sin modificar el código.

# Autenticación
## Login local

Usuario/contraseña guardados en DB.

## Google OAuth

Si el email existe → se usa el rol actual.

Si no existe → se crea usuario con rol estudiante.

Inicio de sesión vía Flask-Login.

Redirección automática según rol:

/admin

/profesor

/estudiante

# Roles y Paneles
## Administrador

CRUD usuarios

CRUD cursos

Cambio de roles

Estadísticas globales

## Profesor

Crear / editar / eliminar cursos propios

Gestionar inscripciones

Colocar calificaciones

Estadísticas de desempeño por curso

## Estudiante

Navegar cursos

Inscribirse

Revisar cursos inscritos

Panel de estadísticas personales

# Subida de Imágenes (AWS S3)

 - Implementado en services/s3.py

 - Upload con uuid4()

 - ACL=public-read

 - Devuelve URL pública

 - Integrado al CRUD de cursos

# Conversión de Precios

Endpoint:

  POST /cursos/<id>/convert


Proveedor principal:

  https://api.exchangerate.host


Fallback:

  https://api.frankfurter.app


Monedas:

  USD → ARS

  USD → EUR

  USD → BRL

  La UI maneja el error sin romper la vista.

# Analítica

Generación de gráficos PNG mediante:

 - Pandas
 - Matplotlib

Perfiles:

 - Admin: visión global
 - Profesor: desempeño de sus cursos
 - Estudiante: progreso personal

En producción (Render):

 - Se visualizan datos demo (seeds).
 - Con datos reales, los gráficos se recalculan.

# Base de Datos

Por defecto (local):
instance/users.db

Tablas:

 - User
 - Course
 - Enrollment
 - Grade
 - ForumMessage (opcional)
 - Datos demo iniciales
 - Puedes borrar el fichero para reiniciar.
 
# Deploy (Render)

Este bloque explica cómo desplegar la app (no la URL de tu entrega).

1. Crear cuenta en https://render.com
2. Nuevo servicio: Web Service
3. Conectar repositorio (GitHub)

## Build Command
pip install -r requirements.txt


## Start Command
gunicorn app:app


## Variables obligatorias

SECRET_KEY=
DATABASE_URL=
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=<TU_URL>/auth/authorize
AWS_REGION=
S3_BUCKET=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=


## Notas importantes:

 - Render reinicia SQLite con cada deploy.
 - Para persistencia real → usar PostgreSQL.

# Mejoras Futuras (Roadmap)

1. Migración de SQLite a PostgreSQL
2. Sistema de notificaciones
3. Materiales de cursos (archivos y links)
4. Dashboard responsive
 - Generación de certificados al finalizar un curso
 - Descarga desde el panel del estudiante
5. Mejora del panel Estudiante
 - Subida de trabajos
 - Historial de entregas y calificaciones
6. Módulo de valoración con IA
 - Opiniones de estudiantes
 - Análisis de sentimiento
 - Ranking por curso

# Estado actual (Parcial 2)

Blueprints modulares
CRUD completo por rol
Login + Google OAuth
AWS S3 funcional
Analítica activa
Seed reproducible
Integraciones externas reales
Variables de entorno separadas