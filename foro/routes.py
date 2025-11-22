# foro/routes.py
from flask import Blueprint, render_template, current_app

foro_bp = Blueprint("foro", __name__)


@foro_bp.route("/foro")
def ver_foro():
    temas_foro = current_app.temas_foro
    return render_template("foro.html", temas=temas_foro)