# admin/routes.py
# from flask import (
#     Blueprint, render_template, redirect,
#     url_for, request, current_app
# )
# from flask_login import login_required, current_user

# admin_bp = Blueprint("admin", __name__)


# @admin_bp.route("/admin")
# @login_required
# def admin_panel():
#     if current_user.role != "admin":
#         return render_template("403.html"), 403
#     return render_template("admin.html")


# @admin_bp.route("/admin/users")
# @login_required
# def admin_users():
#     if current_user.role != "admin":
#         return render_template("403.html"), 403

#     User = current_app.User
#     users = User.query.all()
#     return render_template("admin_users.html", users=users)


# @admin_bp.route("/admin/users/<int:user_id>/update_role", methods=["POST"])
# @login_required
# def admin_update_user_role(user_id):
#     if current_user.role != "admin":
#         return render_template("403.html"), 403

#     db = current_app.db
#     User = current_app.User

#     new_role = request.form.get("role")
#     user = User.query.get_or_404(user_id)
#     user.role = new_role
#     db.session.commit()

#     return redirect(url_for("admin.admin_users"))


# @admin_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
# @login_required
# def admin_delete_user(user_id):
#     if current_user.role != "admin":
#         return render_template("403.html"), 403

#     db = current_app.db
#     User = current_app.User

#     user = User.query.get_or_404(user_id)

#     if user.id == current_user.id:
#         return redirect(url_for("admin.admin_users"))

#     db.session.delete(user)
#     db.session.commit()
#     return redirect(url_for("admin.admin_users"))

from flask import (
    Blueprint, render_template, redirect,
    url_for, request, current_app
)
from flask_login import login_required, current_user

admin_bp = Blueprint("admin", __name__)


# ---------- Панель администратора (резюме) ----------

@admin_bp.route("/admin")
@login_required
def admin_panel():
    if current_user.role != "admin":
        return render_template("403.html"), 403
    return render_template("admin.html")


# ---------- Gestión de usuarios (CRUD ролей/удаление) ----------

@admin_bp.route("/admin/users")
@login_required
def admin_users():
    if current_user.role != "admin":
        return render_template("403.html"), 403

    User = current_app.User
    users = User.query.all()
    return render_template("admin_users.html", users=users)


@admin_bp.route("/admin/users/<int:user_id>/update_role", methods=["POST"])
@login_required
def admin_update_user_role(user_id):
    if current_user.role != "admin":
        return render_template("403.html"), 403

    db = current_app.db
    User = current_app.User

    new_role = request.form.get("role")
    user = User.query.get_or_404(user_id)
    user.role = new_role
    db.session.commit()

    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
@login_required
def admin_delete_user(user_id):
    if current_user.role != "admin":
        return render_template("403.html"), 403

    db = current_app.db
    User = current_app.User

    user = User.query.get_or_404(user_id)

    # админ не может удалить самого себя
    if user.id == current_user.id:
        return redirect(url_for("admin.admin_users"))

    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("admin.admin_users"))


# =====================================================
#     КУРСЫ ДЛЯ АДМИНА
# =====================================================

# ---------- Mis cursos (курсы, где admin = teacher) ----------

@admin_bp.route("/admin/mis-cursos")
@login_required
def admin_mis_cursos():
    if current_user.role != "admin":
        return render_template("403.html"), 403

    Course = current_app.Course
    cursos = Course.query.filter_by(teacher_id=current_user.id).all()

    return render_template(
        "cursos.html",
        cursos=cursos,
        panel="admin",
        titulo="Mis cursos",
        active="mis_cursos",
    )


# ---------- Todos los cursos (все курсы) ----------

@admin_bp.route("/admin/todos-cursos")
@login_required
def admin_todos_cursos():
    if current_user.role != "admin":
        return render_template("403.html"), 403

    Course = current_app.Course
    cursos = Course.query.all()

    return render_template(
        "cursos.html",
        cursos=cursos,
        panel="admin",
        titulo="Todos los cursos",
        active="todos_cursos",
    )


# ---------- Ver inscripciones (ТОЛЬКО ПРОСМОТР) ----------

@admin_bp.route("/admin/curso/<int:course_id>/inscripciones")
@login_required
def admin_ver_inscripciones_curso(course_id):
    if current_user.role != "admin":
        return render_template("403.html"), 403

    db = current_app.db
    Course = current_app.Course
    Enrollment = current_app.Enrollment
    User = current_app.User

    curso = Course.query.get_or_404(course_id)

    inscripciones = (
        db.session.query(Enrollment, User)
        .join(User, User.id == Enrollment.user_id)
        .filter(Enrollment.course_id == course_id)
        .all()
    )

    # используем тот же шаблон, но в режиме solo_lectura
    return render_template(
        "profesor_inscripciones.html",
        curso=curso,
        inscripciones=inscripciones,
        active="todos_cursos",
        solo_lectura=True,
    )
