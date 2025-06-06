from flask import Flask, request, session, redirect, url_for, render_template, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os
from flask_cors import CORS

app = Flask(__name__)
CORS(app, supports_credentials=True)

app.config.update(dict(
    DATABASE=os.path.join(app.root_path, os.getenv('DATABASE', 'data.db')),
    SECRET_KEY=os.getenv('SECRET_KEY', 'development key'),
))

# --- DB Connection Helpers ---
def connect_db():
    rv = sqlite3.connect(app.config['DATABASE'])
    rv.row_factory = sqlite3.Row
    return rv

def get_db():
    if 'sqlite_db' not in g:
        g.sqlite_db = connect_db()
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('sqlite_db', None)
    if db is not None:
        db.close()

# --- Init DB ---
def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.executescript(f.read())
        db.commit()

# --- Dummy Data Seeding ---
def seed_dummy_users():
    db = get_db()
    dummy_users = [
        ('admin@example.com', generate_password_hash('adminpass'), 'Alice', 'Admin', 'EMP001', 'admin'),
        ('user1@example.com', generate_password_hash('userpass'), 'Bob', 'User', 'EMP002', 'employee'),
        ('user2@example.com', generate_password_hash('userpass2'), 'Charlie', 'Worker', 'EMP003', 'employee')
    ]
    for user in dummy_users:
        try:
            db.execute('INSERT INTO users (email, password, first_name, last_name, employee_id, role) VALUES (?, ?, ?, ?, ?, ?)', user)
        except sqlite3.IntegrityError:
            continue  # Skip if already exists
    db.commit()

# --- User Auth ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        db = get_db()
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        employee_id = request.form['employee_id']
        role = request.form['role']

        try:
            db.execute('INSERT INTO users (email, password, first_name, last_name, employee_id, role) VALUES (?, ?, ?, ?, ?, ?)',
                       (email, password, first_name, last_name, employee_id, role))
            db.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists or role invalid.', 'error')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            flash('Login successful.', 'success')
            return redirect(url_for('show_tickets'))
        else:
            flash('Invalid email or password', 'error')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

# --- Home Page ---
@app.route('/')
def home():
    return render_template('home.html')

# --- Ticket Functions ---
@app.route('/tickets')
def show_tickets():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    if session['role'] == 'admin':
        tickets = db.execute('SELECT * FROM tickets ORDER BY id DESC').fetchall()
    else:
        tickets = db.execute('SELECT * FROM tickets WHERE user_id = ? ORDER BY id DESC',
                             (session['user_id'],)).fetchall()

    return render_template('show_tickets.html', tickets=tickets)

@app.route('/submit', methods=['GET', 'POST'])
def submit_ticket():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']

        if not title or not description:
            flash('All fields are required!', 'error')
        else:
            db = get_db()
            db.execute('INSERT INTO tickets (title, description, user_id) VALUES (?, ?, ?)',
                       (title, description, session['user_id']))
            db.commit()
            flash('Ticket submitted successfully!', 'success')
            return redirect(url_for('show_tickets'))

    return render_template('submit_ticket.html')

if __name__ == '__main__':
    with app.app_context():
        init_db()
        seed_dummy_users()
    app.run(debug=True, host="0.0.0.0", port=5000)
