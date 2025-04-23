from flask import Flask, render_template, request, redirect, flash, session
import mysql.connector
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
import re

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Replace with a secure key for production


def init_mysql_db():
    """Initialize MySQL database and create the required tables if they don't exist."""
    try:
        print("Connecting to MySQL server...")
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD
        )
        cursor = conn.cursor()
        print("Creating database if not exists...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DB}")
        conn.commit()
        cursor.close()
        conn.close()

        print("Connecting to the newly created database...")
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        cursor = conn.cursor()
        print("Creating tables if not exists...")
        # Create the `patients` table
        cursor.execute('''CREATE TABLE IF NOT EXISTS patients (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            name VARCHAR(255) NOT NULL,
                            age INT CHECK (age > 0),
                            weight FLOAT CHECK (weight > 0),
                            bp VARCHAR(255),
                            temperature FLOAT CHECK (temperature > 0),
                            symptoms TEXT,
                            medicines TEXT,
                            appointment_date DATE,
                            payment VARCHAR(50) DEFAULT 'Cash'
                        )''')
        # Create the `users` table
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_id VARCHAR(255) NOT NULL UNIQUE,
                            password VARCHAR(255) NOT NULL
                        )''')
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Database initialized successfully!")

    except mysql.connector.Error as e:
        print(f"❌ Database Initialization Error: {e}")


# Call the function to initialize the database
init_mysql_db()


@app.route('/')
def home():
    """Render the home page."""
    return render_template('home.html')


@app.route('/appointment')
def appointment():
    """Render the appointment registration form."""
    return render_template('user.html')


@app.route('/submit', methods=['POST'])
def submit():
    """Handles form submission and redirects back to the form for a new entry."""
    if request.method == 'POST':
        try:
            # Retrieve form data
            name = request.form.get('name')
            age = request.form.get('age')
            weight = request.form.get('weight')
            bp = request.form.get('bp')
            temperature = request.form.get('temperature')
            symptoms = request.form.get('symptoms')
            medicines = request.form.get('medicines')
            appointment_date = request.form.get('date')  # Retrieve appointment date
            payment = request.form.get('payment')  # Retrieve payment type

            # Insert patient data into the database
            conn = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB
            )
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO patients (name, age, weight, bp, temperature, symptoms, medicines, appointment_date, payment)
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                           (name, age, weight, bp, temperature, symptoms, medicines, appointment_date, payment))
            conn.commit()
            cursor.close()
            conn.close()

            flash("✅ Patient registered successfully! Please fill out the next form.", "success")
            return redirect('/appointment')  # Redirect back to the form
        except mysql.connector.Error as e:
            flash(f"❌ Database error: {e}", "danger")
            return redirect('/appointment')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')

        try:
            conn = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB
            )
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM users WHERE user_id = %s AND password = %s", (user_id, password))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user:
                session['logged_in'] = True
                flash("✅ Login successful!", "success")
                return redirect('/patients')  # Redirect to patients.html
            else:
                flash("❌ Invalid user ID or password.", "danger")
                return redirect('/login')

        except mysql.connector.Error as e:
            flash(f"❌ Database error: {e}", "danger")
            return redirect('/login')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Server-side validation for matching passwords
        if password != confirm_password:
            flash("❌ Passwords do not match. Please try again.", "danger")
            return redirect('/register')

        # Server-side validation for password strength
        regex = r"^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        if not re.match(regex, password):
            flash("❌ Password must contain at least one capital letter, one symbol, one number, and be at least 8 characters long.", "danger")
            return redirect('/register')

        try:
            conn = mysql.connector.connect(
                host=MYSQL_HOST,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB
            )
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (user_id, password) VALUES (%s, %s)", (user_id, password))
            conn.commit()
            cursor.close()
            conn.close()
            flash("✅ Registration successful! Please log in.", "success")
            return redirect('/login')
        except mysql.connector.Error as e:
            flash(f"❌ Database error: {e}", "danger")
            return redirect('/register')

    return render_template('register.html')


@app.route('/patients', methods=['GET'])
def list_patients():
    """Fetch and display the most recent 5 patients or search by name."""
    if not session.get('logged_in'):
        flash("❌ Please log in to access this page.", "danger")
        return redirect('/login')

    try:
        search_query = request.args.get('search')  # Get the search query from the URL parameters
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        cursor = conn.cursor(dictionary=True)

        if search_query:
            # Fetch patients whose names match the search query
            cursor.execute("SELECT * FROM patients WHERE name LIKE %s ORDER BY id DESC", (f"%{search_query}%",))
        else:
            # Fetch the most recent 5 patients
            cursor.execute("SELECT * FROM patients ORDER BY id DESC LIMIT 5")
        
        patients = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('patients.html', patients=patients)
    except mysql.connector.Error as e:
        flash(f"❌ Database error: {e}", "danger")
        return redirect('/')


@app.route('/logout')
def logout():
    """Log out the user."""
    session.pop('logged_in', None)
    flash("✅ You have been logged out.", "success")
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)