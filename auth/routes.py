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
    from flask import current_app

    try:
        # 1) Получаем токен и данные пользователя
        token = google.authorize_access_token()
        user_info = google.userinfo()
    except Exception as e:
        # Если не можем достучаться до Google (как сейчас) —
        # покажем понятную ошибку и вернем на /login.
        flash("No se pudo conectar con Google. Intenta nuevamente más tarde.", "danger")
        return redirect(url_for("login"))

    app = current_app._get_current_object()
    user, error = app.login_or_register_google_user(user_info)

    if error:
        flash(error, "danger")
        return redirect(url_for("login"))

    login_user(user)
    session["google_profile"] = {
        "id": user_info.get("sub"),
        "name": user_info.get("name"),
        "email": user_info.get("email"),
    }

    return app.redirect_by_role(user.role)