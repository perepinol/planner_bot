"""Utility functions for connecting to sqlite3 database."""
import sqlite3
import util


class Event:
    def __init__(self, name, startdate, enddate, starttime, endtime, id=None):
        self.id = id
        self.n = name
        self.sd = util.reverse_date(startdate)
        self.ed = util.reverse_date(enddate)
        self.st = starttime
        self.et = endtime

    @staticmethod
    def from_tuple(tuple):
        return Event(tuple[1], tuple[2], tuple[3], tuple[4], tuple[5],
                     tuple[0])

    def as_tuple(self):
        return (self.id, self.n, self.sd, self.ed, self.st, self.et)

    def as_message(self):
        return "*%s*\n" % (self.n) + \
            " From %s %s\n" % (util.reverse_date(self.sd), self.st) + \
            " To %s %s\n" % (util.reverse_date(self.ed), self.et)


def connect():
    """Connect to the database."""
    return sqlite3.connect("database.db")


def add_user(id):
    """
    Add an unauthorized user to the database.

    Returns true if user has been added, false otherwise.
    """
    value = (id, False)
    conn = connect()
    cur = conn.cursor()
    cur.execute("""SELECT id FROM user WHERE id=?""", (id,))
    if cur.fetchone():
        conn.close()
        return False
    cur.execute("INSERT INTO user VALUES (?, ?)", value)
    conn.commit()
    conn.close()
    return True


def is_authorised(id):
    """Get a list of all authorised users."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT id FROM user WHERE authorized=1 AND id=?", (id,))
    user = cur.fetchone()
    conn.close()
    return user is not None


def add_event(event):
    """Add an event to the database."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("INSERT INTO single (name, startdate, enddate, starttime, " +
                "endtime) VALUES (?, ?, ?, ?, ?)", event.as_tuple()[1:])
    conn.commit()
    cur.close()


def get_events(sd, st, ed, et):
    """Get events in a time range."""
    conn = connect()
    cur = conn.cursor()
    cur.execute("""SELECT * FROM single WHERE
                startdate >= ? AND
                enddate <= ? AND
                starttime >= ? AND
                endtime <= ?""",
                (sd, ed, st, et)
                )
    result = cur.fetchall()
    conn.close()
    return list(map(Event.from_tuple, result))
