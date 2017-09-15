from flask import Flask, g, session, redirect, request, render_template
import os
import re
import scrypt
import sqlite3

import database


DATABASE = 'database.sqlite3'
SALT_LENGTH = 64

app = Flask(__name__)


@app.route('/')
def index():
    if 'email' in session:
        return redirect('/file_management')
    else:
        return redirect('/sign_in?next=/file_management')


@app.route('/sign_in')
def get_sign_in():
    next_url = request.args['next']
    return render_template('sign_in.html', next=next_url)


@app.route('/sign_in', methods=['POST'])
def post_sign_in():
    next_url = request.args['next']
    email = request.form['email']
    password = request.form['password']

    # Check if the fields were filled.
    email_valid = email is not None and email != ''
    email_feedback = 'Please enter your email address'

    password_valid = password is not None and password != ''
    password_feedback = 'Please enter your password'

    # Check if the fields match our simple regex.
    if email_valid:
        email_valid = re.match(r'[^@]+@[^@]+\.[^@]+', email)
        email_feedback = 'The value you’ve entered is not a valid email address'

    if password_valid:
        password_valid = len(password) >= 6
        password_feedback = 'The password you’ve entered is too short to be valid'

    # The rest of the checks involve the DB.
    if email_valid or password_valid:
        ready_db()

    # Check if the user exists in the DB.
    if email_valid:
        email_valid = database.user_exists(email)
        email_feedback = 'The email you’ve entered doesn’t match any account'

    # Check if the password is correct. Do not run this check if the email is incorrect, since we can't tell if the user
    # inputted a correct password or not until they input a correct email.
    if email_valid and password_valid:
        salt, password_hash = database.get_password(email)
        password_valid = password_hash == scrypt.hash(password, salt)
        password_feedback = 'The password you’ve entered is incorrect'

    if email_valid and password_valid:
        # Set the login cookie.
        session['user_id'] = database.get_user_id(email)
        session['email'] = email

        return redirect(next_url)
    else:
        return render_template('sign_in.html',
                               next=next_url,
                               email=email,
                               email_valid=email_valid,
                               email_feedback=email_feedback,
                               password=password,
                               password_valid=password_valid,
                               password_feedback=password_feedback)


@app.route('/sign_up')
def get_sign_up():
    next_url = request.args['next']
    return render_template('sign_up.html', next=next_url)


@app.route('/sign_up', methods=['POST'])
def post_sign_up():
    next_url = request.args['next']
    email = request.form['email']
    password = request.form['password']
    confirmation = request.form['confirmation']

    # Check if the fields were filled.
    email_valid = email is not None and email != ''
    email_feedback = 'Please enter your email address'

    password_valid = password is not None and password != ''
    password_feedback = 'Please enter your password'

    confirmation_valid = confirmation is not None and confirmation != ''
    confirmation_feedback = 'Please enter your password again'

    # Check if the fields match our simple regex.
    if email_valid:
        email_valid = re.match(r'[^@]+@[^@]+\.[^@]+', email)
        email_feedback = 'The value you’ve entered is not a valid email address'

    if password_valid:
        password_valid = len(password) >= 6
        password_feedback = 'The password you’ve entered is too short to be valid'

    if confirmation_valid:
        confirmation_valid = password == confirmation
        confirmation_feedback = 'The passwords you’ve entered don’t match'

    # The rest of the checks involve the DB.
    if email_valid or password_valid:
        ready_db()

    # Check if the user does not already exist in the DB.
    if email_valid:
        email_valid = not database.user_exists(email)
        email_feedback = 'The email you’ve entered is already in use by another account'

    if email_valid and password_valid and confirmation_valid:
        # Hash the password.
        salt = os.urandom(SALT_LENGTH)
        password_hash = scrypt.hash(password, salt)

        # Create the user and their password in the database.
        user_id = database.create_user(email)
        database.create_password(user_id, salt, password_hash)

        # Set the login cookie.
        session['user_id'] = user_id
        session['email'] = email

        return redirect(next_url)
    else:
        return render_template('sign_up.html',
                               next=next_url,
                               email=email,
                               email_valid=email_valid,
                               email_feedback=email_feedback,
                               password=password,
                               password_valid=password_valid,
                               password_feedback=password_feedback,
                               confirmation=confirmation,
                               confirmation_valid=confirmation_valid,
                               confirmation_feedback=confirmation_feedback)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/file_management')
def get_file_management():
    if 'user_id' not in session:
        return redirect('/sign_in?next=/file_management')

    user_id = session['user_id']
    email = session['email']

    ready_db()
    logs = database.get_log_filenames(user_id)

    return render_template('file_management.html',
                           page='file_management',
                           email=email,
                           logs=logs)


@app.route('/file_management', methods=['POST'])
def post_file_management():
    if 'user_id' not in session:
        return redirect('/sign_in?next=/file_management')
    user_id = session['user_id']
    email = session['email']

    ready_db()

    if 'add' in request.form:
        # The user pressed the 'Add file' button.
        if 'log' not in request.files or request.files['log'].filename == '':
            logs = database.get_log_filenames(user_id)
            upload_valid = False
            upload_feedback = 'You did’t select a file to upload'
            return render_template('file_management.html',
                                   page='file_management',
                                   email=email,
                                   logs=logs,
                                   upload_valid=upload_valid,
                                   upload_feedback=upload_feedback)

        new_log = request.files['log']
        filename = new_log.filename
        blob = new_log.read()

        database.create_log(user_id, filename, blob)
    else:  # 'delete' in request.form
        # The user pressed the 'Delete' button.
        log_ids = [key for key in request.form if re.match(r'^\d+$', key)]
        for log_id in log_ids:
            database.delete_log(user_id, log_id)

    logs = database.get_log_filenames(user_id)

    return render_template('file_management.html',
                           page='file_management',
                           email=email,
                           logs=logs)


def connect_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def ready_db():
    if not hasattr(g, 'db'):
        g.db = connect_db()
    return g.db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()


def init_db():
    with app.app_context():
        ready_db()
        database.init_schema()


def init_secret():
    try:
        secret_key = open('secret_key', 'rb').read()
    except FileNotFoundError:
        secret_key = os.urandom(24)
        f = open('secret_key', 'wb')
        f.write(secret_key)
        f.close()

    app.secret_key = secret_key


init_db()
init_secret()

if __name__ == '__main__':
    app.run()
