import sqlite3


class Database:
    conn = sqlite3.connect(database="./database.db")
    cur = conn.cursor()

    def check_database(self):
        self.cur.execute("""CREATE TABLE IF NOT EXISTS "users" (
                        "id"	          INTEGER,
                        "user_id"	      INTEGER NOT NULL UNIQUE,
                        "username"	      TEXT,
                        "user_faculty"    TEXT,
                        "user_course"     INTEGER,
                        "user_group"      TEXT,
                        PRIMARY KEY("id" AUTOINCREMENT));""")
        self.conn.commit()

    def get_users(self):
        self.cur.execute("SELECT * FROM users")
        users = self.cur.fetchall()
        return users

    def get_user(self, user_id):
        self.cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = self.cur.fetchone()
        return user

    def add_user(self, user_id, username):
        self.cur.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        self.conn.commit()

    def update_user(self, user_id, faculty, course, group):
        self.cur.execute("UPDATE users SET user_faculty = ?, user_course = ?, user_group = ? WHERE user_id = ?",
                         (faculty, course, group, user_id))
        self.conn.commit()

