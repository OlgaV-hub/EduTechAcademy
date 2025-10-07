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
        if not user:
            return "Usuario o contraseña incorrectos", 401

        # пароль верный?
        if not bcrypt.check_password_hash(user.password, password):
            return "Usuario o contraseña incorrectos", 401

        # роль совпадает с сохранённой?
        if user.role != rol:
            return "Rol incorrecto para este usuario", 403

        # всё ок — логиним и ведём на нужную панель
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
        return "Acceso denegado", 403
    return render_template('admin.html')

@app.route('/profesor')
@login_required
def profesor_panel():
    if current_user.role not in ('profesor', 'admin'):
        return "Acceso denegado", 403
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
    return render_template('curso_detalle.html', curso=curso)

@app.route('/form_curso')
def form_curso():
    # Mostrar formulario de creación
    return render_template('form_curso.html')

@app.route('/agregar_curso', methods=['POST'])
@login_required
def agregar_curso():
    # (опционально) только profesor/admin могут создавать
    if current_user.role not in ('profesor', 'admin'):
        return "Acceso denegado", 403

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
    # запретим дубликаты
    ya = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if ya:
        return redirect(url_for('mis_cursos'))  # уже записан

    # убедимся, что курс существует
    if not Course.query.get(course_id):
        return "Curso no encontrado", 404

    insc = Enrollment(user_id=current_user.id, course_id=course_id, status='pendiente')
    db.session.add(insc)
    db.session.commit()
    return redirect(url_for('mis_cursos'))

@app.route('/mis-cursos')
@login_required
def mis_cursos():
    inscripciones = Enrollment.query.filter_by(user_id=current_user.id).all()
    # найдём объекты курсов по id
    cursos_ids = [i.course_id for i in inscripciones]
    cursos = Course.query.filter(Course.id.in_(cursos_ids)).all() if cursos_ids else []
    return render_template('estudiante.html', cursos=cursos)

@app.route('/foro')
def ver_foro():
    # Mostrar una lista de temas del foro de memoria
    return render_template('foro.html', temas=temas_foro)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_cursos_si_hace_falta()
    app.run(debug=True)