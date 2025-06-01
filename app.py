from flask import Flask, request, session, redirect, url_for, render_template, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os

app = Flask(__name__) 

app.config.update(dict( 
DATABASE=os.path.join(app.root_path, os.getenv('DATABASE', 'data.db')), 
SECRET_KEY=os.getenv('SECRET_KEY', 'development key'), 
USERNAME=os.getenv('USERNAME', 'admin'), 
PASSWORD=os.getenv('PASSWORD', 'default') 
)) 

def connect_db(): 
    """Connects to the specific database.""" 
    rv = sqlite3.connect(app.config['DATABASE']) 
    rv.row_factory = sqlite3.Row 
    return rv 

def init_db(): 
    with app.app_context(): 
        db = get_db() 
        with app.open_resource('schema.sql', mode='r') as f: 
            db.executescript(f.read()) 
        db.commit() 

def get_db(): 
    """Opens a new database connection if there is none yet for the 
    current application context.""" 
    if not hasattr(g, 'sqlite_db'): 
        g.sqlite_db = connect_db() 
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

def add_ticket(title, description, user_id):
    db = get_db()
    db.execute('INSERT INTO tickets (title, description, user_id) VALUES (?, ?, ?)',
               (title, description, user_id))
    db.commit()

def get_tickets(user_id=None):
    db = get_db()
    if user_id:
        return db.execute('SELECT * FROM tickets WHERE user_id = ? ORDER BY id DESC', (user_id,)).fetchall()
    else:
        return db.execute('SELECT * FROM tickets ORDER BY id DESC').fetchall()

def update_entry(entry_id, title, text): 
    db = get_db() 
    db.execute('update entries set title = ?, text = ? where id = ?', [title, text, entry_id]) 
    db.commit() 

def delete_entry(entry_id): 
    db = get_db() 
    db.execute('delete from entries where id = ?', [entry_id]) 
    db.commit() 

def seed_dummy_users_and_tickets():
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'adminpass', 'admin')")
        db.execute("INSERT INTO users (username, password, role) VALUES ('user1', 'userpass', 'employee')")
        db.execute("INSERT INTO tickets (title, description, user_id) VALUES ('Printer issue', 'Paper jam error', 2)")
        db.commit()

def clear_db(): 
   with app.app_context(): 
    db = get_db() 
    db.execute('DELETE FROM tickets') 
    db.commit() 

@app.before_request
def fake_login():
    # Simulate being logged in as 'admin' or 'user1'
    session['user_id'] = 1         # Change to 2 for regular user
    session['role'] = 'admin' 

# --- Routes ---
@app.route('/')
def show_tickets():
    if 'user_id' not in session:
        return redirect(url_for('submit_ticket'))

    role = session.get('role')
    user_id = session['user_id']

    if role == 'admin':
        tickets = get_tickets()
    else:
        tickets = get_tickets(user_id=user_id)

    return render_template('show_tickets.html', tickets=tickets)

@app.route('/submit', methods=['GET', 'POST'])
def submit_ticket():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']

        if not title or not description:
            flash('All fields are required!', 'error')
        else:
            add_ticket(title, description, session['user_id'])
            flash('Ticket submitted successfully!', 'success')
            return redirect(url_for('show_tickets'))

    return render_template('submit_ticket.html')

if __name__ == '__main__': 
    try: 
        init_db()
        seed_dummy_users_and_tickets() 
        app.run() 
    finally: 
        clear_db()