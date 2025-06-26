import pytest
import tempfile
import sys
import os

# Allow importing app from parent directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, init_db, get_db

# ---------- Test Setup ----------
@pytest.fixture
def client():
    """Creates a test client with a temporary database"""
    db_fd, db_path = tempfile.mkstemp()
    app.config['DATABASE'] = db_path
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

    os.close(db_fd)
    os.unlink(db_path)

# ---------- Helper Functions ----------
def register_user(client, email, emp_id, role='employee'):
    """Registers a user with the given details"""
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
    """Logs in the user"""
    return client.post('/login', data={
        'email': email,
        'password': 'ValidPass1!'
    }, follow_redirects=True)

# ---------- Tests ----------

def test_home_page(client):
    """Check home page loads"""
    resp = client.get('/')
    assert b'Help Desk' in resp.data or resp.status_code == 200

def test_successful_register(client):
    """Register a user successfully"""
    resp = register_user(client, 'new@example.com', 'EMP1001')
    assert b'Registration successful' in resp.data

def test_duplicate_email_register(client):
    """Ensure duplicate emails are not allowed"""
    register_user(client, 'dup@example.com', 'EMP1002')
    resp = register_user(client, 'dup@example.com', 'EMP1003')
    assert b'Email already exists' in resp.data

def test_register_duplicate_employee_id(client):
    """Ensure duplicate employee IDs are rejected"""
    register_user(client, 'user1@example.com', 'EMP2000')
    resp = register_user(client, 'user2@example.com', 'EMP2000')
    assert b'Employee ID already exists' in resp.data

def test_register_invalid_employee_id(client):
    """Test invalid employee ID format"""
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
    """Passwords must match to register"""
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
    """Reject weak passwords"""
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
    """Login with correct credentials"""
    register_user(client, 'login@example.com', 'EMP1006')
    resp = login_user(client, 'login@example.com')
    assert b'Login successful' in resp.data

def test_invalid_login(client):
    """Login should fail for non-existent user"""
    resp = login_user(client, 'nonexistent@example.com')
    assert b'Invalid email or password' in resp.data

def test_logout(client):
    """User can log out"""
    register_user(client, 'logout@example.com', 'EMP1007')
    login_user(client, 'logout@example.com')
    resp = client.get('/logout', follow_redirects=True)
    assert b'Logged out successfully' in resp.data

def test_dashboard_requires_login(client):
    """Dashboard is restricted to logged in users"""
    resp = client.get('/dashboard', follow_redirects=True)
    assert b'Login' in resp.data

def test_ticket_submission(client):
    """Submit a new ticket successfully"""
    register_user(client, 'ticket@example.com', 'EMP1008')
    login_user(client, 'ticket@example.com')
    resp = client.post('/submit', data={'title': 'Test Ticket', 'description': 'Desc'}, follow_redirects=True)
    assert b'Ticket submitted successfully' in resp.data
    assert b'Test Ticket' in resp.data

def test_ticket_submission_missing_fields(client):
    """Ticket submission requires title and description"""
    register_user(client, 'ticketfail@example.com', 'EMP1009')
    login_user(client, 'ticketfail@example.com')
    resp = client.post('/submit', data={'title': '', 'description': ''}, follow_redirects=True)
    assert b'All fields are required.' in resp.data

def test_ticket_edit(client):
    """User can edit their own ticket"""
    register_user(client, 'edit@example.com', 'EMP1010')
    login_user(client, 'edit@example.com')
    client.post('/submit', data={'title': 'Old Title', 'description': 'Old Desc'})
    db = get_db()
    ticket_id = db.execute('SELECT id FROM tickets WHERE title = ?', ('Old Title',)).fetchone()['id']
    resp = client.post(f'/ticket/{ticket_id}/edit', data={'title': 'New Title', 'description': 'New Desc'}, follow_redirects=True)
    assert b'Ticket updated successfully' in resp.data
    assert b'New Title' in resp.data

