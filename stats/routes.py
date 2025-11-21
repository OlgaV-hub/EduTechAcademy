# stats/routes.py
import io
import textwrap

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from flask import current_app, render_template, send_file
from flask_login import login_required, current_user

from . import stats_bp


def _get_db_models():
    """
    Достаём db и модели, которые мы повесили на app:
    app.db, app.Course, app.Enrollment.
    """
    db = current_app.db
    Course = current_app.Course
    Enrollment = current_app.Enrollment
    return db, Course, Enrollment


def _fig_to_png(fig):
    """Сохранить фигуру в PNG и вернуть send_file."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    return send_file(buf, mimetype="image/png")


def _solo_admin_o_profesor():
    return current_user.is_authenticated and current_user.role in ("admin", "profesor")


# ---------- ADMIN / PROF: inscripciones ----------

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
        .join(Enrollment, Enrollment.course_id == Course.id)
        .group_by(Course.id, Course.nombre)
    )

    if current_user.role == "profesor":
        q = q.filter(Course.teacher_id == current_user.id)

    rows = q.all()
    if not rows:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)

    df = pd.DataFrame(rows, columns=["curso", "cantidad"])

    etiquetas = []
    for nombre in df["curso"]:
        partes = textwrap.wrap(nombre, width=18)
        etiquetas.append("\n".join(partes))

    fig, ax = plt.subplots(figsize=(7, 4))
    posiciones = range(len(df))
    colores = plt.cm.Pastel1(range(len(df)))
    ax.bar(posiciones, df["cantidad"], color=colores)

    ax.set_title("Inscripciones por curso")
    ax.set_ylabel("Inscripciones")
    ax.set_xlabel("Curso")

    ax.set_xticks(list(posiciones))
    ax.set_xticklabels(etiquetas, rotation=0, ha="center")
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    fig.tight_layout()
    return _fig_to_png(fig)


# ---------- ADMIN / PROF: notas ----------

@stats_bp.route("/admin/stats/notas.png")
@login_required
def admin_notas_png():
    if not _solo_admin_o_profesor():
        return "Acceso denegado", 403

    db, Course, Enrollment = _get_db_models()

    q = (
        db.session.query(
            Course.nombre.label("curso"),
            db.func.avg(Enrollment.nota).label("nota_promedio"),
        )
        .join(Enrollment, Enrollment.course_id == Course.id)
        .filter(Enrollment.nota != None)  # noqa: E711
        .group_by(Course.id, Course.nombre)
    )

    if current_user.role == "profesor":
        q = q.filter(Course.teacher_id == current_user.id)

    rows = q.all()
    if not rows:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)

    df = pd.DataFrame(rows, columns=["curso", "nota"])

    etiquetas = []
    for nombre in df["curso"]:
        partes = textwrap.wrap(nombre, width=18)
        etiquetas.append("\n".join(partes))

    fig, ax = plt.subplots(figsize=(7, 4))
    posiciones = range(len(df))
    colores = plt.cm.Set2(range(len(df)))
    ax.bar(posiciones, df["nota"], color=colores)

    ax.set_title("Notas promedio por curso")
    ax.set_ylabel("Nota promedio")
    ax.set_xlabel("Curso")

    ax.set_xticks(list(posiciones))
    ax.set_xticklabels(etiquetas, rotation=0, ha="center")
    ax.set_ylim(0, 10)
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    fig.tight_layout()
    return _fig_to_png(fig)


# ---------- ADMIN / PROF: actividad (inscripciones por fecha) ----------

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
        q = (
            q.join(Course, Enrollment.course_id == Course.id)
             .filter(Course.teacher_id == current_user.id)
        )

    q = q.group_by(db.func.date(Enrollment.created_at)).order_by(
        db.func.date(Enrollment.created_at)
    )

    rows = q.all()
    if not rows:
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)

    df = pd.DataFrame(rows, columns=["fecha", "cantidad"])

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(df["fecha"], df["cantidad"], marker="o")

    ax.set_title("Actividad de inscripciones por fecha")
    ax.set_ylabel("Inscripciones")
    ax.set_xlabel("Fecha")

    ax.grid(True, linestyle="--", alpha=0.3)
    fig.autofmt_xdate()
    fig.tight_layout()

    return _fig_to_png(fig)


# ---------- ADMIN / PROF: страница с тремя графиками ----------

@stats_bp.route("/admin/stats")
@login_required
def admin_stats_page():
    if not _solo_admin_o_profesor():
        return "Acceso denegado", 403
    return render_template("admin_stats.html", active="stats")


@stats_bp.route("/profesor/stats")
@login_required
def profesor_stats_page():
    return admin_stats_page()


# ---------- ESTUDIANTE: notas ----------

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
        fig, ax = plt.subplots(figsize=(5, 3))
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)

    df = pd.DataFrame(rows, columns=["curso", "nota"])
    df_group = df.groupby("curso")["nota"].mean().reset_index()

    etiquetas = [textwrap.fill(nombre, width=18) for nombre in df_group["curso"]]

    fig, ax = plt.subplots(figsize=(6, 4))
    colors = plt.cm.Set2(range(len(df_group)))
    ax.bar(etiquetas, df_group["nota"], color=colors)

    ax.set_title("Notas por curso")
    ax.set_ylabel("Nota promedio")
    ax.set_xlabel("Curso")

    ax.tick_params(axis="x", labelrotation=0)
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    fig.tight_layout()
    return _fig_to_png(fig)


# ---------- ESTUDIANTE: estado entregas ----------

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
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, "Sin datos", ha="center", va="center")
        ax.axis("off")
        return _fig_to_png(fig)

    df = pd.DataFrame(rows, columns=["estado", "cantidad"])

    fig, ax = plt.subplots(figsize=(5, 4))
    colors = plt.cm.Pastel2(range(len(df)))
    ax.bar(df["estado"], df["cantidad"], color=colors)

    ax.set_title("Estado de entregas")
    ax.set_ylabel("Cantidad")
    ax.set_xlabel("Estado")

    ax.set_xticklabels(df["estado"], rotation=0)
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    fig.tight_layout()
    return _fig_to_png(fig)


# ---------- ESTUDIANTE: страница «Mi estadística» ----------

@stats_bp.route("/estudiante/stats")
@login_required
def estudiante_stats_page():
    if current_user.role != "estudiante":
        return "Acceso denegado", 403
    return render_template("estudiante_stats.html", active="mi_stats")