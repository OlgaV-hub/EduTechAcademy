import os, requests
from dotenv import load_dotenv

load_dotenv()
FX_API_BASE = os.getenv('FX_API_BASE', 'https://api.exchangerate.host')
FX_API_FALLBACK = os.getenv('FX_API_FALLBACK', 'https://open.er-api.com/v6')
FX_API_ALT = os.getenv('FX_API_ALT', 'https://api.frankfurter.app')

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)

app = Flask(__name__)

# === конфиг приложения/БД ===
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY') or 'clave_secreta_123'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL') or 'sqlite:///users.db'
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

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         username = request.form['username'].strip()
#         password = request.form['password']
#         rol      = request.form['rol']

#         user = User.query.filter_by(username=username).first()

#         if (not user) or (not bcrypt.check_password_hash(user.password, password)):
#             return render_template('login.html', error="Usuario o contraseña incorrectos")

#         if user.role != rol:
#             return render_template('login.html', error="Rol incorrecto para este usuario")

#         login_user(user)
#         return redirect_by_role(user.role)

#     return render_template('login.html')

@app.route('/login', methods=['GET','POST'])
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

        # ВАЖНО: используем ИМЕНА ЭНДПОИНТОВ ИЗ ТВОЕГО КОДА
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

        # проверяем дубликаты по username (в твоей модели это unique)
        if User.query.filter_by(username=username).first():
            flash('El usuario ya existe.', 'warning')
            return redirect(url_for('register'))

        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, password=hashed_pw, role=role)
        db.session.add(user)
        db.session.commit()

        flash('Registro exitoso. Sesión iniciada.', 'success')
        login_user(user)

        # перенаправление по роли (имена эндпоинтов — как в твоём коде)
        if user.role == 'admin':
            return redirect(url_for('admin_panel'))
        elif user.role == 'profesor':
            return redirect(url_for('profesor_panel'))
        else:
            return redirect(url_for('estudiante_panel'))

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
    if current_user.role != 'estudiante':
        return render_template('403.html'), 403
    # вкладка "Inicio" активна по умолчанию
    return render_template('estudiante.html', active='resumen', cursos=[])

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

@app.route('/form_curso')
@login_required
def form_curso():
    if current_user.role not in ('profesor','admin'):
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

    # Duplicado (mismo profesor + mismo nombre)
    exist = Course.query.filter_by(
        nombre=nombre,
        teacher_id=current_user.id
    ).first()
    if exist:
        flash('Ya existe un curso con ese nombre para este profesor.', 'warning')
        return redirect(url_for('form_curso'))

    nuevo = Course(
        nombre=nombre,
        descripcion=descripcion,
        precio=precio,
        teacher_id=current_user.id if current_user.role == 'profesor' else None
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

        # Duplicado con el mismo profesor (excluyendo el curso actual)
        dup = Course.query.filter(
            Course.id != curso.id,
            Course.teacher_id == curso.teacher_id,
            Course.nombre == nombre
        ).first()
        if dup:
            flash('Ya existe un curso con ese nombre para este profesor.', 'warning')
            return redirect(url_for('editar_curso', course_id=curso.id))

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
    if current_user.role != 'estudiante':
        return render_template('403.html'), 403

    inscripciones = Enrollment.query.filter_by(user_id=current_user.id).all()
    cursos_ids = [i.course_id for i in inscripciones]
    cursos = Course.query.filter(Course.id.in_(cursos_ids)).all() if cursos_ids else []

    return render_template('estudiante.html', active='mis', cursos=cursos)

@app.route('/foro')
def ver_foro():
    # Mostrar una lista de temas del foro de memoria
    return render_template('foro.html', temas=temas_foro)

@app.errorhandler(404)
def err_404(e):
    return render_template('404.html'), 404

def seed_usuarios_si_hace_falta():
    """Создаёт admin и profesor, если их ещё нет. Идемпотентно."""
    created = []

    def ensure(username, password, role):
        u = User.query.filter_by(username=username).first()
        if not u:
            # У ТЕБЯ в модели поле называется password, и ты хранишь там хэш.
            password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
            u = User(username=username, password=password_hash, role=role)
            db.session.add(u)
            db.session.commit()
            created.append(f'{username} ({role})')

    ensure('admin', 'admin123', 'admin')
    ensure('prof',  'prof123',  'profesor')

    if created:
        print('Seed usuarios -> creados:', created)
    else:
        print('Seed usuarios -> ya existen')

# --- INIT DB EN RENDER (se ejecuta al primer request) ---
@app.before_first_request
def _init_db_and_seed():
    from flask import current_app
    with current_app.app_context():
        db.create_all()
        # tus funciones ya existen en tu código:
        seed_cursos_si_hace_falta()
        seed_usuarios_si_hace_falta()
# --- fin ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_cursos_si_hace_falta()
        seed_usuarios_si_hace_falta() 
    app.run(debug=True)