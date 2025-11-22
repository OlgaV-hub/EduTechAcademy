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
    if current_user.role not in ("profesor", "admin"):
        return render_template("403.html"), 403
    return render_template("profesor.html")


@profesor_bp.route(
    "/profesor/curso/<int:course_id>/inscripciones",
    methods=["GET", "POST"],
)
@login_required
def gestionar_inscripciones_curso(course_id):
    if current_user.role not in ("profesor", "admin"):
        return render_template("403.html"), 403

    db = current_app.db
    Course = current_app.Course
    Enrollment = current_app.Enrollment
    User = current_app.User

    curso = Course.query.get_or_404(course_id)

    # profesor → может видеть только свои курсы
    if current_user.role == "profesor" and curso.teacher_id != current_user.id:
        return render_template("403.html"), 403

    if request.method == "POST":
        enroll_id_str = request.form.get("enrollment_id", "").strip()
        status = request.form.get("status", "").strip()
        nota_str = request.form.get("nota", "").strip()

        allowed_status = ["pendiente", "entregado", "vencido"]

        try:
            enroll_id = int(enroll_id_str)
        except ValueError:
            flash("ID inválido.", "warning")
            return redirect(url_for("profesor.gestionar_inscripciones_curso", course_id=course_id))

        insc = Enrollment.query.get_or_404(enroll_id)

        if insc.course_id != curso.id:
            flash("No pertenece a este curso.", "warning")
            return redirect(url_for("profesor.gestionar_inscripciones_curso", course_id=course_id))

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
        return redirect(url_for("profesor.gestionar_inscripciones_curso", course_id=course_id))

    inscripciones = (
        db.session.query(Enrollment, User)
        .join(User, User.id == Enrollment.user_id)
        .filter(Enrollment.course_id == course_id)
        .all()
    )

    return render_template(
        "profesor_inscripciones.html",
        curso=curso,
        inscripciones=inscripciones
    )