def test_add_comment(client):
    """User can add a comment to their ticket"""
    register_user(client, 'comment@example.com', 'EMP1012')
    login_user(client, 'comment@example.com')
    client.post('/submit', data={'title': 'Comment Ticket', 'description': 'Desc'})
    db = get_db()
    ticket_id = db.execute('SELECT id FROM tickets WHERE title = ?', ('Comment Ticket',)).fetchone()['id']
    resp = client.post(f'/ticket/{ticket_id}/comment', data={'content': 'A comment'}, follow_redirects=True)
    assert b'Comment added successfully' in resp.data
    assert b'A comment' in resp.data

def test_admin_delete_ticket(client):
    """Only admin can delete tickets"""
    register_user(client, 'userdel@example.com', 'EMP1013')
    login_user(client, 'userdel@example.com')
    client.post('/submit', data={'title': 'Del Ticket', 'description': 'Desc'})
    db = get_db()
    ticket_id = db.execute('SELECT id FROM tickets WHERE title = ?', ('Del Ticket',)).fetchone()['id']
    resp = client.post(f'/ticket/{ticket_id}/delete', follow_redirects=True)
    assert b'not authorised' in resp.data

    register_user(client, 'admin@example.com', 'EMP1014', role='admin')
    login_user(client, 'admin@example.com')
    resp = client.post(f'/ticket/{ticket_id}/delete', follow_redirects=True)
    assert b'Ticket deleted successfully' in resp.data

def test_admin_close_ticket(client):
    """Only admin can close tickets"""
    register_user(client, 'closer@example.com', 'EMP1015')
    login_user(client, 'closer@example.com')
    client.post('/submit', data={'title': 'Close Ticket', 'description': 'Desc'})
    db = get_db()
    ticket_id = db.execute('SELECT id FROM tickets WHERE title = ?', ('Close Ticket',)).fetchone()['id']
    resp = client.post(f'/ticket/{ticket_id}/close', follow_redirects=True)
    assert b'not authorised' in resp.data

    register_user(client, 'adminclose@example.com', 'EMP1016', role='admin')
    login_user(client, 'adminclose@example.com')
    resp = client.post(f'/ticket/{ticket_id}/close', follow_redirects=True)
    assert b'Ticket closed successfully' in resp.data

def test_admin_view_users(client):
    """Admin can view all users"""
    register_user(client, 'adminv@example.com', 'EMP2021', role='admin')
    login_user(client, 'adminv@example.com')
    resp = client.get('/admin/users')
    assert b'EMP2021' in resp.data

def test_non_admin_view_users_denied(client):
    """Employees should not access the admin user list"""
    register_user(client, 'empv@example.com', 'EMP2022', role='employee')
    login_user(client, 'empv@example.com')
    resp = client.get('/admin/users', follow_redirects=True)
    assert b'not authorised' in resp.data

def test_admin_view_user_tickets(client):
    """Admin can view another user's tickets"""
    register_user(client, 'target@example.com', 'EMP2023', role='employee')
    login_user(client, 'target@example.com')
    client.post('/submit', data={'title': 'Emp Ticket', 'description': 'emp desc'})
    register_user(client, 'adminv2@example.com', 'EMP2024', role='admin')
    login_user(client, 'adminv2@example.com')
    db = get_db()
    user_id = db.execute('SELECT id FROM users WHERE email = ?', ('target@example.com',)).fetchone()['id']
    resp = client.get(f'/users/{user_id}/tickets')
    assert b'Emp Ticket' in resp.data

def test_view_user_tickets_invalid_user(client):
    """Admin views ticket for invalid/non-existent user"""
    register_user(client, 'adminv3@example.com', 'EMP2025', role='admin')
    login_user(client, 'adminv3@example.com')
    resp = client.get('/users/999/tickets', follow_redirects=True)
    assert b'User not found' in resp.data
