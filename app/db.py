import os, sqlite3
from contextlib import contextmanager
DB_PATH = os.path.join("instance_data", "doculens.db")

def init_db():
    os.makedirs("instance_data", exist_ok=True)
    with sqlite3.connect(DB_PATH) as c:
        c.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        c.execute("INSERT OR IGNORE INTO users(id,name,email,password_hash) VALUES(1,'Local Workspace','local@doculens','not-used')")
        c.execute("CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, original_name TEXT NOT NULL, stored_name TEXT NOT NULL, file_type TEXT NOT NULL, page_count INTEGER DEFAULT 0, chunk_count INTEGER DEFAULT 0, summary TEXT DEFAULT '', topics TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id))")
        c.execute("UPDATE documents SET user_id=1 WHERE user_id<>1")
        c.commit()

@contextmanager
def db():
    init_db()
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()
