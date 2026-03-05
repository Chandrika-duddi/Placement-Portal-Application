import hashlib

from flask import Flask, render_template, request, redirect, url_for,session,flash
app=Flask(__name__)
app.secret_key = 'your_secret_key' 

users = {}
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()
        role = request.form['role'] 
        
        if email in users:
            flash('Email already registered!')
            return render_template('register_form.html')
        
        users[email] = {'password': password, 'role': role}
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register_form.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hashlib.sha256(request.form['password'].encode()).hexdigest()

        if email in users and users[email]['password'] == password:
            session['email'] = email
            session['role'] = users[email]['role']
            flash('Login successful!')
            if session['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif session['role'] == 'student':
                return redirect(url_for('student_dashboard'))
            elif session['role'] == 'company':
                return redirect(url_for('company_dashboard'))
        else:
            flash('Invalid email or password!')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!')
    return redirect(url_for('login'))
@app.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    return render_template('admin_dash.html')

@app.route('/student/dashboard')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    return render_template('student_dash.html')

@app.route('/company/dashboard')
def company_dashboard():
    if session.get('role') != 'company':
        return redirect(url_for('login'))
    return render_template('company_dash.html')

if __name__ == '__main__':
    app.run(debug=True) 
