import os, requests
from dotenv import load_dotenv

load_dotenv()
FX_API_BASE = os.getenv('FX_API_BASE', 'https://api.exchangerate.host')
FX_API_FALLBACK = os.getenv('FX_API_FALLBACK', 'https://open.er-api.com/v6')
FX_API_ALT = os.getenv('FX_API_ALT', 'https://api.frankfurter.app')

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)

app = Flask(__name__)

# === конфиг приложения/БД ===
app.config['SECRET_KEY'] = 'clave_secreta_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# === инициализация зависимостей ===
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'   # гости будут редиректиться сюда

class User(UserMixin, db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role     = db.Column(db.String(20), nullable=False, default='estudiante')

class Course(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    nombre      = db.Column(db.String(120), nullable=False)        # título
    descripcion = db.Column(db.Text, nullable=True)
    precio      = db.Column(db.Float, nullable=False, default=0.0) # price
    teacher_id  = db.Column(db.Integer, nullable=True)             # opcional: id del profe

class Enrollment(db.Model):
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, nullable=False)
    course_id  = db.Column(db.Integer, nullable=False)
    status     = db.Column(db.String(20), nullable=False, default='pendiente')

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

            # 2) open.er-api.com (без ключа; берем курс и умножаем)
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
    return User.query.get(int(user_id))

temas_foro = ["Bienvenida", "Dudas de inscripción"]

@app.route('/')
def index():
    # Mostrar la página de inicio con enlaces para Login/Registro
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        rol      = request.form['rol']

        user = User.query.filter_by(username=username).first()

        if (not user) or (not bcrypt.check_password_hash(user.password, password)):
            return render_template('login.html', error="Usuario o contraseña incorrectos")

        if user.role != rol:
            return render_template('login.html', error="Rol incorrecto para este usuario")

        login_user(user)
        return redirect_by_role(user.role)

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        rol      = request.form.get('rol', 'estudiante')  # admin | profesor | estudiante

        if User.query.filter_by(username=username).first():
            return "Usuario ya existe", 400

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password=hashed_pw, role=rol)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/admin')
@login_required
def admin_panel():
    if current_user.role != 'admin':
        return render_template('403.html'), 403
    return render_template('admin.html')

@app.route('/profesor')
@login_required
def profesor_panel():
    if current_user.role not in ('profesor', 'admin'):
        return render_template('403.html'), 403
    return render_template('profesor.html')

@app.route('/estudiante')
@login_required
def estudiante_panel():
    return render_template('estudiante.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/protected')
@login_required
def protected():
    return f"Hola {current_user.username} (rol: {current_user.role})"

@app.route('/cursos')
def listar_cursos():
    cursos = Course.query.all()
    return render_template('cursos.html', cursos=cursos)

@app.route('/cursos/<int:course_id>')
def detalle_curso(course_id):
    curso = Course.query.get_or_404(course_id)
    return render_template(
        'curso_detalle.html',
        curso=curso,
        converted=None,   # <— добавили
        error=None,       # <— добавили
        moneda=None,      # <— опционально, чтобы не ругалось
        amount=None       # <— опционально
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

@app.route('/form_curso')
@login_required
def form_curso():
    if current_user.role not in ('profesor','admin'):
        return render_template('403.html'), 403
    return render_template('form_curso.html')

@app.route('/agregar_curso', methods=['POST'])
@login_required
def agregar_curso():
    # (опционально) только profesor/admin могут создавать
    if current_user.role not in ('profesor', 'admin'):
        return render_template('403.html'), 403

    nombre      = request.form.get('nombre', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    precio_str  = request.form.get('precio', '0').strip()

    try:
        precio = float(precio_str)
    except ValueError:
        precio = 0.0

    if not nombre:
        return "Nombre es obligatorio", 400

    nuevo = Course(
        nombre=nombre,
        descripcion=descripcion,
        precio=precio,
        teacher_id=current_user.id  # opcional
    )
    db.session.add(nuevo)
    db.session.commit()
    return redirect(url_for('listar_cursos'))

@app.route('/inscribirme/<int:course_id>', methods=['POST'])
@login_required
def inscribirme(course_id):
    ya = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if ya:
        return redirect(url_for('mis_cursos', msg='ya_inscripto'))

    if not Course.query.get(course_id):
        return redirect(url_for('listar_cursos', msg='curso_no_encontrado'))

    insc = Enrollment(user_id=current_user.id, course_id=course_id, status='pendiente')
    db.session.add(insc)
    db.session.commit()
    return redirect(url_for('mis_cursos', msg='ok'))

@app.route('/mis-cursos')
@login_required
def mis_cursos():
    inscripciones = Enrollment.query.filter_by(user_id=current_user.id).all()
    cursos_ids = [i.course_id for i in inscripciones]
    cursos = Course.query.filter(Course.id.in_(cursos_ids)).all() if cursos_ids else []
    msg = request.args.get('msg')  # <— добавили
    return render_template('estudiante.html', cursos=cursos, msg=msg)

@app.route('/foro')
def ver_foro():
    # Mostrar una lista de temas del foro de memoria
    return render_template('foro.html', temas=temas_foro)

@app.errorhandler(404)
def err_404(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_cursos_si_hace_falta()
    app.run(debug=True)