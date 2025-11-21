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

import io

import pandas as pd

import matplotlib
matplotlib.use("Agg")  # рендер без X-сервера
import matplotlib.pyplot as plt


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

# Конфиг приложения / БД
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or 'clave_secreta_123'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL') or 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Конфиг Google OAuth (как у профе)
app.config["GOOGLE_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID")
app.config["GOOGLE_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET")

# Регистрация OAuth-клиента и auth-blueprint
oauth.init_app(app)
app.register_blueprint(auth_bp, url_prefix="/auth")

# --- Расширения ---
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
    
    # когда студент записался на курс
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # итоговая оценка по курсу (0–10, например)
    nota = db.Column(db.Float, nullable=True)


# =========================
# 3) SERVICES & HELPERS
# =========================

def login_or_register_google_user(user_info):
    """
    Принимает словарь user_info от Google,
    возвращает (user, error_message).
    Если user=None, то error_message содержит текст ошибки.
    """
    email = user_info.get("email")
    name = user_info.get("name") or email

    if not email:
        # Без email не можем связать с нашей таблицей User
        return None, "No se pudo obtener el email desde Google."

    # Ищем пользователя по username=email
    user = User.query.filter_by(username=email).first()

    # Если пользователя ещё нет – создаём как estudiante
    if not user:
        # Генерируем случайный пароль, чтобы поле password не было пустым
        random_hash = bcrypt.generate_password_hash(os.urandom(16)).decode("utf-8")
        user = User(
            username=email,
            password=random_hash,
            role="estudiante",  # базовая роль
        )
        db.session.add(user)
        db.session.commit()

    return user, None


def convertir_monto_desde_usd(amount: float, to: str):
    """
    Пробуем 2–3 бесплатных API. Возвращаем (valor_convertido, error_str).
    Внутренняя валюта – USD.
    """
    providers = [FX_API_BASE, FX_API_FALLBACK, FX_API_ALT]

    for base in providers:
        try:
            # 1) exchangerate.host (поддерживает ARS и есть endpoint /convert)
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

            # 2) open.er-api.com (без ключа; берём курс и умножаем)
            elif 'open-er-api' in base or 'open.er-api.com' in base:
                r = requests.get(f"{base}/latest/USD", timeout=6)
                if r.ok:
                    data = r.json()
                    # ожидаем {"result":"success","conversion_rates":{"ARS": ...}}
                    if data.get("result") == "success":
                        rate = data.get("conversion_rates", {}).get(to)
                        if rate:
                            return float(amount) * float(rate), None

            # 3) frankfurter.app (стабильный, но НЕТ ARS; хорош для EUR/USD)
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
                        # здесь API сразу возвращает уже умноженную сумму
                        return float(rate_value), None
        except requests.RequestException:
            # пробуем следующий провайдер
            continue

    return None, "Todas las APIs fallaron o no están disponibles ahora."


def redirect_by_role(role: str):
    if role == 'admin':
        return redirect(url_for('admin_panel'))
    elif role == 'profesor':
        return redirect(url_for('profesor_panel'))
    return redirect(url_for('estudiante_panel'))


# Даём доступ к этим функциям через объект app,
# чтобы blueprints могли их вызывать через current_app,
# не импортируя модуль app вторым разом.
app.login_or_register_google_user = login_or_register_google_user
app.redirect_by_role = redirect_by_role


