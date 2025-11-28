import os
import requests

from dotenv import load_dotenv

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)

from auth import auth_bp, oauth  

from services.s3 import subir_imagen_curso, url_publica

from datetime import datetime, timedelta


# =========================
# 1) CONFIG & INIT
# =========================

load_dotenv()

# --- FX API endpoints ---
FX_API_BASE = os.getenv('FX_API_BASE', 'https://api.exchangerate.host')
FX_API_FALLBACK = os.getenv('FX_API_FALLBACK', 'https://open.er-api.com/v6')
FX_API_ALT = os.getenv('FX_API_ALT', 'https://api.frankfurter.app')

# --- Flask app ---
app = Flask(__name__)

# Configuración de la aplicación / BD
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or 'clave_secreta_123'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL') or 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración de Google OAuth 
app.config["GOOGLE_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID")
app.config["GOOGLE_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET")

# Registrar un cliente OAuth y auth-blueprint
oauth.init_app(app)
app.register_blueprint(auth_bp, url_prefix="/auth")

# --- Extensiones---
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'login'

db.init_app(app)
bcrypt.init_app(app)
login_manager.init_app(app)

app.jinja_env.globals["url_publica"] = url_publica


# =========================
# 2) MODELS
# =========================

class User(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role     = db.Column(db.String(20), nullable=False, default='estudiante')


class Course(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(120), nullable=False)        
    descripcion = db.Column(db.Text, nullable=True)
    precio      = db.Column(db.Float, nullable=False, default=0.0) 
    teacher_id  = db.Column(db.Integer, nullable=True)             
    image_key   = db.Column(db.String(255), nullable=True)


class Enrollment(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, nullable=False)
    course_id = db.Column(db.Integer, nullable=False)
    status    = db.Column(db.String(20), nullable=False, default='pendiente')
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    nota = db.Column(db.Float, nullable=True)

app.db = db
app.Course = Course
app.Enrollment = Enrollment
app.User = User

# --- Flask-Login: cómo cargar usuario por ID ---
@login_manager.user_loader
def load_user(user_id):
    """Devuelve el usuario por id para Flask-Login."""
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None

# =========================
# 3) SERVICES & HELPERS
# =========================

def login_or_register_google_user(user_info):

    email = user_info.get("email")
    name = user_info.get("name") or email

    if not email:
        return None, "No se pudo obtener el email desde Google."

    user = User.query.filter_by(username=email).first()

    if not user:
        random_hash = bcrypt.generate_password_hash(os.urandom(16)).decode("utf-8")
        user = User(
            username=email,
            password=random_hash,
            role="estudiante",  
        )
        db.session.add(user)
        db.session.commit()

    return user, None


def convertir_monto_desde_usd(amount: float, to: str):

    providers = [FX_API_BASE, FX_API_FALLBACK, FX_API_ALT]

    for base in providers:
        try:
            # 1) exchangerate.host (Admite ARS y tiene endpoint /convert)
            if 'exchangerate.host' in base:
                r = requests.get(
                    f"{base}/convert",
                    params={"from": "USD", "to": to, "amount": amount},
                    timeout=6,
                )
                if r.ok:
                    data = r.json()
                    if data.get("result") is not None:
                        return float(data["result"]), None

            # 2) open.er-api.com 
            elif 'open-er-api' in base or 'open.er-api.com' in base:
                r = requests.get(f"{base}/latest/USD", timeout=6)
                if r.ok:
                    data = r.json()

                    if data.get("result") == "success":
                        rate = data.get("conversion_rates", {}).get(to)
                        if rate:
                            return float(amount) * float(rate), None

            # 3) frankfurter.app (estable, pero NO ARS; para EUR/USD)
            elif 'frankfurter.app' in base:
                r = requests.get(
                    f"{base}/latest",
                    params={"amount": amount, "from": "USD", "to": to},
                    timeout=6,
                )
                if r.ok:
                    data = r.json()
                    rate_value = data.get("rates", {}).get(to)
                    if rate_value is not None:
                        # Aquí la API devuelve inmediatamente la suma ya multiplicada.
                        return float(rate_value), None
        except requests.RequestException:
            # Probemos con el siguiente proveedor
            continue

    return None, "Todas las APIs fallaron o no están disponibles ahora."

app.convertir_monto_desde_usd = convertir_monto_desde_usd


def redirect_by_role(role: str):
    if role == 'admin':
        return redirect(url_for('admin.admin_panel'))
    elif role == 'profesor':
        return redirect(url_for('profesor.profesor_panel'))
    return redirect(url_for('estudiante.estudiante_panel'))


app.login_or_register_google_user = login_or_register_google_user
app.redirect_by_role = redirect_by_role


# Foro
temas_foro = ["Bienvenida", "Dudas de inscripción"]
app.temas_foro = temas_foro



# --- INIT DB EN RENDER / PROD (Flask 3.x, sin before_first_request) ---

from seeds import (
    seed_cursos_si_hace_falta,
    seed_usuarios_si_hace_falta,
    seed_stats_demo,
)


def _init_db_and_seed():
    with app.app_context():
        db.create_all()

        try:
            seed_cursos_si_hace_falta(db, Course)
        except Exception as e:
            print("Error en seed_cursos_si_hace_falta:", e)

        try:
            seed_usuarios_si_hace_falta(db, User, bcrypt)
        except Exception as e:
            print("Error en seed_usuarios_si_hace_falta:", e)

        try:
            seed_stats_demo(db, User, Course, Enrollment, bcrypt)
        except Exception as e:
            print("Error en seed_stats_demo:", e)


_init_db_and_seed()

# --- REGISTRO DE BLUEPRINTS ---

from stats import stats_bp
from courses import courses_bp
from profesor import profesor_bp
from admin import admin_bp
from foro import foro_bp
from estudiante import estudiante_bp

app.register_blueprint(stats_bp)
app.register_blueprint(courses_bp)
app.register_blueprint(profesor_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(foro_bp)
app.register_blueprint(estudiante_bp)

# =========================
# 4) ROUTES (Views)
# =========================

@app.route('/')
def index():
    # Mostrar la página de inicio con enlaces para Login/Registro
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        if not username or not password:
            flash('Complete usuario y contraseña.', 'warning')
            return redirect(url_for('login'))

        user = User.query.filter_by(username=username).first()
        if not user:
            flash('Usuario no encontrado.', 'danger')
            return redirect(url_for('login'))

        if not bcrypt.check_password_hash(user.password, password):
            flash('Contraseña incorrecta.', 'danger')
            return redirect(url_for('login'))

        login_user(user)
        flash('Sesión iniciada.', 'success')

        if user.role == 'admin':
            return redirect(url_for('admin.admin_panel'))
        elif user.role == 'profesor':
            return redirect(url_for('profesor.profesor_panel'))
        else:
            return redirect(url_for('estudiante.estudiante_panel'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        role = 'estudiante'

        if not username or not password:
            flash('Debe completar usuario y contraseña.', 'warning')
            return redirect(url_for('register'))

        if User.query.filter_by(username=username).first():
            flash('El usuario ya existe.', 'warning')
            return redirect(url_for('register'))

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password=hashed_pw, role=role)
        db.session.add(user)
        db.session.commit()

        flash('Registro exitoso. Sesión iniciada.', 'success')
        login_user(user)

        if user.role == 'admin':
            return redirect(url_for('admin.admin_panel'))
        elif user.role == 'profesor':
            return redirect(url_for('profesor.profesor_panel'))
        else:
            return redirect(url_for('estudiante.estudiante_panel'))

    return render_template('register.html')


# --- Auth utils ---

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/protected')
@login_required
def protected():
    return f"Hola {current_user.username} (rol: {current_user.role})"


# --- Error handlers ---

@app.errorhandler(404)
def err_404(e):
    return render_template('404.html'), 404


# =========================
# MAIN
# =========================

if __name__ == '__main__':
    app.run(debug=True)