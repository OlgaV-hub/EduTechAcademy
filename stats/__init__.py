# stats/__init__.py
from flask import Blueprint

stats_bp = Blueprint("stats", __name__)

# Импортируем маршруты, чтобы они «повесились» на stats_bp
from . import routes  # noqa: E402,F401