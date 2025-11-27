# stats/routes.py

import io
import textwrap

import matplotlib
matplotlib.use("Agg")  
import matplotlib.pyplot as plt
import pandas as pd

from flask import current_app, render_template, send_file
from flask_login import login_required, current_user


from . import stats_bp


# =========================
# Helpers
# =========================

def _solo_admin_o_profesor() -> bool:
    return current_user.is_authenticated and current_user.role in ("admin", "profesor")


def _get_db_models():
    """Devuelve db, Course, Enrollment guardados en app.py."""
    db = current_app.db
    Course = current_app.Course
    Enrollment = current_app.Enrollment
    return db, Course, Enrollment


def _fig_to_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


def _fig_sin_datos(msg="Sin datos"):
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, msg, ha="center", va="center")
    ax.axis("off")
    return _fig_to_png(fig)


# =========================
# ADMIN / PROFESOR  (gráficos)
# =========================

@stats_bp.route("/admin/stats/inscripciones.png")
@login_required
def admin_inscripciones_png():
    if not _solo_admin_o_profesor():
        return "Acceso denegado", 403

    db, Course, Enrollment = _get_db_models()

    q = (
        db.session.query(
            Course.nombre.label("curso"),
            db.func.count(Enrollment.id).label("cantidad"),
        )
        .join(Course, Enrollment.course_id == Course.id)
    )

    # admin -> todos los cursos
    # profesor -> solo sus cursos
    if current_user.role == "profesor":
        q = q.filter(Course.teacher_id == current_user.id)

    q = q.group_by(Course.nombre).order_by(Course.nombre)
    rows = q.all()
    if not rows:
        return _fig_sin_datos()

    df = pd.DataFrame(rows, columns=["curso", "cantidad"])

 
    etiquetas = [textwrap.fill(nombre, width=18) for nombre in df["curso"]]

    fig, ax = plt.subplots(figsize=(9, 4))
    x = range(len(df))
    colors = plt.cm.Set3(range(len(df)))

    ax.bar(x, df["cantidad"], color=colors)
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas, rotation=20, ha="right")

    ax.set_title("Inscripciones por curso")
    ax.set_ylabel("Inscripciones")
    ax.set_xlabel("Curso")
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    fig.tight_layout()
    return _fig_to_png(fig)


@stats_bp.route("/admin/stats/notas.png")
@login_required
def admin_notas_png():
    if not _solo_admin_o_profesor():
        return "Acceso denegado", 403

    db, Course, Enrollment = _get_db_models()

    q = (
        db.session.query(
            Course.nombre.label("curso"),
            Enrollment.nota.label("nota"),
        )
        .join(Course, Enrollment.course_id == Course.id)
        .filter(Enrollment.nota.isnot(None))
    )

    if current_user.role == "profesor":
        q = q.filter(Course.teacher_id == current_user.id)

    q = q.order_by(Course.nombre)
    rows = q.all()
    if not rows:
        return _fig_sin_datos()

    df = pd.DataFrame(rows, columns=["curso", "nota"])
    df_group = df.groupby("curso")["nota"].mean().reset_index()

    etiquetas = [textwrap.fill(nombre, width=18) for nombre in df_group["curso"]]

    fig, ax = plt.subplots(figsize=(9, 4))
    x = range(len(df_group))
    colors = plt.cm.Set2(range(len(df_group)))

    ax.bar(x, df_group["nota"], color=colors)
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas, rotation=20, ha="right")

    ax.set_title("Notas promedio por curso")
    ax.set_ylabel("Nota promedio")
    ax.set_xlabel("Curso")
    ax.set_ylim(0, 10)
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    fig.tight_layout()
    return _fig_to_png(fig)


