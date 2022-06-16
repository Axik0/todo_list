from flask import Flask, render_template, request, url_for, flash, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length

from flask_bootstrap import Bootstrap

from flask_login import UserMixin, login_user, logout_user, LoginManager, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from datetime import date

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzz'
Bootstrap(app)

# login manager initialisation
login_manager = LoginManager()
login_manager.init_app(app)


##Connect to Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafes.db'
# this has to be turned off to prevent flask-sqlalchemy framework from tracking events and save resources
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# I have to create this key to use CSRF protection for form
db = SQLAlchemy(app)

# bi-directional one-to-many relationship
class User(UserMixin, db.Model):
    # Usermixin contains some important methods for our User
    # base class to inherit when we create our db entities
    __tablename__ = "users"
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


# @app.before_first_request
# def before_first_request():
#     db.create_all()

# callback that returns User object by id
@login_manager.user_loader
def load_user(user_id):
    return db.session.query(User).get(int(user_id))


class LoginForm(FlaskForm):
    username_f = StringField(label='Username', validators=[DataRequired(), Length(min=1, max=30)])
    password_f = PasswordField(label='Password', validators=[DataRequired(), Length(min=1, max=30)])
    submit_f = SubmitField('Submit')


@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    # check if it's a valid POST request
    if form.validate_on_submit():
        r_user_name = request.form.get('username_f')
        r_user_password = request.form.get('location_f')
        try:
            result = db.session.query(User).filter_by(username=r_user_name).first()
            if check_password_hash(result.password, r_user_password):
                login_user(result)
                flash('You were successfully logged in')
                return redirect(url_for('index'))
            else:
                flash('Wrong password')
                return redirect(url_for('login'))
        except:
            flash('User with that e-mail not found.')
            return redirect(url_for('login'))
    else:
        return render_template("login.html", form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route("/register", methods=['GET', 'POST'])
def register():
    form = LoginForm()
    if form.validate_on_submit():
        name = request.form.get('name_f')
        password = request.form.get('password_f')
        check_presence = db.session.query(User).filter_by(username=name).first()
        if check_presence:
            flash('User with that email already exists')
            return redirect(url_for('register'))
        else:
            try:
                new_user = User()
                new_user.name = name
                hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
                new_user.password = hashed_password
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                flash('You were successfully logged in')
                return redirect(url_for('index'))
            except:
                flash("Couldn't add the user to the database")
                return redirect(url_for('register'))
    else:
        return render_template("register.html", form=form)


@app.route("/")
def index():
    return render_template("index.html")

# @app.route("/create_list")
# def create_list():
#     # list = {priority_id: task}?
#     # list = []
#     # list.append(task)
#     return render_template("register.html", form=form)

# @app.route("/add")
# def create_list():
#     return render_template("add.html")


class TaskForm(FlaskForm):
    task_f = StringField(label='Task')
    submit_f = SubmitField('Submit')

tdl = []
list_name = None

@app.route("/add", methods=['GET', 'POST'])
def add_task():
    global tdl, list_name
    task_to_edit = None
    rename = None
    if request.method == 'POST':
        # this response allows us to catch list's name
        action_pre = request.form.get('action0')
        # this response happens each time we add a task to the list, save the list or delete that
        action = request.form.get('action')
        # this response provides task_id to edit
        action_task = request.form.get('action2')
        # this response provides updated data for some task_id
        action_edit_task = request.form.get('action3')
        # this response brings new name for the list of tasks
        action_edit_name = request.form.get('action4')
        if action_pre == 'Create':
            if not list_name:
                list_name = request.form.get('name')
            print(list_name)
        elif action == 'Rename':
            flash("Rename", "info")
            rename = True
        elif action_edit_name == 'Confirm':
            flash(f"List {list_name} has been renamed.", "info")
            list_name = request.form.get('new_list_name')
        elif action == 'Add':
            task = request.form.get('task_f')
            if task:
                priority = request.form.get('priority_f')
                if [task, priority] not in tdl:
                    tdl.append([task, priority])
                else:
                    flash("This task already exists.", "error")
            else:
                flash("Please type a task.", "error")
        elif action == 'Delete' and tdl:
            tdl = []
            list_name = None
            flash("List has been deleted.", "info")
            return redirect(url_for('add_task'))
        elif action == 'Save' and tdl:
            flash(f"List {list_name} has been saved.", "info")
            print(tdl, list_name)
            return redirect(url_for('show_list'))
        elif action_task == 'Edit' and tdl:
            # the task_id has been received, ready to process, transfer old values to the template
            task_to_edit_id = int(request.form.get('task_id'))
            task_to_edit = [task_to_edit_id, tdl[task_to_edit_id]]
        elif action_edit_task == 'Confirm':
            # the task has been updated, renew it in the list
            edited_task_id = int(request.form.get('task_idf3'))
            updated_task_text = request.form.get('task_f3')
            updated_task_priority = request.form.get('priority_f3')
            tdl[edited_task_id] = [updated_task_text, updated_task_priority]
            flash("Edited", "info")
            task_to_edit = None
        elif action_task == 'Delete' and tdl:
            task_to_delete = int(request.form.get('task_id'))
            tdl.pop(task_to_delete)
        else:
            flash("Nothing to save/delete yet.", "error")
        return render_template("add.html", tdl=tdl, name=list_name, task=task_to_edit, rename=rename)
    else:
        return render_template("add.html", tdl=tdl, name=list_name)


@app.route("/list", methods=['GET', 'POST'])
def show_list():
    global tdl, list_name
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'Confirm':
            # save to database
            flash("Your list has been saved to the database.", "info")
            return redirect(url_for('index'))
        elif action == 'Edit':
            flash("Edit your list again.", "info")
            return redirect(url_for('add_task'))
        elif action == 'Delete':
            flash("Your list has been deleted.", "info")
            # check database, delete if present
            return redirect(url_for('index'))
    else:
        if tdl and list_name:
            return render_template("list.html", tdl=tdl, name=list_name)
        else:
            flash("Nothing here yet, first create a list. ", "error")
            return redirect(url_for('add_task'))

if __name__ == '__main__':
    app.run()
# debug=True
