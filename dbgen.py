"""Script to generate planner bot's database."""
import sqlite3


if __name__ == '__main__':
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("""CREATE TABLE user (id long, authorized boolean);""")
    cur.execute("""CREATE TABLE single (
                id integer PRIMARY KEY,
                name varchar(100),
                startdate varchar(10),
                enddate varchar(10),
                starttime varchar(5),
                endtime varchar(5));"""
                )