@stats_bp.route("/admin/stats/actividad.png")
@login_required
def admin_actividad_png():
    if not _solo_admin_o_profesor():
        return "Acceso denegado", 403

    db, Course, Enrollment = _get_db_models()

    q = db.session.query(
        db.func.date(Enrollment.created_at).label("fecha"),
        db.func.count(Enrollment.id).label("cantidad"),
    )

    if current_user.role == "profesor":
        q = q.join(Course, Enrollment.course_id == Course.id)
        q = q.filter(Course.teacher_id == current_user.id)

    q = q.group_by(db.func.date(Enrollment.created_at)).order_by(
        db.func.date(Enrollment.created_at)
    )

    rows = q.all()
    if not rows:
        return _fig_sin_datos()

    df = pd.DataFrame(rows, columns=["fecha", "cantidad"])

    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(df["fecha"], df["cantidad"], marker="o")

    ax.set_title("Actividad de inscripciones por fecha")
    ax.set_ylabel("Inscripciones")
    ax.set_xlabel("Fecha")
    ax.grid(True, linestyle="--", alpha=0.3)
    fig.autofmt_xdate()

    fig.tight_layout()
    return _fig_to_png(fig)


# =========================
# Páginas HTML admin / profesor
# =========================

@stats_bp.route("/admin/stats")
@login_required
def admin_stats_page():
    if current_user.role != "admin":
        return "Acceso denegado", 403
    return render_template("admin_stats.html", active="stats")


@stats_bp.route("/profesor/stats")
@login_required
def profesor_stats_page():
    if current_user.role != "profesor":
        return "Acceso denegado", 403

    return render_template("admin_stats.html", active="stats")


# =========================
# ESTUDIANTE
# =========================

@stats_bp.route("/estudiante/stats/notas.png")
@login_required
def estudiante_notas_png():
    if current_user.role != "estudiante":
        return "Acceso denegado", 403

    db, Course, Enrollment = _get_db_models()

    q = (
        db.session.query(
            Course.nombre.label("curso"),
            Enrollment.nota.label("nota"),
        )
        .join(Course, Enrollment.course_id == Course.id)
        .filter(
            Enrollment.user_id == current_user.id,
            Enrollment.nota.isnot(None),
        )
    )

    rows = q.all()
    if not rows:
        return _fig_sin_datos()

    df = pd.DataFrame(rows, columns=["curso", "nota"])
    df_group = df.groupby("curso")["nota"].mean().reset_index()

    etiquetas = [textwrap.fill(nombre, width=18) for nombre in df_group["curso"]]

    fig, ax = plt.subplots(figsize=(6, 4))
    x = range(len(df_group))
    colors = plt.cm.Set2(range(len(df_group)))

    ax.bar(x, df_group["nota"], color=colors)
    ax.set_xticks(x)
    ax.set_xticklabels(etiquetas, rotation=20, ha="right")

    ax.set_title("Notas por curso")
    ax.set_ylabel("Nota promedio")
    ax.set_xlabel("Curso")
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    fig.tight_layout()
    return _fig_to_png(fig)


@stats_bp.route("/estudiante/stats/estado_entregas.png")
@login_required
def estudiante_estado_entregas_png():
    if current_user.role != "estudiante":
        return "Acceso denegado", 403

    db, Course, Enrollment = _get_db_models()

    q = (
        db.session.query(
            Enrollment.status.label("estado"),
            db.func.count(Enrollment.id).label("cantidad"),
        )
        .filter(Enrollment.user_id == current_user.id)
        .group_by(Enrollment.status)
    )

    rows = q.all()
    if not rows:
        return _fig_sin_datos()

    df = pd.DataFrame(rows, columns=["estado", "cantidad"])

    fig, ax = plt.subplots(figsize=(5, 4))
    colors = plt.cm.Pastel2(range(len(df)))
    ax.bar(df["estado"], df["cantidad"], color=colors)

    ax.set_title("Estado de entregas")
    ax.set_ylabel("Cantidad")
    ax.set_xlabel("Estado")
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    fig.tight_layout()
    return _fig_to_png(fig)


@stats_bp.route("/estudiante/stats")
@login_required
def estudiante_stats_page():
    if current_user.role != "estudiante":
        return "Acceso denegado", 403
    return render_template("estudiante_stats.html", active="mi_stats")