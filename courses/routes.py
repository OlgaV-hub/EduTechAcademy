# courses/routes.py
from flask import (
    Blueprint, render_template, redirect, url_for,
    request, flash, current_app
)
from flask_login import login_required, current_user
from services.s3 import subir_imagen_curso

courses_bp = Blueprint("courses", __name__)


@courses_bp.route("/cursos")
@login_required
def listar_cursos():
    Course = current_app.Course

    if current_user.role == "admin":
        cursos = Course.query.all()
    elif current_user.role == "profesor":
        cursos = Course.query.filter_by(teacher_id=current_user.id).all()
    else:
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
    if current_user.role not in ("profesor", "admin"):
        return render_template("403.html"), 403
    return render_template("form_curso.html")


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
    return redirect(url_for("courses.listar_cursos"))


@courses_bp.route("/cursos/<int:course_id>/edit", methods=["GET", "POST"])
@login_required
def editar_curso(course_id):
    db = current_app.db
    Course = current_app.Course

    curso = Course.query.get_or_404(course_id)

    if current_user.role not in ("admin", "profesor"):
        return render_template("403.html"), 403
    if current_user.role == "profesor" and curso.teacher_id != current_user.id:
        return render_template("403.html"), 403

    if request.method == "POST":
        nombre = (request.form.get("nombre") or "").strip()
        descripcion = (request.form.get("descripcion") or "").strip()

        try:
            precio = float(request.form.get("precio") or 0)
        except ValueError:
            precio = 0

        dup = Course.query.filter(
            Course.id != curso.id,
            Course.teacher_id == curso.teacher_id,
            Course.nombre == nombre,
        ).first()
        if dup:
            flash("Nombre duplicado", "warning")
            return redirect(url_for("courses.editar_curso", course_id=curso.id))

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
        return redirect(url_for("courses.listar_cursos"))

    return render_template("form_curso.html", curso=curso)


@courses_bp.route("/cursos/<int:course_id>/delete", methods=["POST"])
@login_required
def eliminar_curso(course_id):
    db = current_app.db
    Course = current_app.Course

    curso = Course.query.get_or_404(course_id)

    if current_user.role not in ("admin", "profesor"):
        return render_template("403.html"), 403
    if current_user.role == "profesor" and curso.teacher_id != current_user.id:
        return render_template("403.html"), 403

    db.session.delete(curso)
    db.session.commit()
    flash("Curso eliminado", "info")
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