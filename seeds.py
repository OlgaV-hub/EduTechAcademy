# seeds.py

from datetime import datetime, timedelta


def seed_cursos_si_hace_falta(db, Course):
    """
    Crea cursos de ejemplo solo si la tabla está vacía.
    No toca nada si ya hay cursos.
    """
    if Course.query.count() > 0:
        print("Seed cursos -> ya hay cursos, no se crean datos demo")
        return

    cursos_demo = [
        {
            "nombre": "Programación 1",
            "descripcion": (
                "Curso base de programación imperativa en Python: "
                "variables, condicionales, ciclos y funciones."
            ),
            "precio": 100.0,
        },
        {
            "nombre": "Base de Datos",
            "descripcion": (
                "Modelado entidad–relación, SQL básico, claves primarias/foráneas "
                "y consultas con filtros."
            ),
            "precio": 120.0,
        },
        {
            "nombre": "Desarrollo Web con HTML, CSS y Bootstrap",
            "descripcion": (
                "Fundamentos del desarrollo web, maquetación responsive con "
                "Bootstrap 5, componentes y grillas."
            ),
            "precio": 150.0,
        },
        {
            "nombre": "Introducción a UX/UI y Diseño Centrado en el Usuario",
            "descripcion": (
                "Heurísticas de Nielsen, investigación con usuarios, wireframes, "
                "prototipos y pruebas de usabilidad."
            ),
            "precio": 130.0,
        },
        {
            "nombre": "Java Essentials — Fundamentos del Lenguaje",
            "descripcion": (
                "Sintaxis básica, clases y objetos, herencia, manejo de "
                "excepciones y ejercicios prácticos."
            ),
            "precio": 150.0,
        },
        {
            "nombre": "C# Avanzado",
            "descripcion": (
                "Características avanzadas de C#, LINQ, colecciones genéricas y "
                "patrones comunes en aplicaciones desktop/web."
            ),
            "precio": 555.0,
        },
        {
            "nombre": "MariaDB / MySQL",
            "descripcion": (
                "Administración básica de bases de datos relacionales, creación "
                "de esquemas, índices y consultas JOIN."
            ),
            "precio": 777.0,
        },
        {
            "nombre": "Deep Learning",
            "descripcion": (
                "Introducción a redes neuronales profundas y flujo de trabajo "
                "típico en proyectos de datos."
            ),
            "precio": 777.0,
        },
        {
            "nombre": "PostgreSQL",
            "descripcion": (
                "Fundamentos de PostgreSQL para aplicaciones productivas: tipos "
                "de datos, índices y buenas prácticas."
            ),
            "precio": 999.0,
        },
    ]

    for data in cursos_demo:
        c = Course(
            nombre=data["nombre"],
            descripcion=data["descripcion"],
            precio=data["precio"],
            teacher_id=None,   # después lo asignamos al profe en seed_stats_demo
            image_key=None,    # imagen se sube desde el formulario (AWS S3)
        )
        db.session.add(c)

    db.session.commit()
    print("Seed cursos -> creados cursos demo")


def seed_usuarios_si_hace_falta(db, User, bcrypt):
    """
    Crea usuarios básicos (admin, prof, alumnos demo) si no existen.
    No modifica usuarios existentes.
    """
    created = []

    def ensure(username, password, role):
        u = User.query.filter_by(username=username).first()
        if not u:
            password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
            u = User(username=username, password=password_hash, role=role)
            db.session.add(u)
            db.session.commit()
            created.append(f"{username} ({role})")

    # usuarios principales
    ensure("admin", "admin123", "admin")
    ensure("prof", "prof123", "profesor")

    # alumnos demo
    ensure("alumno_demo", "demo123", "estudiante")
    ensure("alumno_ux", "ux123", "estudiante")
    ensure("alumno_data", "data123", "estudiante")

    if created:
        print("Seed usuarios -> creados:", created)
    else:
        print("Seed usuarios -> ya existen")


