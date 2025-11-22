# estudiante/routes.py
from flask import Blueprint, render_template, current_app, request
from flask_login import login_required, current_user

estudiante_bp = Blueprint("estudiante", __name__)


@estudiante_bp.route("/estudiante")
@login_required
def estudiante_panel():
    if current_user.role != "estudiante":
        return render_template("403.html"), 403

    msg = request.args.get("msg")
    return render_template(
        "estudiante.html",
        active="inicio",
        cursos=[],
        msg=msg,
    )


@estudiante_bp.route("/mis-cursos")
@login_required
def mis_cursos():
    if current_user.role != "estudiante":
        return render_template("403.html"), 403

    Enrollment = current_app.Enrollment
    Course = current_app.Course

    inscripciones = Enrollment.query.filter_by(user_id=current_user.id).all()
    cursos_ids = [i.course_id for i in inscripciones]
    cursos = Course.query.filter(Course.id.in_(cursos_ids)).all() if cursos_ids else []

    msg = request.args.get("msg")
    return render_template(
        "estudiante.html",
        cursos=cursos,
        msg=msg,
        active="mis_cursos",
    )


@estudiante_bp.route("/estudiante/cursos")
@login_required
def estudiante_todos_cursos():
    if current_user.role != "estudiante":
        return render_template("403.html"), 403

    Course = current_app.Course
    cursos = Course.query.all()

    msg = request.args.get("msg")

    return render_template(
        "estudiante.html",
        cursos=cursos,
        msg=msg,
        active="todos_cursos",
    )