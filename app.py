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

def redirect_by_role(role: str):
    if role == 'admin':
        return redirect(url_for('admin_panel'))
    elif role == 'profesor':
        return redirect(url_for('profesor_panel'))
    return redirect(url_for('estudiante_panel'))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

cursos = [
    {'nombre': 'Programación 1', 'descripcion': 'Curso base'},
    {'nombre': 'Base de Datos',  'descripcion': 'Modelado y SQL'},
    {'nombre': 'UX Básico',      'descripcion': 'Introducción a UX'}
]
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
    # Mostrar una lista de cursos de memoria
    return render_template('cursos.html', cursos=cursos)

@app.route('/form_curso')
def form_curso():
    # Mostrar formulario de creación
    return render_template('form_curso.html')

@app.route('/agregar_curso', methods=['POST'])
def agregar_curso():
    # Tomar datos del formulario
    nombre = request.form.get('nombre')
    descripcion = request.form.get('descripcion')

    nuevo_curso = {
        'nombre': nombre,
        'descripcion': descripcion
    }

    if nuevo_curso in cursos:
        return render_template('Error.html')
    else:
        cursos.append(nuevo_curso)
        return redirect(url_for('listar_cursos'))

@app.route('/foro')
def ver_foro():
    # Mostrar una lista de temas del foro de memoria
    return render_template('foro.html', temas=temas_foro)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)