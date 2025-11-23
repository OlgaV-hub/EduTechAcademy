# courses/routes.py
from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, current_app
)
from flask_login import login_required, current_user
from services.s3 import subir_imagen_curso

courses_bp = Blueprint("courses", __name__)

@courses_bp.route("/cursos")
def listar_cursos():
    """Публичный список курсов (для незалогиненных и всех ролей)."""
    Course = current_app.Course
    cursos = Course.query.all()
    return render_template("cursos.html", cursos=cursos)

@courses_bp.route("/cursos/<int:course_id>")
@login_required
def detalle_curso(course_id):
    Course = current_app.Course
    curso = Course.query.get_or_404(course_id)

    return render_template(
        "curso_detalle.html",
        curso=curso,
        converted=None,
        error=None,
        moneda=None,
        amount=None,
    )

@courses_bp.route("/cursos/<int:course_id>/convert", methods=["POST"])
@login_required
def convertir_precio(course_id):
    Course = current_app.Course
    convertir = current_app.convertir_monto_desde_usd

    curso = Course.query.get_or_404(course_id)

    amount_str = request.form.get("amount", "").strip()
    moneda = request.form.get("to", "ARS").upper()

    try:
        amount = float(amount_str)
    except ValueError:
        amount = 0.0

    converted, error = convertir(amount, moneda)

    return render_template(
        "curso_detalle.html",
        curso=curso,
        converted=converted,
        error=error,
        moneda=moneda,
        amount=amount,
    )

@courses_bp.route("/form_curso")
@login_required
def form_curso():
    # Только проф / админ могут создавать курсы
    if current_user.role not in ("profesor", "admin"):
        return render_template("403.html"), 403

    # Какой макет использовать
    if current_user.role == "profesor":
        panel_template = "profesor.html"
        panel = "profesor"
    else:  # admin
        panel_template = "admin.html"
        panel = "admin"

    return render_template(
        "form_curso.html",
        panel_template=panel_template,  # <- имя макета
        panel=panel,                    # 'profesor' или 'admin'
        active="agregar_curso",         # подсветка пункта меню
        curso=None                      # форма "создать", не "редактировать"
    )

@courses_bp.route("/agregar_curso", methods=["POST"])
@login_required
def agregar_curso():
    if current_user.role not in ("admin", "profesor"):
        return render_template("403.html"), 403

    db = current_app.db
    Course = current_app.Course

    nombre = (request.form.get("nombre") or "").strip()
    descripcion = (request.form.get("descripcion") or "").strip()

    try:
        precio = float(request.form.get("precio") or 0)
    except ValueError:
        precio = 0

    if not nombre:
        flash("Nombre obligatorio", "warning")
        return redirect(url_for("courses.form_curso"))

    exist = Course.query.filter_by(
        nombre=nombre,
        teacher_id=current_user.id if current_user.role == "profesor" else None
    ).first()
    if exist:
        flash("Curso duplicado", "warning")
        return redirect(url_for("courses.form_curso"))

    file = request.files.get("imagen")
    image_key = subir_imagen_curso(file)

    nuevo = Course(
        nombre=nombre,
        descripcion=descripcion,
        precio=precio,
        teacher_id=current_user.id if current_user.role == "profesor" else None,
        image_key=image_key,
    )
    db.session.add(nuevo)
    db.session.commit()

    flash("Curso creado", "success")
    
    # после commit()
    if current_user.role == "profesor":
        return redirect(url_for("profesor.profesor_todos_cursos"))

    if current_user.role == "admin":
        return redirect(url_for("admin.admin_todos_cursos"))

    # fallback (не должен сработать)
    return redirect(url_for("courses.listar_cursos"))

@courses_bp.route("/curso/<int:course_id>/editar", methods=["GET", "POST"])
@login_required
def editar_curso(course_id):
    db = current_app.db
    Course = current_app.Course

    curso = Course.query.get_or_404(course_id)

    # Права доступа: только admin и profesor
    if current_user.role not in ("admin", "profesor"):
        return render_template("403.html"), 403

    # Профе может редактировать только свои курсы
    if current_user.role == "profesor" and curso.teacher_id != current_user.id:
        return render_template("403.html"), 403

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()
        precio_raw = request.form.get("precio", "0").strip()

        try:
            precio = float(precio_raw) if precio_raw else 0.0
        except ValueError:
            precio = 0.0

        # Проверка на дубликат имени
        dup = Course.query.filter(
            Course.id != curso.id,
            Course.nombre == nombre,
        ).first()
        if dup:
            flash("Nombre duplicado", "warning")
            return redirect(url_for("courses.editar_curso", course_id=curso.id))

        # Обновление изображения (если выбрано)
        file = request.files.get("imagen")
        if file and file.filename:
            new_key = subir_imagen_curso(file)
            if new_key:
                curso.image_key = new_key

        curso.nombre = nombre
        curso.descripcion = descripcion
        curso.precio = precio
        db.session.commit()

        flash("Actualizado", "success")

        # 👉 Редирект по роли, а НЕ на /cursos
        if current_user.role == "profesor":
            return redirect(url_for("profesor.profesor_todos_cursos"))
        if current_user.role == "admin":
            return redirect(url_for("admin.admin_todos_cursos"))
        return redirect(url_for("courses.listar_cursos"))

    # GET: показать форму с нужным layout (чтобы было боковое меню)
    panel = None
    if current_user.role == "profesor":
        panel = "profesor"
    elif current_user.role == "admin":
        panel = "admin"

    return render_template("form_curso.html", curso=curso, panel=panel)

@courses_bp.route("/cursos/<int:course_id>/delete", methods=["POST"])
@login_required
def eliminar_curso(course_id):
    db = current_app.db
    Course = current_app.Course

    curso = Course.query.get_or_404(course_id)

    # Права доступа
    if current_user.role not in ("admin", "profesor"):
        return render_template("403.html"), 403
    if current_user.role == "profesor" and curso.teacher_id != current_user.id:
        return render_template("403.html"), 403

    db.session.delete(curso)
    db.session.commit()
    flash("Curso eliminado", "info")

    # 👉 После удаления возвращаем на панель в зависимости от роли
    if current_user.role == "profesor":
        return redirect(url_for("profesor.profesor_todos_cursos"))
    if current_user.role == "admin":
        return redirect(url_for("admin.admin_todos_cursos"))
    return redirect(url_for("courses.listar_cursos"))

@courses_bp.route("/inscribirme/<int:course_id>", methods=["POST"])
@login_required
def inscribirme(course_id):
    if current_user.role != "estudiante":
        return render_template("403.html"), 403

    db = current_app.db
    Enrollment = current_app.Enrollment
    Course = current_app.Course

    ya = Enrollment.query.filter_by(
        user_id=current_user.id,
        course_id=course_id,
    ).first()
    if ya:
        return redirect(url_for("estudiante.mis_cursos", msg="ya_inscripto"))

    if not Course.query.get(course_id):
        return redirect(url_for("courses.listar_cursos", msg="curso_no_encontrado"))

    insc = Enrollment(
        user_id=current_user.id,
        course_id=course_id,
        status="pendiente",
    )
    db.session.add(insc)
    db.session.commit()

    return redirect(url_for("estudiante.mis_cursos", msg="ok"))
