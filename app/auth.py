from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

from app import db
from app.models import User


auth = Blueprint("auth", __name__)


 
@auth.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not name or not email or not password:
            flash("Name, email and password are required.")
            return render_template("register.html")

        existing_user = User.query.filter_by(
            email=email
        ).first()

        if existing_user:
            flash("Email already registered.")
            return render_template("register.html")

        hashed_password = generate_password_hash(password)

        user = User(
            name=name,
            email=email,
            password=hashed_password,
            role="employee"
        )

        db.session.add(user)
        db.session.commit()

        flash("Registration successful. Please login.")

        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "register.html"
    )


@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:
            flash("Email and password are required.")
            return render_template("login.html")

        user = User.query.filter_by(
            email=email
        ).first()

        if user and check_password_hash(
            user.password,
            password
        ):

            session["user_id"] = user.id
            session["user_name"] = user.name
            session["role"] = str(user.role).strip().lower()

            return redirect(
                url_for("main.dashboard")
            )

        flash("Invalid email or password.")

    return render_template(
        "login.html"
    )
@auth.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))



 

 