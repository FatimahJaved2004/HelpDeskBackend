from flask import Flask, request, session, redirect, url_for, render_template, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
from datetime import datetime
import sqlite3
import os
import re
import humanize

# --- App setup ---
app = Flask(__name__)
CORS(app, supports_credentials=True)

app.config.update({
    'DATABASE': os.path.join(app.root_path, os.getenv('DATABASE', 'data.db')),
    'SECRET_KEY': os.getenv('SECRET_KEY', 'development key')
})

# --- DB helpers ---
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
    if db:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql') as f:
            db.executescript(f.read().decode('utf-8'))
        db.commit()

# --- Template filter ---
@app.template_filter('naturaltime')
def naturaltime_filter(value):
    if not value:
        return ''
    try:
        dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        return humanize.naturaltime(datetime.utcnow() - dt)
    except Exception:
        return value

# --- Seed data ---
def seed_dummy_users():
    db = get_db()
    users = [
        ('admin@fujitsu.com', generate_password_hash('adminpass'), 'Alice', 'Admin', 'EMP0001', 'admin'),
        ('user1@fujitsu.com', generate_password_hash('userpass'), 'Bob', 'Smith', 'EMP0002', 'employee'),
        ('user2@fujitsu.com', generate_password_hash('userpass2'), 'Charlie', 'Jane', 'EMP0003', 'employee'),
        ('user3@fujitsu.com', generate_password_hash('adminpass2'), 'David', 'Lee', 'EMP0004', 'admin'),
        ('user5@fujitsu.com', generate_password_hash('userpass4'), 'Fatimah', 'Javed', 'EMP0005', 'employee'),
        ('user6@fujitsu.com', generate_password_hash('userpass5'), 'Evelyn', 'Adams', 'EMP0006', 'employee'),
        ('user7@fujitsu.com', generate_password_hash('userpass6'), 'Sam', 'Miller', 'EMP0007', 'employee'),
        ('user8@fujitsu.com', generate_password_hash('userpass7'), 'Toto', 'Brown', 'EMP0008', 'employee'),
        ('user9@fujitsu.com', generate_password_hash('userpass8'), 'Ashton', 'Wright', 'EMP0009', 'employee'),
        ('user10@fujitsu.com', generate_password_hash('userpass9'), 'Mehak', 'Sajel', 'EMP0010', 'employee')
    ]
    for u in users:
        try:
            db.execute('INSERT INTO users (email, password, first_name, last_name, employee_id, role) VALUES (?, ?, ?, ?, ?, ?)', u)
        except sqlite3.IntegrityError:
            continue
    db.commit()

def seed_dummy_tickets():
    db = get_db()
    users = db.execute('SELECT id FROM users WHERE role = ?', ('employee',)).fetchall()
    tickets = [
        ("Cannot access email", "403 error logging in", users[0]['id']),
        ("Printer jam", "Printer on floor 2 jammed", users[0]['id']),
        ("Slow laptop", "Laptop takes 20 mins to boot", users[1]['id']),
        ("VPN drops", "VPN disconnects repeatedly", users[1]['id']),
        ("Software installation", "Need to install software on new laptop", users[2]['id']),
        ("Hardware upgrade", "Request to upgrade RAM on laptop", users[3]['id']),
        ("Network issue", "Cannot connect to Wi-Fi", users[4]['id']),
        ("Password reset", "Forgot password, need reset link", users[5]['id']),
        ("Email configuration", "Need help setting up email client", users[6]['id']),
        ("Access request", "Request access to shared drive", users[7]['id']),
        ("System crash", "System crashes on startup", users[7]['id']),
        ("Backup failure", "Daily backup failed, need investigation", users[1]['id']),
        ("Application bug", "Found bug in internal application", users[7]['id']),
        ("Database issue", "Cannot connect to database server", users[6]['id']),
        ("Security alert", "Received security alert email", users[5]['id']),
        ("Performance issue", "System performance is slow", users[4]['id']),
        ("Update request", "Request to update software version", users[3]['id']),
        ("New hardware request", "Request for new monitor and keyboard", users[2]['id']),
        ("Training request", "Need training on new software tools", users[1]['id']),
        ("Policy clarification", "Need clarification on IT policy", users[0]['id'])
    ]
    for t in tickets:
        db.execute('INSERT INTO tickets (title, description, user_id) VALUES (?, ?, ?)', t)
    db.commit()

