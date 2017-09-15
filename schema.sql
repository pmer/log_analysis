DROP TABLE IF EXISTS schema_version;
CREATE TABLE schema_version (
    last_modified INTEGER
);

DROP TABLE IF EXISTS users;
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL
);

DROP TABLE IF EXISTS passwords;
CREATE TABLE passwords (
    user_id INTEGER PRIMARY KEY,
    salt TEXT NOT NULL,
    password_hash TEXT NOT NULL
);

DROP TABLE IF EXISTS logs;
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    blob TEXT NOT NULL
);

DROP INDEX IF EXISTS users_email;
CREATE INDEX users_email ON users (email);
