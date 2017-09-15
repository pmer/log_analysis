from flask import g
import os


SCHEMA_FILE = 'schema.sql'


def init_schema():
    if db_is_empty() or need_schema_update():
        print('Updating schema, dropping all tables')

        schema = open(SCHEMA_FILE).read()
        g.db.cursor().executescript(schema)

        schema_mod_time = int(os.stat(SCHEMA_FILE).st_mtime)
        query_db("""
                 INSERT INTO schema_version (last_modified)
                 VALUES (?)
                 """, [schema_mod_time])

        g.db.commit()


def db_is_empty():
    rows = query_db("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type='table'
                    """)
    return rows is None or len(rows) == 0


def need_schema_update():
    row = query_db("""
                   SELECT last_modified
                   FROM schema_version
                   """, one=True)
    if row is None:
        return True

    db_mod_time = row['last_modified']
    schema_mod_time = int(os.stat(SCHEMA_FILE).st_mtime)
    return schema_mod_time > db_mod_time


def user_exists(email):
    row = query_db("""
                   SELECT id
                   FROM users
                   WHERE email = ?
                   """, [email], one=True)
    return True if row else False


def get_user_id(email):
    row = query_db("""
                   SELECT id
                   FROM users
                   WHERE email = ?
                   """, [email], one=True)
    return row['id'] if row else None


def get_password(email):
    row = query_db("""
                   SELECT salt, password_hash
                   FROM users, passwords
                   WHERE id = user_id and
                         email = ?
                   """, [email], one=True)
    if row:
        return row['salt'], row['password_hash']
    else:
        return None, None


def create_user(email):
    # Create a user without specifying their id. SQLite will automatically allocate an id for them but won't tell us
    # what it is.
    query_db("""
             INSERT into users (email)
             VALUES (?)
             """, [email])

    g.db.commit()

    # Query the sqlite_sequence table, as recommended by Stack Overflow, to find the id.
    row = query_db("""
                   SELECT seq
                   FROM sqlite_sequence
                   WHERE name = "users"
                   """, one=True)
    assert(row is not None)

    return row['seq']


def create_password(user_id, salt, password_hash):
    query_db("""
             INSERT into passwords (user_id, salt, password_hash)
             VALUES (?, ?, ?)
             """, [user_id, salt, password_hash])

    g.db.commit()


def get_log_filenames(user_id):
    return query_db("""
                    SELECT id, filename
                    FROM logs
                    WHERE user_id = ?
                    """, [user_id])


def create_log(user_id, filename, blob):
    query_db("""
             INSERT INTO logs (user_id, filename, blob)
             VALUES (?, ?, ?)
             """, [user_id, filename, blob])

    g.db.commit()


def delete_log(user_id, log_id):
    query_db("""
             DELETE FROM logs
             WHERE user_id = ? AND
                   id = ?
             """, [user_id, log_id])

    g.db.commit()


def query_db(query, args=(), one=False):
    cur = g.db.execute(query, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows
