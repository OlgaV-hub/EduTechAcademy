# admin/routes.py
from flask import (
    Blueprint, render_template, redirect,
    url_for, request, current_app
)
from flask_login import login_required, current_user

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@login_required
def admin_panel():
    if current_user.role != "admin":
        return render_template("403.html"), 403
    return render_template("admin.html")


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

    if user.id == current_user.id:
        return redirect(url_for("admin.admin_users"))

    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("admin.admin_users"))