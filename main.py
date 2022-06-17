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

user_session_data = {}
DD = [None, None, []]

# for some reason, it doesn't work fine when I use DD
def draft_drop(except_list_id=False):
    """flushes session's draft, completely or with an exception of 0-th item(list_id)"""
    # this condition here to prevent an error when there is no cookie or active session
    #  but someone visits / route, which has this function inside
    # this doesn't matter and has nothing to do with the DD-bug above
    if current_user.is_authenticated:
        global user_session_data
        if except_list_id:
            user_session_data[current_user.id][1] = [None, None, []][1]
            user_session_data[current_user.id][2] = [None, None, []][2]
        else:
            user_session_data[current_user.id] = [None, None, []]



def draft_upd(new_draft):
    """updates session's draft, completely or with an exception of 0-th item(list_id)"""
    global user_session_data
    if new_draft[0]:
        user_session_data[current_user.id] = new_draft
    else:
        user_session_data[current_user.id][1] = new_draft[1]
        user_session_data[current_user.id][2] = new_draft[2]

def draft_get():
    """retrieves the draft"""
    global user_session_data
    # print(current_user, user_session_data)
    return user_session_data[current_user.id]



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
    # has to be called as 'id' in order to accomplish login procedure
    id = db.Column(db.Integer, primary_key=True)
    u_date = db.Column(db.Date, default=date.today())

    user_name = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(20), nullable=False)

    lists = relationship("List", back_populates="author")

    # I just want to return a string with custom printable representation of an object, overrides standard one
    def __repr__(self):
        return f'<User_{self.id}: {self.user_name}>'


class List(db.Model):
    __tablename__ = "lists"
    list_id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    l_date = db.Column(db.Date, default=date.today())

    list_name = db.Column(db.String(200), unique=True, nullable=False)
    body = db.Column(db.PickleType, nullable=False)

    author = db.Column(db.String(250), nullable=False)
    author = relationship("User", back_populates="lists")

    # I just want to return a string with custom printable representation of an object, overrides standard one
    def __repr__(self):
        return f'<Author-{self.author_id}, List-{self.list_id}: {self.body}>'


@app.before_first_request
def before_first_request():
    db.create_all()

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
        r_user_password = request.form.get('password_f')
        try:
            result = db.session.query(User).filter_by(user_name=r_user_name).first()
            if check_password_hash(result.password, r_user_password):
                login_user(result)
                # create/clear draft for this particular user session
                draft_drop()
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
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = LoginForm()
    if form.validate_on_submit():
        name = request.form.get('username_f')
        password = request.form.get('password_f')
        check_presence = db.session.query(User).filter_by(user_name=name).first()
        if check_presence:
            flash('User with that username already exists')
            return redirect(url_for('register'))
        else:
            try:
                hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
                new_user = User(user_name=name, password=hashed_password)
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                # create/clear draft for this particular user session
                draft_drop()
                flash(f'{new_user} You were successfully logged in')
                return redirect(url_for('index'))
            except:
                flash("Couldn't add the user to the database")
                return redirect(url_for('register'))
    else:
        return render_template("register.html", form=form)


@app.route("/")
def index():
    # if someone is logged in, I want to get rid of any unfinished/loaded draft for this user
    draft_drop()

    return render_template("index.html")


@app.route("/add", methods=['GET', 'POST'])
@login_required
def add_task():
    draft = draft_get()
    list_name, tdl = draft[1], draft[2]
    task_to_edit, rename_flag = None, None

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

        # name the list before starting to fill in tasks
        if action_pre == 'Create':
            list_name = request.form.get('name')

        # list rename handler section
        elif action == 'Rename':
            flash("Rename", "info")
            rename_flag = True
        elif action_edit_name == 'Confirm':
            flash(f"List {list_name} has been renamed.", "info")
            list_name = request.form.get('new_list_name')

        # populates newly created list
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

        # delete draft
        elif action == 'Delete' and tdl:
            # check if the draft has already been submitted to db
            if draft_get()[0]:
                try:
                    db.session.query(List).filter_by(list_id=draft[0]).delete()
                    db.session.commit()
                    flash("Your list has been deleted from the database.", "info")
                    draft_drop()
                except:
                    flash("Couldn't find or delete this list, something's wrong.", "error")
            # flush the draft for both scenarios
            draft_drop()
            flash("List has been deleted.", "info")
            return redirect(url_for('get_all'))
        # show draft again before saving to the database
        elif action == 'Save' and tdl:
            flash(f"List {list_name} has been saved.", "info")
            draft_upd([None, list_name, tdl])
            return redirect(url_for('show_list'))

        # edit task handler section
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
        # update the draft with any changes before rendering it
        draft_upd([None, list_name, tdl])
        return render_template("add.html", tdl=tdl, name=list_name, task=task_to_edit, rename=rename_flag)
    else:
        # BUG?
        # draft_drop()
        return render_template("add.html", tdl=tdl, name=list_name)


@app.route("/list", methods=['GET', 'POST'])
@app.route("/lists/<int:list_id>", methods=['GET', 'POST'])
@login_required
def show_list(list_id=None):
    draft = draft_get()
    # print(list_id)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'Confirm':
            # save to database
            if draft[0]:
                # if it was an item from the database, get that outta there and update just its fields
                list_to_update = db.session.query(List).get(draft[0])
                list_to_update.list_name, list_to_update.body = draft[1], draft[2]
                db.session.commit()
                flash("Your list has been updated in the database.", "info")
            else:
                # insert completely new list into the database
                # I suppose that same list_name problem is eliminated at the database level and raises an exception
                try:
                    new_list = List(list_name=draft[1], author=current_user, body=draft[2])
                    db.session.add(new_list)
                    db.session.commit()
                    draft_drop()
                    flash("Your list has been saved to the database.", "info")
                except:
                    flash("List with this name already exists in the database, please rename.", "error")
            return redirect(url_for('get_all'))
        elif action == 'Edit':
            flash("Edit your list again.", "info")
            return redirect(url_for('add_task'))
        elif action == 'Delete':
            if draft[0]:
                # check database, delete if present
                try:
                    db.session.query(List).filter_by(list_id=draft[0]).delete()
                    db.session.commit()
                    flash("Your list has been deleted from the database.", "info")
                    draft_drop()
                except:
                    flash("Couldn't find or delete this list, something's wrong.", "error")
            else:
                # just flush the draft
                draft_drop()
                flash("Your draft has been deleted.", "info")
            return redirect(url_for('get_all'))
    else:
        if list_id is None:
            # this covers case of a new list, created from scratch
            return render_template("list.html", tdl=draft[2], name=draft[1])
        elif list_id:
            # when we open a list from database with an exact id
            query = db.session.query(List).filter_by(author=current_user, list_id=list_id).first()
            draft_upd([query.list_id, query.list_name, query.body])
            return redirect(url_for('show_list'))
        else:
            flash("Nothing here yet, first create a list. ", "error")
            return redirect(url_for('add_task'))



@app.route("/all")
@login_required
def get_all():
    # I want to get rid of any unfinished/loaded draft for this user
    draft_drop()

    query = db.session.query(List).filter_by(author=current_user).all()
    user_lists = [[lst.list_id, lst.list_name, lst.body] for lst in query]
    # user_lists = [['id1', 'listname1', [[1, 2], [2, 1], [3, 3]]], ['id2', 'listname2', [[1, 3], [2, 1], [3, 3]]]]
    return render_template("all.html", lists=user_lists)


if __name__ == '__main__':
    app.run()
# debug=True