def seed_stats_demo(db, User, Course, Enrollment, bcrypt):
    """
    Crea inscripciones y notas de demostración para alimentar los gráficos
    (admin, profesor y estudiante).
    Solo se ejecuta si NO hay inscripciones.
    """
    if Enrollment.query.count() > 0:
        print("Seed stats -> ya hay inscripciones, no se crean datos demo")
        return

    def days_ago(n):
        return datetime.utcnow() - timedelta(days=n)

    # --- 1) Asegurar alumnos demo ---
    alumnos_info = [
        ("alumno_demo", "demo123"),
        ("alumno_ux", "ux123"),
        ("alumno_data", "data123"),
    ]

    alumnos = {}
    for username, pwd in alumnos_info:
        u = User.query.filter_by(username=username).first()
        if not u:
            pw_hash = bcrypt.generate_password_hash(pwd).decode("utf-8")
            u = User(username=username, password=pw_hash, role="estudiante")
            db.session.add(u)
            db.session.commit()
            print(f"Seed stats -> creado usuario {username}")
        alumnos[username] = u

    # --- 2) Asegurar cursos (igual que en seed_cursos_si_hace_falta) ---
    def get_or_create_curso(nombre, descripcion, precio):
        c = Course.query.filter_by(nombre=nombre).first()
        if not c:
            c = Course(
                nombre=nombre,
                descripcion=descripcion,
                precio=precio,
                teacher_id=None,
                image_key=None,
            )
            db.session.add(c)
            db.session.commit()
        return c

    c_prog1 = get_or_create_curso(
        "Programación 1",
        "Curso base de programación imperativa.",
        100.0,
    )
    c_bd = get_or_create_curso(
        "Base de Datos",
        "Modelado, SQL básico y consultas.",
        120.0,
    )
    c_html = get_or_create_curso(
        "Desarrollo Web con HTML, CSS y Bootstrap",
        "Fundamentos del desarrollo web y maquetación con Bootstrap 5.",
        150.0,
    )
    c_ux = get_or_create_curso(
        "Introducción a UX/UI y Diseño Centrado en el Usuario",
        "Heurísticas, investigación de usuarios, prototipos y wireframes.",
        130.0,
    )
    c_java = get_or_create_curso(
        "Java Essentials — Fundamentos del Lenguaje",
        "Sintaxis básica, clases, herencia y manejo de excepciones.",
        150.0,
    )
    c_csharp = get_or_create_curso(
        "C# Avanzado",
        "Características avanzadas de C# y LINQ.",
        555.0,
    )
    c_mariadb = get_or_create_curso(
        "MariaDB / MySQL",
        "Administración básica de bases de datos relacionales.",
        777.0,
    )
    c_dl = get_or_create_curso(
        "Deep Learning",
        "Introducción a redes neuronales profundas.",
        777.0,
    )
    c_pg = get_or_create_curso(
        "PostgreSQL",
        "Fundamentos de PostgreSQL para aplicaciones productivas.",
        999.0,
    )

    # --- 3) Asignar cursos al profesor demo (para /profesor/stats) ---
    prof = User.query.filter_by(username="prof").first()
    if prof:
        for c in [
            c_prog1,
            c_bd,
            c_html,
            c_ux,
            c_java,
            c_csharp,
            c_mariadb,
            c_dl,
            c_pg,
        ]:
            if c.teacher_id is None:
                c.teacher_id = prof.id
        db.session.commit()
        print(f"Seed stats -> cursos asignados al profesor {prof.username}")
    else:
        print("Seed stats -> no se encontró usuario 'prof'; cursos sin teacher_id")

    # --- 4) Inscripciones demo para alimentar TODOS los gráficos ---
    demo_ins = [
        # alumno_demo en cursos web/UX/java
        Enrollment(
            user_id=alumnos["alumno_demo"].id,
            course_id=c_html.id,
            status="entregado",
            nota=8.0,
            created_at=days_ago(12),
        ),
        Enrollment(
            user_id=alumnos["alumno_demo"].id,
            course_id=c_ux.id,
            status="entregado",
            nota=10.0,
            created_at=days_ago(9),
        ),
        Enrollment(
            user_id=alumnos["alumno_demo"].id,
            course_id=c_java.id,
            status="entregado",
            nota=8.5,
            created_at=days_ago(5),
        ),
        # alumno_ux en Programación 1, C#, Deep Learning
        Enrollment(
            user_id=alumnos["alumno_ux"].id,
            course_id=c_prog1.id,
            status="vencido",
            nota=None,
            created_at=days_ago(7),
        ),
        Enrollment(
            user_id=alumnos["alumno_ux"].id,
            course_id=c_csharp.id,
            status="entregado",
            nota=9.0,
            created_at=days_ago(6),
        ),
        Enrollment(
            user_id=alumnos["alumno_ux"].id,
            course_id=c_dl.id,
            status="pendiente",
            nota=None,
            created_at=days_ago(2),
        ),
        # alumno_data en BD, MariaDB/MySQL, PostgreSQL
        Enrollment(
            user_id=alumnos["alumno_data"].id,
            course_id=c_bd.id,
            status="entregado",
            nota=8.0,
            created_at=days_ago(10),
        ),
        Enrollment(
            user_id=alumnos["alumno_data"].id,
            course_id=c_mariadb.id,
            status="entregado",
            nota=9.0,
            created_at=days_ago(4),
        ),
        Enrollment(
            user_id=alumnos["alumno_data"].id,
            course_id=c_pg.id,
            status="pendiente",
            nota=None,
            created_at=days_ago(1),
        ),
    ]

    db.session.add_all(demo_ins)
    db.session.commit()
    print("Seed stats -> creadas inscripciones demo")