def seed_cursos_si_hace_falta():
    """Создаёт 1–2 курса, если таблица пустая."""
    if Course.query.count() == 0:
        db.session.add_all([
            Course(nombre="Programación 1", descripcion="Curso base", precio=100.0),
            Course(nombre="Base de Datos", descripcion="Modelado y SQL", precio=120.0),
        ])
        db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login: получить пользователя по ID (всегда из БД)."""
    try:
        return User.query.get(int(user_id))
    except Exception:
        return None


# Простейший форум в памяти
temas_foro = ["Bienvenida", "Dudas de inscripción"]


def seed_usuarios_si_hace_falta():
    """Создаёт admin и profesor, если их ещё нет. Идемпотентно."""
    created = []

    def ensure(username, password, role):
        u = User.query.filter_by(username=username).first()
        if not u:
            # В модели поле называется password, там хранится хэш
            password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            u = User(username=username, password=password_hash, role=role)
            db.session.add(u)
            db.session.commit()
            created.append(f'{username} ({role})')

    ensure('admin', 'admin123', 'admin')
    ensure('prof',  'prof123',  'profesor')
    ensure('alumno_demo', 'demo123', 'estudiante')

    if created:
        print('Seed usuarios -> creados:', created)
    else:
        print('Seed usuarios -> ya existen')
    

def seed_stats_demo():
    """Создаёт демо-инскрипции и оценки для графиков, если таблица пустая."""
    if Enrollment.query.count() > 0:
        print("Seed stats -> ya hay inscripciones, no se crean datos demo")
        return

    # 1) Находим/создаём демо-студента
    est = User.query.filter_by(username="alumno_demo").first()
    if not est:
        pw_hash = bcrypt.generate_password_hash("demo123").decode("utf-8")
        est = User(username="alumno_demo", password=pw_hash, role="estudiante")
        db.session.add(est)
        db.session.commit()
        print("Seed stats -> creado usuario alumno_demo / demo123")

    # 2) Курсы (из seed_cursos)
    c1 = Course.query.filter_by(nombre="Programación 1").first()
    c2 = Course.query.filter_by(nombre="Base de Datos").first()

    # если нет — на всякий случай создадим
    if not c1:
        c1 = Course(nombre="Programación 1", descripcion="Curso base", precio=100.0)
        db.session.add(c1)
    if not c2:
        c2 = Course(nombre="Base de Datos", descripcion="Modelado y SQL", precio=120.0)
        db.session.add(c2)
    db.session.commit()

    # 3) Даты для активности
    now = datetime.utcnow()

    demo_ins = [
        # Curso 1: entregado, высокая оценка
        Enrollment(
            user_id=est.id,
            course_id=c1.id,
            status="entregado",
            nota=9.0,
            created_at=now - timedelta(days=10),
        ),
        # Curso 2: entregado, с оценкой 7 (чтобы появился на графике notas)
        Enrollment(
            user_id=est.id,
            course_id=c2.id,
            status="entregado",
            nota=7.0,
            created_at=now - timedelta(days=7),
        ),
        # Curso 1: ещё одна entrega, чтобы был "пик" по датам
        Enrollment(
            user_id=est.id,
            course_id=c1.id,
            status="entregado",
            nota=8.0,
            created_at=now - timedelta(days=4),
        ),
        # Дополнительная запись "не сдано" (pendiente, без оценки)
        Enrollment(
            user_id=est.id,
            course_id=c2.id,
            status="pendiente",
            nota=None,
            created_at=now - timedelta(days=1),
        ),
    ]

    db.session.add_all(demo_ins)
    db.session.commit()
    print("Seed stats -> creadas inscripciones demo")


# --- INIT DB EN RENDER / PROD (Flask 3.x, sin before_first_request) ---

def _init_db_and_seed():
    with app.app_context():
        db.create_all()
        # Если эти функции уже есть — они просто создадут записи, если их нет
        try:
            seed_cursos_si_hace_falta()
        except Exception:
            pass
        try:
            seed_usuarios_si_hace_falta()
        except Exception:
            pass


# вызываем инициализацию на старте процесса (импорт модуля под gunicorn)
_init_db_and_seed()

# =========================
# 3b) STATS (Pandas + Matplotlib)
# =========================

stats_bp = Blueprint("stats", __name__)


def _fig_to_png(fig):
    """Сохранить фигуру в PNG и вернуть send_file."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return send_file(buf, mimetype="image/png")


def _solo_admin_o_profesor():
    return current_user.is_authenticated and current_user.role in ("admin", "profesor")


# ---------- ADMIN / PROF: inscripciones ----------

@stats_bp.route("/admin/stats/inscripciones.png")
@login_required
def admin_inscripciones_png():
    if not _solo_admin_o_profesor():
        return "Acceso denegado", 403

    # join Course + Enrollment
    q = db.session.query(
        Course.nombre.label("curso"),
        db.func.count(Enrollment.id).label("inscripciones"),
    ).join(Enrollment, Enrollment.course_id == Course.id)

    # если это profesor — считаем только его курсы
    if current_user.role == "profesor":
        q = q.filter(Course.teacher_id == current_user.id)

    q = q.group_by(Course.id)
    rows = q.all()

    if not rows:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)

    df = pd.DataFrame(rows, columns=["curso", "inscripciones"])

    fig, ax = plt.subplots(figsize=(6, 4))
    colors = plt.cm.Pastel1(range(len(df)))
    ax.bar(df["curso"], df["inscripciones"], color=colors)

    ax.set_title("Inscripciones por curso")
    ax.set_ylabel("Inscripciones")
    ax.set_xlabel("Curso")
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    fig.tight_layout()
    return _fig_to_png(fig)