# --- Routes ---
@app.route('/')
def home():
    return render_template('home.html')

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

        if not re.match(r'^EMP\d{4}$', employee_id):
            flash('Employee ID must be in the format EMP0001.', 'error')
            return render_template('register.html')

        if db.execute('SELECT 1 FROM users WHERE employee_id = ?', (employee_id,)).fetchone():
            flash('Employee ID already exists.', 'error')
            return render_template('register.html')

        pw_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
        if not re.match(pw_pattern, password):
            flash('Password must be at least 8 characters long, include uppercase, lowercase, a number, and a special character.', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')

        try:
            hashed_pw = generate_password_hash(password)
            db.execute('INSERT INTO users (email, password, first_name, last_name, employee_id, role) VALUES (?, ?, ?, ?, ?, ?)',
                       (email, hashed_pw, first_name, last_name, employee_id, role))
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
            session['first_name'] = user['first_name']
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

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    user_id = session['user_id']
    role = session['role']
    status = request.args.get('status')

    q = '''
        SELECT t.*, u.first_name || ' ' || u.last_name AS creator_name
        FROM tickets t
        JOIN users u ON t.user_id = u.id
    '''
    params = ()

    if role != 'admin':
        q += ' WHERE t.user_id = ?'
        params = (user_id,)

    if status:
        if 'WHERE' in q:
            q += ' AND t.status = ?'
        else:
            q += ' WHERE t.status = ?'
        params += (status,)

    q += ' ORDER BY t.id DESC'
    tickets = db.execute(q, params).fetchall()

    return render_template('show_tickets.html', tickets=tickets)

@app.route('/submit', methods=['GET', 'POST'])
def submit_ticket():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        if not title or not description:
            flash('All fields are required.', 'error')
        else:
            db = get_db()
            db.execute('INSERT INTO tickets (title, description, user_id) VALUES (?, ?, ?)',
                       (title, description, session['user_id']))
            db.commit()
            flash('Ticket submitted successfully.', 'success')
            return redirect(url_for('dashboard'))
    return render_template('submit_ticket.html')

@app.route('/ticket/<int:ticket_id>/close', methods=['POST'])
def close_ticket(ticket_id):
    if 'user_id' not in session or session['role'] != 'admin':
        flash('You are not authorised to close tickets.', 'error')
        return redirect(url_for('dashboard'))
    db = get_db()
    db.execute('UPDATE tickets SET status = ? WHERE id = ?', ('Closed', ticket_id))
    db.commit()
    flash('Ticket closed successfully.', 'success')
    return redirect(url_for('dashboard'))

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
        ORDER BY c.created_at
    ''', (ticket_id,)).fetchall()
    return render_template('view_ticket.html', ticket=ticket, comments=comments)

@app.route('/ticket/<int:ticket_id>/comment', methods=['POST'])
def add_comment(ticket_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    content = request.form['content']
    db = get_db()
    db.execute('INSERT INTO comments (user_id, content, ticket_id) VALUES (?, ?, ?)',
               (session['user_id'], content, ticket_id))
    db.commit()
    flash('Comment added successfully.', 'success')
    return redirect(url_for('view_ticket', ticket_id=ticket_id))

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

# --- Run ---
if __name__ == '__main__':
    if not os.path.exists(app.config['DATABASE']):
        init_db()
    with app.app_context():
        db = get_db()
        if not db.execute('SELECT 1 FROM users').fetchone():
            seed_dummy_users()
        if not db.execute('SELECT 1 FROM tickets').fetchone():
            seed_dummy_tickets()
    app.run(debug=True, host="0.0.0.0", port=5000)
