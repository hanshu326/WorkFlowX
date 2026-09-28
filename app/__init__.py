from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect


db = SQLAlchemy()
csrf = CSRFProtect()


def create_app():

    app = Flask(__name__)

    app.config.from_object("config.Config")

    db.init_app(app)
    csrf.init_app(app)

    from app.routes import main
    app.register_blueprint(main)

    from app.auth import auth
    app.register_blueprint(auth)

    return app