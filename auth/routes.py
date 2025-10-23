# auth/routes.py
# import os
# from flask import Blueprint, url_for, session, redirect
# from authlib.integrations.flask_client import OAuth

# auth_bp = Blueprint("auth", __name__)
# oauth = OAuth()

# # Регистрируем провайдера Google по OIDC (well-known)
# google = oauth.register(
#     name="google",
#     client_id=os.getenv("GOOGLE_CLIENT_ID"),
#     client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
#     server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
#     client_kwargs={"scope": "openid email profile"},
# )

# @auth_bp.route("/login")
# def login():
#     redirect_uri = url_for("auth.authorize", _external=True)
#     return google.authorize_redirect(redirect_uri)

# @auth_bp.route("/authorize")
# def authorize():
#     token = google.authorize_access_token()  # обмен кода на токен
#     user_info = google.userinfo()            # профе делал google.userinfo()

#     # Сохраняем компактно в сессию (как показывал профе)
#     session["guser"] = {
#         "id": user_info["sub"],
#         "name": user_info.get("name"),
#         "email": user_info.get("email"),
#     }

#     # Импорт здесь, чтобы избежать циклов импорта
#     from flask_login import login_user
#     from app import GUser  # временный in-memory пользователь по образцу профе

#     g = GUser(session["guser"]["id"], session["guser"]["name"], session["guser"]["email"])
#     login_user(g)  # теперь login_required будет пропускать

#     return redirect(url_for("estudiante_panel")) 

import os
from flask import Blueprint, url_for, session, redirect
from authlib.integrations.flask_client import OAuth

auth_bp = Blueprint("auth", __name__)
oauth = OAuth()

google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@auth_bp.route("/login")
def login():
    redirect_uri = url_for("auth.authorize", _external=True)
    return google.authorize_redirect(redirect_uri, prompt="select_account")

@auth_bp.route("/authorize")
def authorize():
    token = google.authorize_access_token()
    user_info = google.userinfo()

    # сохраняем кратко в сессию + роль
    session["user"] = {
        "id": user_info["sub"],
        "name": user_info.get("name"),
        "email": user_info.get("email"),
        "role": "estudiante",   # как у профе
    }

    from flask_login import login_user
    from app import GUser

    u = GUser(
        user_info["sub"],
        user_info.get("name"),
        user_info.get("email"),
        role="estudiante",
    )
    login_user(u)

    return _redirect_by_role("estudiante")
    
from flask import redirect, url_for

def _redirect_by_role(role: str):
    if role == "admin":
        return redirect(url_for("admin_panel"))
    if role == "profesor":
        return redirect(url_for("profesor_panel"))
    return redirect(url_for("estudiante_panel"))