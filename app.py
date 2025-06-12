from flask import Flask, request, session, redirect, url_for, render_template, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os
import re
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
            continue
    db.commit()

# --- User Auth ---
import re  # Ensure you have this import at the top

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        db = get_db()
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        employee_id = request.form['employee_id']
        role = request.form['role']

        # --- Validate Employee ID format ---
        if not re.match(r'^EMP\d{4}$', employee_id):
            flash('Employee ID must be in the format EMP0001.', 'error')
            return render_template('register.html')

        # --- Check if Employee ID is already used ---
        existing_emp = db.execute('SELECT 1 FROM users WHERE employee_id = ?', (employee_id,)).fetchone()
        if existing_emp:
            flash('Employee ID already exists.', 'error')
            return render_template('register.html')

        # --- Validate Password ---
        password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
        if not re.match(password_pattern, password):
            flash('Password must be at least 8 characters long, include uppercase, lowercase, a number, and a special character.', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        # --- Insert User ---
        hashed_password = generate_password_hash(password)
        try:
            db.execute('INSERT INTO users (email, password, first_name, last_name, employee_id, role) VALUES (?, ?, ?, ?, ?, ?)',
                       (email, hashed_password, first_name, last_name, employee_id, role))
            db.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Email already exists.', 'error')

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
            return redirect(url_for('dashboard'))
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

# --- Dashboard ---
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    role = session.get('role')
    user_id = session.get('user_id')

    if role == 'admin':
        tickets = db.execute('SELECT * FROM tickets ORDER BY id DESC').fetchall()
    else:
        tickets = db.execute('SELECT * FROM tickets WHERE user_id = ? ORDER BY id DESC', (user_id,)).fetchall()

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
            return redirect(url_for('dashboard'))

    return render_template('submit_ticket.html')

@app.route('/ticket/<int:ticket_id>/edit', methods=['GET', 'POST'])
def edit_ticket(ticket_id):
    db = get_db()
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        db.execute('UPDATE tickets SET title = ?, description = ? WHERE id = ?', (title, description, ticket_id))
        db.commit()
        flash('Ticket updated successfully.', 'success')
        return redirect(url_for('dashboard'))

    ticket = db.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
    return render_template('edit_ticket.html', ticket=ticket)

@app.route('/ticket/<int:ticket_id>/delete', methods=['POST'])
def delete_ticket(ticket_id):
    if session.get('role') != 'admin':
        flash('You are not authorised to delete tickets.', 'error')
        return redirect(url_for('dashboard'))

    db = get_db()
    db.execute('DELETE FROM tickets WHERE id = ?', (ticket_id,))
    db.commit()
    flash('Ticket deleted successfully.', 'success')
    return redirect(url_for('dashboard'))


def seed_dummy_tickets():
    db = get_db()

    # Get existing users
    users = db.execute('SELECT id FROM users WHERE role = ?', ('employee',)).fetchall()

    dummy_tickets = [
        ("Cannot access email", "Getting a 403 error when logging in.", users[0]['id']),
        ("Printer not working", "The printer on floor 2 is jammed.", users[0]['id']),
        ("Slow computer", "Laptop takes 20 minutes to boot.", users[1]['id']),
        ("VPN issue", "VPN disconnects every 5 minutes.", users[1]['id']),
    ]

    for title, description, user_id in dummy_tickets:
        db.execute('INSERT INTO tickets (title, description, user_id) VALUES (?, ?, ?)',
                   (title, description, user_id))

    db.commit()

@app.route('/ticket/<int:ticket_id>')
def view_ticket(ticket_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    db = get_db()
    ticket = db.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,)).fetchone()
    comments = db.execute('''
        SELECT c.content, c.created_at, u.first_name || ' ' || u.last_name AS author
        FROM comments c
        JOIN users u ON c.user_id = u.id
        WHERE c.ticket_id = ?
        ORDER BY c.created_at ASC
    ''', (ticket_id,)).fetchall()

    return render_template('view_ticket.html', ticket=ticket, comments=comments)

@app.route('/ticket/<int:ticket_id>/comment', methods=['POST'])
def add_comment(ticket_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    content = request.form['content']
    db = get_db()
    db.execute(
        'INSERT INTO comments (user_id, content, ticket_id) VALUES (?, ?, ?)',
        (session['user_id'], content, ticket_id)
    )
    db.commit()
    flash('Comment added successfully.', 'success')
    return redirect(url_for('view_ticket', ticket_id=ticket_id))

# --- Main Application ---
if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        init_db()

    with app.app_context():
        db = get_db()

        if not db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
            seed_dummy_users()

        if not db.execute('SELECT 1 FROM tickets LIMIT 1').fetchone():
            seed_dummy_tickets()

    app.run(debug=True, host="0.0.0.0", port=5000)