# ---------- ADMIN / PROF: notas ----------

@stats_bp.route("/admin/stats/notas.png")
@login_required
def admin_notas_png():
    if not _solo_admin_o_profesor():
        return "Acceso denegado", 403

    q = (
        db.session.query(
            Course.nombre.label("curso"),
            Enrollment.nota.label("nota"),
        )
        .join(Course, Enrollment.course_id == Course.id)
        .filter(Enrollment.nota.isnot(None))
    )

    if current_user.role == "profesor":
        q = q.filter(Course.teacher_id == current_user.id)

    rows = q.all()
    if not rows:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)

    df = pd.DataFrame(rows, columns=["curso", "nota"])
    df_group = df.groupby("curso")["nota"].mean().reset_index()

    fig, ax = plt.subplots()
    df_group.plot(kind="bar", x="curso", y="nota", legend=False, ax=ax)
    ax.set_ylabel("Nota promedio")
    ax.set_xlabel("Curso")
    fig.tight_layout()

    return _fig_to_png(fig)


# ---------- ADMIN / PROF: actividad (inscripciones por fecha) ----------

@stats_bp.route("/admin/stats/actividad.png")
@login_required
def admin_actividad_png():
    if not _solo_admin_o_profesor():
        return "Acceso denegado", 403

    q = db.session.query(
        db.func.date(Enrollment.created_at).label("fecha"),
        db.func.count(Enrollment.id).label("cantidad"),
    )

    if current_user.role == "profesor":
        # фильтруем по курсам данного преподавателя
        q = (
            q.join(Course, Enrollment.course_id == Course.id)
            .filter(Course.teacher_id == current_user.id)
        )

    q = q.group_by(db.func.date(Enrollment.created_at)).order_by(
        db.func.date(Enrollment.created_at)
    )
    rows = q.all()

    if not rows:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)

    df = pd.DataFrame(rows, columns=["fecha", "cantidad"])

    fig, ax = plt.subplots()
    df.plot(kind="line", x="fecha", y="cantidad", marker="o", ax=ax, legend=False)
    ax.set_ylabel("Inscripciones")
    ax.set_xlabel("Fecha")
    fig.autofmt_xdate()
    fig.tight_layout()

    return _fig_to_png(fig)


# ---------- ADMIN / PROF: страница с тремя графиками ----------

@stats_bp.route("/admin/stats")
@login_required
def admin_stats_page():
    if not _solo_admin_o_profesor():
        return "Acceso denegado", 403
    # один и тот же шаблон для admin и profesor
    return render_template("admin_stats.html", active="stats")


@stats_bp.route("/profesor/stats")
@login_required
def profesor_stats_page():
    # просто алиас на ту же страницу
    return admin_stats_page()


# ---------- ESTUDIANTE: notas ----------

@stats_bp.route("/estudiante/stats/notas.png")
@login_required
def estudiante_notas_png():
    if current_user.role != "estudiante":
        return "Acceso denegado", 403

    q = (
        db.session.query(
            Course.nombre.label("curso"),
            Enrollment.nota.label("nota"),
        )
        .join(Course, Enrollment.course_id == Course.id)
        .filter(
            Enrollment.user_id == current_user.id,
            Enrollment.nota.isnot(None),
        )
    )

    rows = q.all()
    if not rows:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, "Sin datos", ha="center", va="center")
            ax.axis("off")
            return _fig_to_png(fig)

    df = pd.DataFrame(rows, columns=["curso", "nota"])
    df_group = df.groupby("curso")["nota"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(6, 4))

    # красивые разные цвета из палитры
    colors = plt.cm.Set2(range(len(df_group)))
    ax.bar(df_group["curso"], df_group["nota"], color=colors)

    ax.set_title("Notas por curso")
    ax.set_ylabel("Nota promedio")
    ax.set_xlabel("Curso")
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    fig.tight_layout()
    return _fig_to_png(fig)


