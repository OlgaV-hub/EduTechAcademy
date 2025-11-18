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
from flask import Blueprint, url_for, session, redirect, flash
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
    from flask_login import login_user
    # импортируем хелперы из App.py, НО не лезем к db напрямую
    from flask import current_app

    # 1. Получаем токен и данные пользователя у Google
    token = google.authorize_access_token()
    user_info = google.userinfo()

    # 2. Пытаемся найти/создать пользователя в нашей БД
    #    Берём функцию с главного приложения через current_app,
    #    а не через import app (чтобы не создавалась вторая копия приложения)
    app = current_app._get_current_object()
    user, error = app.login_or_register_google_user(user_info)

    if error:
        flash(error, "danger")
        return redirect(url_for("login"))

    # 3. Логиним как обычного пользователя Flask-Login
    login_user(user)

    # 4. (опционально) сохраняем профиль Google в сессию
    session["google_profile"] = {
        "id": user_info.get("sub"),
        "name": user_info.get("name"),
        "email": user_info.get("email"),
    }

    # 5. Редирект по роли, как в обычном логине
    return app.redirect_by_role(user.role)

def _redirect_by_role(role: str):
    if role == "admin":
        return redirect(url_for("admin_panel"))
    if role == "profesor":
        return redirect(url_for("profesor_panel"))
    return redirect(url_for("estudiante_panel"))