import pytest
import tempfile
import os
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

def test_successful_login(client):
    register_user(client, 'login@example.com', 'EMP1004')
    resp = login_user(client, 'login@example.com')
    assert b'Login successful' in resp.data

def test_ticket_submission(client):
    register_user(client, 'ticket@example.com', 'EMP1005')
    login_user(client, 'ticket@example.com')
    resp = client.post('/submit', data={
        'title': 'Test Ticket',
        'description': 'Test Description'
    }, follow_redirects=True)
    assert b'Ticket submitted successfully' in resp.data
    assert b'Test Ticket' in resp.data

def test_ticket_edit(client):
    register_user(client, 'edit@example.com', 'EMP1006')
    login_user(client, 'edit@example.com')
    client.post('/submit', data={'title': 'Old Title', 'description': 'Old Desc'})
    db = get_db()
    ticket_id = db.execute('SELECT id FROM tickets WHERE title = ?', ('Old Title',)).fetchone()['id']
    resp = client.post(f'/ticket/{ticket_id}/edit', data={
        'title': 'New Title',
        'description': 'New Desc'
    }, follow_redirects=True)
    assert b'Ticket updated successfully' in resp.data
    assert b'New Title' in resp.data

def test_add_comment(client):
    register_user(client, 'comment@example.com', 'EMP1007')
    login_user(client, 'comment@example.com')
    client.post('/submit', data={'title': 'Comment Ticket', 'description': 'Some Desc'})
    db = get_db()
    ticket_id = db.execute('SELECT id FROM tickets WHERE title = ?', ('Comment Ticket',)).fetchone()['id']
    resp = client.post(f'/ticket/{ticket_id}/comment', data={'content': 'A comment'}, follow_redirects=True)
    assert b'Comment added successfully' in resp.data
    assert b'A comment' in resp.data

def test_admin_delete_ticket(client):
    register_user(client, 'userdel@example.com', 'EMP1008')
    login_user(client, 'userdel@example.com')
    client.post('/submit', data={'title': 'Del Ticket', 'description': 'Desc'})
    db = get_db()
    ticket_id = db.execute('SELECT id FROM tickets WHERE title = ?', ('Del Ticket',)).fetchone()['id']

    # Try as employee
    resp = client.post(f'/ticket/{ticket_id}/delete', follow_redirects=True)
    assert b'not authorised' in resp.data

    # Register admin and delete
    register_user(client, 'admin@example.com', 'EMP1009', role='admin')
    login_user(client, 'admin@example.com')
    resp = client.post(f'/ticket/{ticket_id}/delete', follow_redirects=True)
    assert b'Ticket deleted successfully' in resp.data

def test_admin_close_ticket(client):
    register_user(client, 'closer@example.com', 'EMP1010')
    login_user(client, 'closer@example.com')
    client.post('/submit', data={'title': 'Close Ticket', 'description': 'Close this'})
    db = get_db()
    ticket_id = db.execute('SELECT id FROM tickets WHERE title = ?', ('Close Ticket',)).fetchone()['id']

    # Try as employee
    resp = client.post(f'/ticket/{ticket_id}/close', follow_redirects=True)
    assert b'not authorised' in resp.data

    # Register admin and close
    register_user(client, 'adminclose@example.com', 'EMP1011', role='admin')
    login_user(client, 'adminclose@example.com')
    resp = client.post(f'/ticket/{ticket_id}/close', follow_redirects=True)
    assert b'Ticket closed successfully' in resp.data
