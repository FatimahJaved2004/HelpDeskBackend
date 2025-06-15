import pytest
import tempfile
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, init_db, get_db

# ---------- Fixture to create a temp database ----------
@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp()
    app.config['DATABASE'] = db_path
    app.config['TESTING'] = True

    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

    os.close(db_fd)
    os.unlink(db_path)

# ---------- Helper functions ----------
def register_user(client, email, emp_id, role='employee'):
    return client.post('/register', data={
        'email': email,
        'password': 'ValidPass1!',
        'confirm_password': 'ValidPass1!',
        'first_name': 'Test',
        'last_name': 'User',
        'employee_id': emp_id,
        'role': role
    }, follow_redirects=True)

def login_user(client, email):
    return client.post('/login', data={
        'email': email,
        'password': 'ValidPass1!'
    }, follow_redirects=True)

# ---------- Tests ----------
def test_successful_register(client):
    resp = register_user(client, 'new@example.com', 'EMP1001')
    assert b'Registration successful' in resp.data

def test_duplicate_email_register(client):
    register_user(client, 'dup@example.com', 'EMP1002')
    resp = register_user(client, 'dup@example.com', 'EMP1003')
    assert b'Email already exists' in resp.data

def test_register_invalid_employee_id(client):
    resp = client.post('/register', data={
        'email': 'badid@example.com',
        'password': 'ValidPass1!',
        'confirm_password': 'ValidPass1!',
        'first_name': 'Bad',
        'last_name': 'ID',
        'employee_id': 'BAD001',
        'role': 'employee'
    }, follow_redirects=True)
    assert b'Employee ID must be in the format EMP0001.' in resp.data

def test_register_password_mismatch(client):
    resp = client.post('/register', data={
        'email': 'mismatch@example.com',
        'password': 'ValidPass1!',
        'confirm_password': 'DiffPass1!',
        'first_name': 'Mismatch',
        'last_name': 'Test',
        'employee_id': 'EMP1004',
        'role': 'employee'
    }, follow_redirects=True)
    assert b'Passwords do not match.' in resp.data

def test_register_weak_password(client):
    resp = client.post('/register', data={
        'email': 'weakpass@example.com',
        'password': 'weak',
        'confirm_password': 'weak',
        'first_name': 'Weak',
        'last_name': 'Password',
        'employee_id': 'EMP1005',
        'role': 'employee'
    }, follow_redirects=True)
    assert b'Password must be at least 8 characters long' in resp.data

def test_successful_login(client):
    register_user(client, 'login@example.com', 'EMP1006')
    resp = login_user(client, 'login@example.com')
    assert b'Login successful' in resp.data

def test_invalid_login(client):
    resp = login_user(client, 'nonexistent@example.com')
    assert b'Invalid email or password' in resp.data

def test_logout(client):
    register_user(client, 'logout@example.com', 'EMP1007')
    login_user(client, 'logout@example.com')
    resp = client.get('/logout', follow_redirects=True)
    assert b'Logged out successfully' in resp.data

def test_dashboard_requires_login(client):
    resp = client.get('/dashboard', follow_redirects=True)
    assert b'Login' in resp.data

def test_view_ticket_requires_login(client):
    resp = client.get('/ticket/1', follow_redirects=True)
    assert b'Login' in resp.data

def test_ticket_submission(client):
    register_user(client, 'ticket@example.com', 'EMP1008')
    login_user(client, 'ticket@example.com')
    resp = client.post('/submit', data={'title': 'Test Ticket', 'description': 'Desc'}, follow_redirects=True)
    assert b'Ticket submitted successfully' in resp.data
    assert b'Test Ticket' in resp.data

def test_ticket_submission_missing_fields(client):
    register_user(client, 'ticketfail@example.com', 'EMP1009')
    login_user(client, 'ticketfail@example.com')
    resp = client.post('/submit', data={'title': '', 'description': ''}, follow_redirects=True)
    assert b'All fields are required.' in resp.data

def test_ticket_edit(client):
    register_user(client, 'edit@example.com', 'EMP1010')
    login_user(client, 'edit@example.com')
    client.post('/submit', data={'title': 'Old Title', 'description': 'Old Desc'})
    db = get_db()
    ticket_id = db.execute('SELECT id FROM tickets WHERE title = ?', ('Old Title',)).fetchone()['id']
    resp = client.post(f'/ticket/{ticket_id}/edit', data={'title': 'New Title', 'description': 'New Desc'}, follow_redirects=True)
    assert b'Ticket updated successfully' in resp.data
    assert b'New Title' in resp.data

def test_edit_ticket_get(client):
    register_user(client, 'editget@example.com', 'EMP1011')
    login_user(client, 'editget@example.com')
    client.post('/submit', data={'title': 'GET Test', 'description': 'desc'})
    db = get_db()
    ticket_id = db.execute('SELECT id FROM tickets WHERE title = ?', ('GET Test',)).fetchone()['id']
    resp = client.get(f'/ticket/{ticket_id}/edit')
    assert b'GET Test' in resp.data

def test_add_comment(client):
    register_user(client, 'comment@example.com', 'EMP1012')
    login_user(client, 'comment@example.com')
    client.post('/submit', data={'title': 'Comment Ticket', 'description': 'Desc'})
    db = get_db()
    ticket_id = db.execute('SELECT id FROM tickets WHERE title = ?', ('Comment Ticket',)).fetchone()['id']
    resp = client.post(f'/ticket/{ticket_id}/comment', data={'content': 'A comment'}, follow_redirects=True)
    assert b'Comment added successfully' in resp.data
    assert b'A comment' in resp.data

def test_admin_delete_ticket(client):
    register_user(client, 'userdel@example.com', 'EMP1013')
    login_user(client, 'userdel@example.com')
    client.post('/submit', data={'title': 'Del Ticket', 'description': 'Desc'})
    db = get_db()
    ticket_id = db.execute('SELECT id FROM tickets WHERE title = ?', ('Del Ticket',)).fetchone()['id']

    # Employee tries delete
    resp = client.post(f'/ticket/{ticket_id}/delete', follow_redirects=True)
    assert b'not authorised' in resp.data

    # Admin deletes
    register_user(client, 'admin@example.com', 'EMP1014', role='admin')
    login_user(client, 'admin@example.com')
    resp = client.post(f'/ticket/{ticket_id}/delete', follow_redirects=True)
    assert b'Ticket deleted successfully' in resp.data

def test_admin_close_ticket(client):
    register_user(client, 'closer@example.com', 'EMP1015')
    login_user(client, 'closer@example.com')
    client.post('/submit', data={'title': 'Close Ticket', 'description': 'Desc'})
    db = get_db()
    ticket_id = db.execute('SELECT id FROM tickets WHERE title = ?', ('Close Ticket',)).fetchone()['id']

    # Employee tries close
    resp = client.post(f'/ticket/{ticket_id}/close', follow_redirects=True)
    assert b'not authorised' in resp.data

    # Admin closes
    register_user(client, 'adminclose@example.com', 'EMP1016', role='admin')
    login_user(client, 'adminclose@example.com')
    resp = client.post(f'/ticket/{ticket_id}/close', follow_redirects=True)
    assert b'Ticket closed successfully' in resp.data
