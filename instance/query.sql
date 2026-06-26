CREATE TABLE posts(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    content TEXT,
    author TEXT,
    likes INTEGER DEFAULT 0,
    dislikes INTEGER DEFAULT 0
)