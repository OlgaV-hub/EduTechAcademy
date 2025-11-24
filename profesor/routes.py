# profesor/routes.py
from flask import (
    Blueprint, render_template, redirect,
    url_for, request, flash, current_app
)
from flask_login import login_required, current_user

profesor_bp = Blueprint("profesor", __name__)


@profesor_bp.route("/profesor")
@login_required
def profesor_panel():
    if current_user.role != "profesor":
        return render_template("403.html"), 403
    return render_template("profesor.html")


# ---------- Mis cursos ----------

@profesor_bp.route("/profesor/mis-cursos")
@login_required
def profesor_mis_cursos():
    if current_user.role != "profesor":
        return render_template("403.html"), 403

    Course = current_app.Course
    cursos = Course.query.filter_by(teacher_id=current_user.id).all()

    return render_template(
        "cursos.html",
        cursos=cursos,
        panel="profesor",
        titulo="Mis cursos",
        active="mis_cursos",
    )


# ---------- Todos los cursos ----------

@profesor_bp.route("/profesor/todos-cursos")
@login_required
def profesor_todos_cursos():
    if current_user.role != "profesor":
        return render_template("403.html"), 403

    Course = current_app.Course
    cursos = Course.query.all()

    return render_template(
        "cursos.html",
        cursos=cursos,
        panel="profesor",
        titulo="Todos los cursos",
        active="todos_cursos",
    )


# ---------- Calificaciones ----------

@profesor_bp.route("/profesor/calificaciones")
@login_required
def profesor_calificaciones():
    if current_user.role != "profesor":
        return render_template("403.html"), 403

    db = current_app.db
    Course = current_app.Course
    Enrollment = current_app.Enrollment
    User = current_app.User

    filas = (
        db.session.query(Enrollment, Course, User)
        .join(Course, Enrollment.course_id == Course.id)
        .join(User, Enrollment.user_id == User.id)
        .order_by(Course.nombre.asc(), User.username.asc())
        .all()
    )

    return render_template(
        "profesor_calificaciones.html",
        filas=filas,
        active="calificaciones",
    )


# ---------- Edición de inscripciones por un curso ----------

@profesor_bp.route(
    "/profesor/curso/<int:course_id>/inscripciones",
    methods=["GET", "POST"],
)
@login_required
def gestionar_inscripciones_curso(course_id):
    if current_user.role != "profesor":
        return render_template("403.html"), 403

    db = current_app.db
    Course = current_app.Course
    Enrollment = current_app.Enrollment
    User = current_app.User

    curso = Course.query.get_or_404(course_id)

    if request.method == "POST":
        enroll_id_str = request.form.get("enrollment_id", "").strip()
        status = (request.form.get("status") or "").strip()
        nota_str = (request.form.get("nota") or "").strip()

        try:
            enroll_id = int(enroll_id_str)
        except ValueError:
            flash("ID de inscripción inválido.", "warning")
            return redirect(url_for("profesor.gestionar_inscripciones_curso",
                                    course_id=course_id))

        insc = Enrollment.query.get(enroll_id)
        if not insc or insc.course_id != course_id:
            flash("Inscripción no encontrada.", "warning")
            return redirect(url_for("profesor.gestionar_inscripciones_curso",
                                    course_id=course_id))

        allowed_status = ("pendiente", "entregado", "vencido")
        if status in allowed_status:
            insc.status = status

        if nota_str == "":
            insc.nota = None
        else:
            try:
                insc.nota = float(nota_str)
            except ValueError:
                flash("La nota debe ser numérica.", "warning")

        db.session.commit()
        flash("Actualizado", "success")
        return redirect(url_for("profesor.gestionar_inscripciones_curso",
                                course_id=course_id))

    inscripciones = (
        db.session.query(Enrollment, User)
        .join(User, User.id == Enrollment.user_id)
        .filter(Enrollment.course_id == course_id)
        .all()
    )

    return render_template(
        "profesor_inscripciones.html",
        curso=curso,
        inscripciones=inscripciones,
        active="mis_cursos",  
        solo_lectura=False     
    )
