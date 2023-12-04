from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Replace with a strong secret key



# Function to connect to the SQLite database
def get_db_connection():
    conn = sqlite3.connect('todo.db')
    conn.row_factory = sqlite3.Row
    return conn

# Function to create the user and tasks tables in the database
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            fullname TEXT,
            email TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            task_content TEXT,
            prio INTEGER,
            dd DATE,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    conn.commit()
    conn.close()

# Initialize the user table
create_tables()

# User registration route
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']

        # Hash the password before storing it
        hashed_password = generate_password_hash(password, method='sha256')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (fullname, email, username, password_hash) VALUES (?, ?, ?, ?)", (fullname, email, username, hashed_password))
        conn.commit()
        conn.close()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template("register.html")

# User login route
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template("login.html")

# User logout route
@app.route("/logout")
def logout():
    session.pop('user_id', None)
    flash('Logout successful!', 'success')
    return redirect(url_for('home'))

# Home Page route
@app.route("/")
def home():
    return render_template("register.html")

# Route to form used to add a new task to the database
@app.route("/enternew")
def enternew():
    if 'user_id' in session:
        return render_template("task.html")
    else:
        flash('Unauthorized access. Please log in.', 'danger')
        return redirect(url_for('login'))

# Route to add a new record (INSERT) task data to the database
@app.route("/addrec", methods=['POST', 'GET'])
def addrec():
    if 'user_id' in session:
        if request.method == 'POST':
            try:
                task = request.form['task']
                task_content = request.form['task_content']
                prio = request.form['prio']
                dd = request.form['dd']
                user_id = session['user_id']

                # Connect to SQLite3 database and execute the INSERT
                with sqlite3.connect('todo.db') as con:
                    cur = con.cursor()
                    cur.execute("INSERT INTO tasks (task, task_content, prio, dd, user_id) VALUES (?,?,?,?,?)",
                                (task, task_content, prio, dd, user_id))

                    con.commit()
                    msg = "Record successfully added to the database"
            except:
                con.rollback()
                msg = "Error in the INSERT"

            finally:
                con.close()
                # Send the transaction message to result.html
                return render_template('result.html', msg=msg)
    else:
        flash('Unauthorized access. Please log in.', 'danger')
        return redirect(url_for('login'))

# Route to SELECT all data from the database and display in a table      
@app.route('/list')
def list():
    if 'user_id' in session:
        user_id = session['user_id']
        # Connect to the SQLite3 database and SELECT rowid and all Rows from the tasks table.
        con = sqlite3.connect("todo.db")
        con.row_factory = sqlite3.Row

        cur = con.cursor()
        cur.execute("SELECT rowid, * FROM tasks WHERE user_id=?", (user_id,))

        rows = cur.fetchall()
        con.close()
        # Send the results of the SELECT to the list.html page
        return render_template("list.html", rows=rows)
    else:
        flash('Unauthorized access. Please log in.', 'danger')
        return redirect(url_for('login'))

# Route that will SELECT a specific row in the database then load an Edit form 
@app.route("/edit/<row_id>", methods=['POST', 'GET'])
def edit(row_id):
    rows = None
        
    if request.method == 'POST':
        try:
            # Use the hidden input value of id from the form to get the rowid
            id = row_id
            # Connect to the database and SELECT a specific rowid
            con = sqlite3.connect("todo.db")
            con.row_factory = sqlite3.Row

            cur = con.cursor()
            cur.execute("SELECT rowid, * FROM tasks WHERE rowid = " + id)

            rows = cur.fetchall()
        except:
            id = None
        finally:
            con.close()
    
    # Check if rows is not None before iterating over it
    if rows is not None:
        # Send the specific record of data to edit.html
        return render_template("edit.html", rows=rows)
    else:
        # Handle the case when rows is None (no data found)
        return render_template("edit.html", rows=[])

# Route used to execute the UPDATE statement on a specific record in the database
@app.route("/editrec/<int:row_id>", methods=['POST', 'GET'])
def editrec(row_id):
    if 'user_id' in session:
        # Data will be available from POST submitted by the form
        if request.method == 'POST':
            con = None # Define con outside the try block
            try:
                # Use the hidden input value of id from the form to get the rowid
                rowid = row_id
                task = request.form['task']
                task_content = request.form['task_content']
                prio = request.form['prio']
                dd = request.form['dd']

                user_id = session['user_id']

                # UPDATE a specific record in the database based on the rowid and user_id
                con =sqlite3.connect('todo.db')
                cur = con.cursor()
                cur.execute("UPDATE tasks SET task=?, task_content=?, prio=?, dd=? WHERE rowid=? AND user_id=?",
                            (task, task_content, prio, dd, rowid, user_id))

                con.commit()
                msg = "Record successfully edited in the database"
            except:
                if con:
                    con.rollback()
                msg = "Error in the Edit"
            finally:
                if con:
                    con.close()
                # Send the transaction message to result.html
                return render_template('result.html', msg=msg)
    else:
        flash('Unauthorized access. Please log in.', 'danger')
        return redirect(url_for('login'))

# Route used to DELETE a specific record in the database    
@app.route("/delete", methods=['POST', 'GET'])
def delete():
    if 'user_id' in session:
        # Data will be available from POST submitted by the form
        if request.method == 'POST':
            try:
                # Use the hidden input value of id from the form to get the rowid
                rowid = request.form['id']

                user_id = session['user_id']

                # Connect to the database and DELETE a specific record based on rowid and user_id
                with sqlite3.connect('todo.db') as con:
                    cur = con.cursor()
                    cur.execute("DELETE FROM tasks WHERE rowid=? AND user_id=?", (rowid, user_id))

                    con.commit()
                    msg = "Record successfully deleted from the database"
            except:
                con.rollback()
                msg = "Error in the DELETE"
            finally:
                con.close()
                # Send the transaction message to result.html
                return render_template('result.html', msg=msg)
    else:
        flash('Unauthorized access. Please log in.', 'danger')
        return redirect(url_for('login'))
    
# Protected route for authenticated users
@app.route("/dashboard")
def dashboard():
    if 'user_id' in session:
        return render_template('task.html')
    else:
        flash('Unauthorized access. Please log in.', 'danger')
        return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