# ---------- ESTUDIANTE: estado entregas (используем status инскрипций) ----------

@stats_bp.route("/estudiante/stats/estado_entregas.png")
@login_required
def estudiante_estado_entregas_png():
    if current_user.role != "estudiante":
        return "Acceso denegado", 403

    q = (
        db.session.query(
            Enrollment.status.label("estado"),
            db.func.count(Enrollment.id).label("cantidad"),
        )
        .filter(Enrollment.user_id == current_user.id)
        .group_by(Enrollment.status)
    )

    rows = q.all()
    if not rows:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)

    df = pd.DataFrame(rows, columns=["estado", "cantidad"])

    fig, ax = plt.subplots()
    df.plot(kind="bar", x="estado", y="cantidad", legend=False, ax=ax)
    ax.set_ylabel("Cantidad")
    ax.set_xlabel("Estado")
    fig.tight_layout()

    return _fig_to_png(fig)


# ---------- ESTUDIANTE: страница «Mi estadística» ----------

@stats_bp.route("/estudiante/stats")
@login_required
def estudiante_stats_page():
    if current_user.role != "estudiante":
        return "Acceso denegado", 403
    return render_template("estudiante_stats.html", active="mi_stats")


# Регистрация blueprint-а
app.register_blueprint(stats_bp)

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

        # пароль хранится как bcrypt-хэш в user.password
        if not bcrypt.check_password_hash(user.password, password):
            flash('Contraseña incorrecta.', 'danger')
            return redirect(url_for('login'))

        login_user(user)
        flash('Sesión iniciada.', 'success')

        # Имена эндпоинтов — как в твоём коде
        if user.role == 'admin':
            return redirect(url_for('admin_panel'))
        elif user.role == 'profesor':
            return redirect(url_for('profesor_panel'))
        else:
            return redirect(url_for('estudiante_panel'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''

        # жёстко назначаем роль студенту
        role = 'estudiante'

        if not username or not password:
            flash('Debe completar usuario y contraseña.', 'warning')
            return redirect(url_for('register'))

        # проверяем дубликаты по username
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
            return redirect(url_for('admin_panel'))
        elif user.role == 'profesor':
            return redirect(url_for('profesor_panel'))
        else:
            return redirect(url_for('estudiante_panel'))

    return render_template('register.html')


# --- Панель администратора + CRUD пользователей ---

@app.route('/admin')
@login_required
def admin_panel():
    if current_user.role != 'admin':
        return render_template('403.html'), 403
    return render_template('admin.html')


@app.route('/admin/users')
@login_required
def admin_users():
    # Только админ может видеть список пользователей
    if current_user.role != 'admin':
        return render_template('403.html'), 403

    users = User.query.all()
    return render_template('admin_users.html', users=users)


@app.route('/admin/users/<int:user_id>/update_role', methods=['POST'])
@login_required
def admin_update_user_role(user_id):
    if current_user.role != 'admin':
        return render_template('403.html'), 403

    new_role = request.form.get('role')
    user = User.query.get_or_404(user_id)
    user.role = new_role
    db.session.commit()

    return redirect(url_for('admin_users'))


@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        return render_template('403.html'), 403

    user = User.query.get_or_404(user_id)

    # не дать админу удалить самого себя
    if user.id == current_user.id:
        return redirect(url_for('admin_users'))

    db.session.delete(user)
    db.session.commit()

    return redirect(url_for('admin_users'))


# --- Панели profesor / estudiante ---

@app.route('/profesor')
@login_required
def profesor_panel():
    if current_user.role not in ('profesor', 'admin'):
        return render_template('403.html'), 403
    return render_template('profesor.html')


@app.route('/estudiante')
@login_required
def estudiante_panel():
    if current_user.role != 'estudiante':
        return render_template('403.html'), 403

    msg = request.args.get('msg')
    
    return render_template('estudiante.html', active='inicio', cursos=[], msg=msg)


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


# --- Cursos y FX ---

@app.route('/cursos')
@login_required
def listar_cursos():
    # Admin видит все курсы
    if current_user.role == 'admin':
        cursos = Course.query.all()

    # Profesor видит только свои курсы
    elif current_user.role == 'profesor':
        cursos = Course.query.filter_by(teacher_id=current_user.id).all()

    # Estudiante (и прочие) видят все доступные курсы для inscripción
    else:
        cursos = Course.query.all()

    return render_template('cursos.html', cursos=cursos)


@app.route('/cursos/<int:course_id>')
def detalle_curso(course_id):
    curso = Course.query.get_or_404(course_id)
    return render_template(
        'curso_detalle.html',
        curso=curso,
        converted=None,
        error=None,
        moneda=None,
        amount=None
    )


@app.route('/cursos/<int:course_id>/convert', methods=['POST'])
def convertir_precio(course_id):
    curso = Course.query.get_or_404(course_id)
    amount_str = request.form.get('amount', '').strip()
    moneda = request.form.get('to', 'ARS').upper()

    try:
        amount = float(amount_str or 0)
    except ValueError:
        amount = 0.0

    converted, error = convertir_monto_desde_usd(amount, moneda)

    return render_template(
        'curso_detalle.html',
        curso=curso,
        converted=converted,
        error=error,
        moneda=moneda,
        amount=amount
    )

@app.route('/profesor/curso/<int:course_id>/inscripciones', methods=['GET', 'POST'])
@login_required
def gestionar_inscripciones_curso(course_id):
    # Доступ только профу и админу
    if current_user.role not in ('profesor', 'admin'):
        return render_template('403.html'), 403

    curso = Course.query.get_or_404(course_id)

    # Профессор может видеть только свои курсы
    if current_user.role == 'profesor' and curso.teacher_id != current_user.id:
        return render_template('403.html'), 403

    # --- Обработка обновления одной инскрипции ---
    if request.method == 'POST':
        enroll_id_str = request.form.get('enrollment_id', '').strip()
        status = request.form.get('status', '').strip()
        nota_str = request.form.get('nota', '').strip()

        # допустимые статусы
        allowed_status = ['pendiente', 'entregado', 'vencido']

        try:
            enroll_id = int(enroll_id_str)
        except ValueError:
            flash('ID de inscripción inválido.', 'warning')
            return redirect(url_for('gestionar_inscripciones_curso',
                                    course_id=course_id))

        insc = Enrollment.query.get_or_404(enroll_id)

        # доп. проверка: эта inscripción должна относиться к текущему курсу
        if insc.course_id != curso.id:
            flash('La inscripción no pertenece a este curso.', 'warning')
            return redirect(url_for('gestionar_inscripciones_curso',
                                    course_id=course_id))

        # статус
        if status in allowed_status:
            insc.status = status

        # nota (может быть пустой)
        if nota_str == '':
            insc.nota = None
        else:
            try:
                insc.nota = float(nota_str)
            except ValueError:
                flash('La nota debe ser numérica.', 'warning')

        db.session.commit()
        flash('Inscripción actualizada.', 'success')
        return redirect(url_for('gestionar_inscripciones_curso',
                                course_id=course_id))

    # --- GET: показать список студентов этого курса ---
    inscripciones = (
        db.session.query(Enrollment, User)
        .join(User, User.id == Enrollment.user_id)
        .filter(Enrollment.course_id == course_id)
        .all()
    )

    return render_template(
        'profesor_inscripciones.html',
        curso=curso,
        inscripciones=inscripciones
    )

@app.route('/form_curso')
@login_required
def form_curso():
    if current_user.role not in ('profesor', 'admin'):
        return render_template('403.html'), 403
    return render_template('form_curso.html')


@app.route('/agregar_curso', methods=['POST'])
@login_required
def agregar_curso():
    if current_user.role not in ('admin', 'profesor'):
        return render_template('403.html'), 403

    nombre = (request.form.get('nombre') or '').strip()
    descripcion = (request.form.get('descripcion') or '').strip()
    try:
        precio = float(request.form.get('precio') or 0)
    except ValueError:
        precio = 0

    if not nombre:
        return "Nombre es obligatorio", 400

    # проверка дубликата (как было раньше)
    exist = Course.query.filter_by(
        nombre=nombre,
        teacher_id=current_user.id
    ).first()
    if exist:
        flash('Ya existe un curso con ese nombre para este profesor.', 'warning')
        return redirect(url_for('form_curso'))

    # NUEVO: S3
    file = request.files.get('imagen')
    image_key = subir_imagen_curso(file)

    nuevo = Course(
        nombre=nombre,
        descripcion=descripcion,
        precio=precio,
        teacher_id=current_user.id if current_user.role == 'profesor' else None,
        image_key=image_key
    )
    db.session.add(nuevo)
    db.session.commit()
    flash('Curso creado', 'success')
    return redirect(url_for('listar_cursos'))


@app.route('/cursos/<int:course_id>/edit', methods=['GET', 'POST'])
@login_required
def editar_curso(course_id):
    curso = Course.query.get_or_404(course_id)

    # Permisos: admin o profesor dueño
    if current_user.role not in ('admin', 'profesor'):
        return render_template('403.html'), 403
    if current_user.role != 'admin' and curso.teacher_id != current_user.id:
        return render_template('403.html'), 403

    if request.method == 'POST':
        nombre = (request.form.get('nombre') or '').strip()
        descripcion = (request.form.get('descripcion') or '').strip()
        try:
            precio = float(request.form.get('precio') or 0)
        except ValueError:
            precio = 0

        
        dup = Course.query.filter(
            Course.id != curso.id,
            Course.teacher_id == curso.teacher_id,
            Course.nombre == nombre
        ).first()
        if dup:
            flash('Ya existe un curso con ese nombre para este profesor.', 'warning')
            return redirect(url_for('editar_curso', course_id=curso.id))

        # NUEVO: S3 
        file = request.files.get('imagen')
        if file and file.filename:
            new_key = subir_imagen_curso(file)
            if new_key:
                curso.image_key = new_key

        curso.nombre = nombre
        curso.descripcion = descripcion
        curso.precio = precio
        db.session.commit()
        flash('Curso actualizado', 'success')
        return redirect(url_for('listar_cursos'))

    # GET
    return render_template('form_curso.html', curso=curso)


@app.route('/cursos/<int:course_id>/delete', methods=['POST'])
@login_required
def eliminar_curso(course_id):
    curso = Course.query.get_or_404(course_id)

    if current_user.role not in ('admin', 'profesor'):
        return render_template('403.html'), 403
    if current_user.role != 'admin' and curso.teacher_id != current_user.id:
        return render_template('403.html'), 403

    db.session.delete(curso)
    db.session.commit()
    flash('Curso eliminado', 'info')
    return redirect(url_for('listar_cursos'))


@app.route('/inscribirme/<int:course_id>', methods=['POST'])
@login_required
def inscribirme(course_id):
    if current_user.role != 'estudiante':
        return render_template('403.html'), 403

    ya = Enrollment.query.filter_by(
        user_id=current_user.id,
        course_id=course_id
    ).first()
    if ya:
        return redirect(url_for('mis_cursos', msg='ya_inscripto'))

    if not Course.query.get(course_id):
        return redirect(url_for('listar_cursos', msg='curso_no_encontrado'))

    insc = Enrollment(
        user_id=current_user.id,
        course_id=course_id,
        status='pendiente'
    )
    db.session.add(insc)
    db.session.commit()
    return redirect(url_for('mis_cursos', msg='ok'))


@app.route('/mis-cursos')
@login_required
def mis_cursos():
    if current_user.role != 'estudiante':
        return render_template('403.html'), 403

    inscripciones = Enrollment.query.filter_by(user_id=current_user.id).all()
    cursos_ids = [i.course_id for i in inscripciones]
    cursos = Course.query.filter(Course.id.in_(cursos_ids)).all() if cursos_ids else []

    msg = request.args.get('msg')
    return render_template('estudiante.html', cursos=cursos, msg=msg, active='mis_cursos')


@app.route('/estudiante/cursos')
@login_required
def estudiante_todos_cursos():
    if current_user.role != 'estudiante':
        return render_template('403.html'), 403

    cursos = Course.query.all()
    msg = request.args.get('msg')
    return render_template(
        'estudiante.html',
        cursos=cursos,
        msg=msg,
        active='todos_cursos'
    )


# --- Foro ---

@app.route('/foro')
def ver_foro():
    # Mostrar una lista de temas del foro de memoria
    return render_template('foro.html', temas=temas_foro)


# --- Error handlers ---

@app.errorhandler(404)
def err_404(e):
    return render_template('404.html'), 404


# =========================
# MAIN
# =========================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_cursos_si_hace_falta()
        seed_usuarios_si_hace_falta()
        seed_stats_demo()
    app.run(debug=True)