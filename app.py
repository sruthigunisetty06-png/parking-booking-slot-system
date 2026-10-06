from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, math, uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
DB = "parking.db"

def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL, phone TEXT,
        vehicle_number TEXT NOT NULL, vehicle_type TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS slots(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slot_number TEXT UNIQUE NOT NULL,
        vehicle_type TEXT NOT NULL,
        status TEXT DEFAULT 'AVAILABLE'
    );
    CREATE TABLE IF NOT EXISTS bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL, slot_id INTEGER NOT NULL,
        booking_date TEXT NOT NULL, start_time TEXT NOT NULL,
        end_time TEXT NOT NULL, status TEXT DEFAULT 'CONFIRMED',
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(slot_id) REFERENCES slots(id)
    );
    CREATE TABLE IF NOT EXISTS entry_exit(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id TEXT NOT NULL, entry_time TEXT,
        exit_time TEXT, duration_hours INTEGER, charge REAL DEFAULT 0,
        FOREIGN KEY(booking_id) REFERENCES bookings(booking_id)
    );
    """)
    if conn.execute("SELECT COUNT(*) FROM slots").fetchone()[0] == 0:
        for i in range(1, 11):
            conn.execute("INSERT INTO slots(slot_number,vehicle_type) VALUES(?,?)", (f"2W-{i:02}", "TWO_WHEELER"))
        for i in range(1, 11):
            conn.execute("INSERT INTO slots(slot_number,vehicle_type) VALUES(?,?)", (f"4W-{i:02}", "FOUR_WHEELER"))
    conn.commit(); conn.close()

def conflict(slot_id, date, start, end):
    conn = db()
    row = conn.execute("""
        SELECT id FROM bookings
        WHERE slot_id=? AND booking_date=? AND status='CONFIRMED'
        AND NOT (end_time <= ? OR start_time >= ?)
    """, (slot_id, date, start, end)).fetchone()
    conn.close()
    return row is not None

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        data = request.form
        try:
            conn=db()
            conn.execute("""INSERT INTO users(name,email,password,phone,vehicle_number,vehicle_type)
                            VALUES(?,?,?,?,?,?)""",
                         (data["name"],data["email"],data["password"],data["phone"],
                          data["vehicle_number"],data["vehicle_type"]))
            conn.commit(); conn.close()
            flash("Registration successful. Please login.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered.")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        conn=db()
        user=conn.execute("SELECT * FROM users WHERE email=? AND password=?",
                          (request.form["email"],request.form["password"])).fetchone()
        conn.close()
        if user:
            session["user_id"]=user["id"]; session["user_name"]=user["name"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session: return redirect(url_for("login"))
    conn=db()
    bookings=conn.execute("""SELECT b.*,s.slot_number,s.vehicle_type
                             FROM bookings b JOIN slots s ON b.slot_id=s.id
                             WHERE b.user_id=? ORDER BY b.id DESC""",(session["user_id"],)).fetchall()
    conn.close()
    return render_template("dashboard.html", bookings=bookings)

@app.route("/book", methods=["GET","POST"])
def book():
    if "user_id" not in session: return redirect(url_for("login"))
    conn=db()
    if request.method == "POST":
        date=request.form["date"]; start=request.form["start_time"]; end=request.form["end_time"]
        vtype=request.form["vehicle_type"]
        if start >= end:
            flash("End time must be later than start time.")
            conn.close(); return redirect(url_for("book"))
        slots=conn.execute("SELECT * FROM slots WHERE vehicle_type=? ORDER BY slot_number",(vtype,)).fetchall()
        chosen=None
        for s in slots:
            if not conflict(s["id"],date,start,end):
                chosen=s; break
        if not chosen:
            flash("No slot available for the selected time.")
            conn.close(); return redirect(url_for("book"))
        bid="PKG-"+datetime.now().strftime("%Y%m%d")+"-"+uuid.uuid4().hex[:6].upper()
        conn.execute("""INSERT INTO bookings(booking_id,user_id,slot_id,booking_date,start_time,end_time)
                        VALUES(?,?,?,?,?,?)""",
                     (bid,session["user_id"],chosen["id"],date,start,end))
        conn.commit(); conn.close()
        return render_template("confirmation.html", booking_id=bid, slot=chosen["slot_number"],
                               date=date,start=start,end=end)
    conn.close()
    return render_template("book.html")

@app.route("/operator", methods=["GET","POST"])
def operator():
    if request.method == "POST":
        action=request.form.get("action")
        conn=db()
        if action=="add_slot":
            try:
                conn.execute("INSERT INTO slots(slot_number,vehicle_type) VALUES(?,?)",
                             (request.form["slot_number"],request.form["vehicle_type"]))
                conn.commit(); flash("Slot added.")
            except sqlite3.IntegrityError: flash("Slot number already exists.")
        elif action=="entry":
            bid=request.form["booking_id"]
            b=conn.execute("SELECT * FROM bookings WHERE booking_id=? AND status='CONFIRMED'",(bid,)).fetchone()
            if b:
                exists=conn.execute("SELECT id FROM entry_exit WHERE booking_id=? AND exit_time IS NULL",(bid,)).fetchone()
                if not exists:
                    conn.execute("INSERT INTO entry_exit(booking_id,entry_time) VALUES(?,?)",
                                 (bid,datetime.now().isoformat(timespec="minutes")))
                    conn.execute("UPDATE bookings SET status='PARKED' WHERE booking_id=?",(bid,))
                    conn.commit(); flash("Vehicle entry recorded.")
                else: flash("Vehicle is already parked.")
            else: flash("Valid confirmed booking not found.")
        elif action=="exit":
            bid=request.form["booking_id"]
            e=conn.execute("SELECT * FROM entry_exit WHERE booking_id=? AND exit_time IS NULL",(bid,)).fetchone()
            if e:
                exit_dt=datetime.now()
                entry_dt=datetime.fromisoformat(e["entry_time"])
                hours=max(1, math.ceil((exit_dt-entry_dt).total_seconds()/3600))
                b=conn.execute("SELECT s.vehicle_type FROM bookings b JOIN slots s ON b.slot_id=s.id WHERE b.booking_id=?",(bid,)).fetchone()
                rate=20 if b["vehicle_type"]=="TWO_WHEELER" else 40
                charge=hours*rate
                conn.execute("""UPDATE entry_exit SET exit_time=?,duration_hours=?,charge=? WHERE id=?""",
                             (exit_dt.isoformat(timespec="minutes"),hours,charge,e["id"]))
                conn.execute("UPDATE bookings SET status='COMPLETED' WHERE booking_id=?",(bid,))
                conn.commit(); flash(f"Exit recorded. Charge: ₹{charge:.2f}")
            else: flash("Active parking record not found.")
        conn.close()
    conn=db()
    slots=conn.execute("SELECT * FROM slots ORDER BY slot_number").fetchall()
    bookings=conn.execute("""SELECT b.*,u.name,u.vehicle_number,s.slot_number,
                             e.entry_time,e.exit_time,e.duration_hours,e.charge
                             FROM bookings b JOIN users u ON b.user_id=u.id
                             JOIN slots s ON b.slot_id=s.id
                             LEFT JOIN entry_exit e ON b.booking_id=e.booking_id
                             ORDER BY b.id DESC""").fetchall()
    conn.close()
    return render_template("operator.html",slots=slots,bookings=bookings)

if __name__=="__main__":
    init_db()
    app.run(debug=True)
