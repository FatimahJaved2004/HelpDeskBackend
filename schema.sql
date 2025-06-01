DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS tickets;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  password TEXT NOT NULL,
  first_name TEXT,
  last_name TEXT,
  employee_id TEXT,
  role TEXT CHECK(role IN ('admin', 'employee')) NOT NULL
);


CREATE TABLE tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT DEFAULT 'Open',
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
