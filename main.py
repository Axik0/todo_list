from flask import Flask, render_template, request, url_for, jsonify, redirect, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length

from datetime import date
from flask_bootstrap import Bootstrap

from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donz'
Bootstrap(app)

##Connect to Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafes.db'
# this has to be turned off to prevent flask-sqlalchemy framework from tracking events and save resources
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# I have to create this key to use CSRF protection for form
db = SQLAlchemy(app)

# bi-directional one-to-many relationship
class User(UserMixin, db.Model):
    __tablename__ = "users"
    # base class to inherit when we create our db entities
    user_id = db.Column(db.Integer, primary_key=True)
    u_date = db.Column(db.Date, default=date.today())
    name = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)

    lists = relationship("List", back_populates="author")


class List(db.Model):
    __tablename__ = "lists"
    list_id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    l_date = db.Column(db.Date, default=date.today())
    body = db.Column(db.Text(), nullable=False)

    author = relationship("User", back_populates="lists")

# list = {priority_id: task}

# @app.before_first_request
# def before_first_request():
#     db.create_all()


class LoginForm(FlaskForm):
    username = StringField(label='Username', validators=[DataRequired(), Length(min=1, max=30)])
    password = PasswordField(label='Password', validators=[DataRequired(), Length(min=1, max=30)])
    submit = SubmitField('Submit')



@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    # check if it's a valid POST request
    if form.validate_on_submit():
        r_user_name = request.form.get('name_f')
        r_user_password = request.form.get('location_f')
        try:
            result = db.session.query(User).filter_by(username=r_user_name).first()
            if result.password == r_user_password:
                return redirect(url_for('index'))
            else:
                return jsonify(response={"error": "Couldn't find such a user. "})
        except:
            return jsonify(response={"error": "Couldn't find such a user. "})
    else:
        return render_template("login.html", form=form)


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = LoginForm()
    # check if it's a valid POST request
    if form.validate_on_submit():
        new_user = User()
        new_user.name = request.form.get('name_f')
        new_user.password = request.form.get('location_f')
        try:
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('index'))
        except:
            return jsonify(response={"error": "Couldn't add user to the database. "})
    else:
        return render_template("login.html", form=form)


if __name__ == '__main__':
    app.run()
# debug=True