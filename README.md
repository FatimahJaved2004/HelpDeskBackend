# Help Desk Ticketing System

This is a Flask-based web application for managing IT support tickets. The app allows employees to submit tickets and add comments, while admins can manage users, close tickets, and oversee all submissions.

---

## 🚀 How to Run This Application

### 1. Requirements

Ensure Python 3.9+ is installed. Then install the dependencies:

```bash
pip install flask flask-cors werkzeug humanize
```

---

### 2. Run the Application

Start the app with:

```bash
python app.py
```

It will run locally at:

```
http://localhost:5000
```

---

### 3. Log In or Register

You can **log in** using the pre-created admin account:

- **Email**: `admin@fujitsu.com`  
- **Password**: `Admin1Pass123!`

You can **log in** using the pre-created **user** account:

- **Email**: `user@fujitsu.com`  
- **Password**: `User1Pass123!`

Or simply **register a new user/admin** via the homepage and log in with your details.

---

## ✅ Features

- Employee registration & login
- Submit and comment on tickets
- Admin-only ticket closing, deletion, and user view
- Flash messages for user feedback
- Client-side and server-side validation
- Bootstrap styling with separate JS and CSS

---

## 💡 Note
To reset everything, delete `data.db` and re-run the app.




