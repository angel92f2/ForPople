from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
import sqlite3
from flask import url_for

app = Flask(__name__)

app.config["SECRET_KEY"] = "secret123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"

db = SQLAlchemy(app)

def get_db():
    conn = sqlite3.connect("forum.db")
    conn.row_factory = sqlite3.Row
    return conn

def add_log(action, username):
    conn = get_db()

    conn.execute(
        "INSERT INTO logs(action, username) VALUES(?, ?)",
        (action, username)
    )

    conn.commit()
    conn.close()


def init_forum():
    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS posts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        author TEXT,
        likes INTEGER DEFAULT 0
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS comments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER,
        author TEXT,
        text TEXT
    )
    """)

    conn.execute("""
CREATE TABLE IF NOT EXISTS post_likes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER,
    username TEXT
)
""")
    
    conn.execute("""
CREATE TABLE IF NOT EXISTS logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT,
    username TEXT
)
""")

    conn.execute("""
CREATE TABLE IF NOT EXISTS post_dislikes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER,
    username TEXT
)
""")
    
    
    conn.commit()
    conn.close()


init_forum()

@app.route("/forum")
def forum():
    conn = get_db()
    raw_posts = conn.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    rows = conn.execute("PRAGMA table_info(posts)").fetchall()

    for row in rows:
        print(row["name"])
    conn.close()

    posts = []
    for post in raw_posts:
        post_dict = dict(post)
        user = User.query.filter_by(username=post['author']).first()
        post_dict['author_role'] = user.role if user else "user"
        posts.append(post_dict)

    current_role = "user"

    if "user" in session:
        current_user = User.query.filter_by(
        username=session["user"]
    ).first()

    if current_user:
        current_role = current_user.role

    return render_template("forum.html", posts=posts, current_role=current_role)

@app.route("/forum/post/<int:id>")
def post(id):
    conn = get_db()
    raw_post = conn.execute("SELECT * FROM posts WHERE id=?", (id,)).fetchone()
    
    if not raw_post:
        conn.close()
        return "Error 404, Post not found", 404

    raw_comments = conn.execute("SELECT * FROM comments WHERE post_id=?", (id,)).fetchall()
    conn.close()

    post_dict = dict(raw_post)
    post_user = User.query.filter_by(username=post_dict['author']).first()
    post_dict['author_role'] = post_user.role if post_user else "user"
    comments = []
    for comment in raw_comments:
        comment_dict = dict(comment)
        comment_user = User.query.filter_by(username=comment['author']).first()
        comment_dict['author_role'] = comment_user.role if comment_user else "user"
        comments.append(comment_dict)

    current_role = "user"

    if "user" in session:
        current_user = User.query.filter_by(
        username=session["user"]
    ).first()

    if current_user:
        current_role = current_user.role

    return render_template("post.html", post=post_dict, comments=comments, current_role=current_role)

@app.route("/forum/comment/<int:id>", methods=["POST"])
def comment(id):

    if "user" not in session:
        return redirect("/login")

    text = request.form["text"]

    conn = get_db()

    conn.execute(
        "INSERT INTO comments(post_id,author,text) VALUES(?,?,?)",
        (id, session["user"], text)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("post", id=id))

@app.route("/forum/delete_comment/<int:comment_id>")
def delete_comment(comment_id):

    if "user" not in session:
        return redirect("/login")

    current_user = User.query.filter_by(
        username=session["user"]
    ).first()

    if not current_user or current_user.role != "admin":
        return "Error 403, access denied", 403

    conn = get_db()

    comment = conn.execute(
        "SELECT * FROM comments WHERE id=?",
        (comment_id,)
    ).fetchone()

    if not comment:
        conn.close()
        return "Comment not found"

    post_id = comment["post_id"]

    conn.execute(
        "DELETE FROM comments WHERE id=?",
        (comment_id,)
    )

    conn.commit()
    add_log(
    f"Delete comment ID:{comment_id}",
    session["user"]
)
    conn.close()

    return redirect(url_for("post", id=post_id))

@app.route("/forum/like/<int:id>")
def like(id):

    if "user" not in session:
        return redirect("/login")

    conn = get_db()

    username = session["user"]

    liked = conn.execute(
        """
        SELECT * FROM post_likes
        WHERE post_id=? AND username=?
        """,
        (id, username)
    ).fetchone()

    if liked:

        conn.execute(
            """
            DELETE FROM post_likes
            WHERE post_id=? AND username=?
            """,
            (id, username)
        )

        conn.execute(
            """
            UPDATE posts
            SET likes = likes - 1
            WHERE id=?
            """,
            (id,)
        )

    else:

        conn.execute(
            """
            INSERT INTO post_likes(post_id, username)
            VALUES(?, ?)
            """,
            (id, username)
        )

        conn.execute(
            """
            UPDATE posts
            SET likes = likes + 1
            WHERE id=?
            """,
            (id,)
        )

    conn.commit()
    conn.close()

    return redirect("/forum")

@app.route("/forum/dislike/<int:id>")
def dislike(id):

    if "user" not in session:
        return redirect("/login")

    username = session["user"]

    conn = get_db()

    disliked = conn.execute(
        """
        SELECT * FROM post_dislikes
        WHERE post_id=? AND username=?
        """,
        (id, username)
    ).fetchone()

    if disliked:

        conn.execute(
            """
            DELETE FROM post_dislikes
            WHERE post_id=? AND username=?
            """,
            (id, username)
        )

        conn.execute(
            """
            UPDATE posts
            SET dislikes = dislikes - 1
            WHERE id=?
            """,
            (id,)
        )

    else:

        conn.execute(
            """
            INSERT INTO post_dislikes(post_id, username)
            VALUES(?,?)
            """,
            (id, username)
        )

        conn.execute(
            """
            UPDATE posts
            SET dislikes = dislikes + 1
            WHERE id=?
            """,
            (id,)
        )

    conn.commit()
    conn.close()

    return redirect("/forum")

@app.route("/forum/create", methods=["GET", "POST"])
def create_post():

      if request.method == "POST":

        title = request.form["title"]
        content = request.form["content"]
        author = session["user"]

        conn = get_db()
        conn.execute(
            "INSERT INTO posts (title, content, author) VALUES (?, ?, ?)",
            (title, content, author)
        )

        conn.commit()
        add_log(
    f"Make post: {title}",
    author
)
        conn.close()

        return redirect("/forum")

@app.route("/forum/delete_post/<int:post_id>")
def delete_post(post_id):

    if "user" not in session:
        return redirect("/login")

    current_user = User.query.filter_by(
        username=session["user"]
    ).first()

    if not current_user or current_user.role != "admin":
        return "Error 403, access denied", 403

    conn = get_db()

    post = conn.execute(
        "SELECT * FROM posts WHERE id=?",
        (post_id,)
    ).fetchone()

    if not post:
        conn.close()
        return "Post not found"

    conn.execute(
        "DELETE FROM comments WHERE post_id=?",
        (post_id,)
    )

    conn.execute(
        "DELETE FROM post_likes WHERE post_id=?",
        (post_id,)
    )

    conn.execute(
        "DELETE FROM post_dislikes WHERE post_id=?",
        (post_id,)
    )

    conn.execute(
        "DELETE FROM posts WHERE id=?",
        (post_id,)
    )

    conn.commit()
    conn.close()

    add_log(
        f"Delete post ID:{post_id}",
        session["user"]
    )

    return redirect("/forum")

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default="user")

with app.app_context():
    db.create_all()
    
    admin_user = User.query.filter_by(username="1").first()
    if admin_user and admin_user.role != "admin":
        admin_user.role = "admin"
        db.session.commit()

@app.route("/")
def home():
    if "user" in session:
        return redirect("/profile")
    return redirect("/login")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        exists = User.query.filter_by(username=username).first()
        if exists:
            return "This user registered"

        user = User(username=username, password=password, role="user")
        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["user"] = user.username
            return redirect("/profile")

        return "Incorrect username or password"

    return render_template("login.html")

@app.route("/profile")
def profile():
    if "user" not in session:
        return redirect("/login")

    user = User.query.filter_by(username=session["user"]).first()

    if user is None:
        session.clear()
        return redirect("/login")

    return render_template(
        "profile.html",
        username=user.username,
        role=user.role
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/admin")
def admin():

    if "user" not in session:
        return redirect("/login")

    current_user = User.query.filter_by(username=session["user"]).first()

    if not current_user or current_user.role != "admin":
        return "Error 403, access denied", 403

    users = User.query.all()

    conn = get_db()

    logs = conn.execute(
    "SELECT * FROM logs ORDER BY id DESC"
).fetchall()

    posts = conn.execute(
    "SELECT * FROM posts ORDER BY id DESC"
).fetchall()

    comments = conn.execute(
    "SELECT * FROM comments ORDER BY id DESC"
).fetchall()

    conn.close()
    return render_template("admin.html", users=users, logs=logs, posts=posts, comments=comments)


@app.route("/set-role/<int:user_id>/<role>")
def set_role(user_id, role):
    if "user" not in session:
        return redirect("/login")

    current_user = User.query.filter_by(username=session["user"]).first()
    if not current_user or current_user.role != "admin":
        return "Error 403,  access denied", 403

    user = db.session.get(User, user_id)
    if user:
        user.role = role
        db.session.commit()

    return redirect("/admin")
@app.route("/lessons")
def lessons():

    return render_template("lessons.html")
@app.route("/terms")
def terms():
    return render_template("page2.html")


@app.route("/index")
def main_page():

    if "user" in session:
        user = User.query.filter_by(username=session["user"]).first()
        role = user.role if user else "user"
    else:
        role = "user"
        
    return render_template("index.html", role=role)

@app.route("/lessons/python")
def python_lesson():
    return render_template("python.html")

@app.route("/lessons/html")
def html_lesson():

    return render_template("html.html")

@app.route("/contacts")
def contacts():

    return render_template("contact page.html")

@app.route("/delete-user/<int:user_id>")
def delete_user(user_id):

    if "user" not in session:
        return redirect("/login")

    current_user = User.query.filter_by(username=session["user"]).first()

    if not current_user or current_user.role != "admin":
        return "Error 403", 403

    user = db.session.get(User, user_id)

    if not user:
        return "User not found"

    if user.username == session["user"]:
        return "You can't delete yourself"

    db.session.delete(user)
    db.session.commit()

    add_log(
        f"Delete user: {user.username}",
        session["user"]
    )

    return redirect("/admin")

@app.route("/change-password/<int:user_id>", methods=["POST"])
def change_password(user_id):

    if "user" not in session:
        return redirect("/login")

    current_user = User.query.filter_by(username=session["user"]).first()

    if not current_user or current_user.role != "admin":
        return "Error 403", 403

    new_password = request.form["password"]

    user = db.session.get(User, user_id)

    if not user:
        return "User not found"

    user.password = new_password
    db.session.commit()

    add_log(
        f"Changed password: {user.username}",
        session["user"]
    )

    return redirect("/admin")

if __name__ == "__main__":
    app.run(debug=True)

    
