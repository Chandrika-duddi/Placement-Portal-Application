import hashlib

from flask import Flask, app, render_template, request, redirect, url_for,session,flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

class placementDrive(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    job_role = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    eligibility_criteria = db.Column(db.Text, nullable=False)
    application_deadline = db.Column(db.DateTime, nullable=False)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey('placement_drive.id'), nullable=False)
    status = db.Column(db.String(50), default='Applied')
    applied_on = db.Column(db.DateTime, default=datetime.utcnow)    

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        if User.query.filter_by(email=email).first():
            flash('Email already registered!')
            return render_template('register_form.html')
        
        user=User(
            email=email,
            password=generate_password_hash(request.form['password']),
            role=request.form['role'],
            name=request.form['name']
        )
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    
    return render_template('register_form.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user=User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.password, request.form['password']):
            if not user.is_approved and user.is_active:
                flash('Your account is pending approval. Please wait for admin approval.')
                return render_template('login.html')
            login_user(user)
            session['role'] = user.role
            flash('Logged in successfully!')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'student':
                return redirect(url_for('student_dashboard'))
            elif user.role == 'company':
                return redirect(url_for('company_dashboard'))
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

    stats={'students': User.query.filter_by(role='student').count(),
           'companies': User.query.filter_by(role='company').count(),
           'drives': placementDrive.query.count(),
           'applications': Application.query.count()}
    pending_users = User.query.filter_by(is_approved=False, is_active=True).all()
    pending_drives = placementDrive.query.filter_by(status='Pending').all()
    return render_template('admin_dash.html', stats=stats, pending_users=pending_users, pending_drives=pending_drives)

@app.route('/admin/approve_user/<int:user_id>')
def approve_user(user_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    
    user = User.query.get(user_id)
    if user:
        user.is_approved = True
        db.session.commit()
        flash(f'User {user.name} approved successfully!')
    return redirect(url_for('admin_dashboard'))

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('login'))
    approved_drives = placementDrive.query.filter_by(status='Approved').all()
    my_applications = Application.query.filter_by(student_id=current_user.id).all()
    return render_template('student_dash.html', drives=approved_drives, applications=my_applications)

@app.route('/student/apply/<int:drive_id>')
@login_required
def apply_drive(drive_id):
    if current_user.role != 'student':
        return redirect(url_for('login'))
    
    existing_application = Application.query.filter_by(student_id=current_user.id, drive_id=drive_id).first()
    if existing_application:
        flash('You have already applied for this drive.')
        return redirect(url_for('student_dashboard'))
    
    new_application = Application(student_id=current_user.id, drive_id=drive_id)
    db.session.add(new_application)
    db.session.commit()
    flash('Application submitted successfully!')
    return redirect(url_for('student_dashboard'))

@app.route('/company/dashboard')
@login_required
def company_dashboard():
    if current_user.role != 'company' or not current_user.is_approved:
        return redirect(url_for('login'))
    drives = placementDrive.query.filter_by(company_name=current_user.name).all()
    apps = db.session.query(Application, User).join(placementDrive).filter(placementDrive.company_id == current_user.id).all()
    return render_template('company_dash.html', drives=drives, applications=apps)

@app.route('/company/create_drive', methods=['GET', 'POST'])
@login_required
def create_drive():
    if current_user.role != 'company' or not current_user.is_approved:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_drive = placementDrive(
            company_name=current_user.name,
            job_role=request.form['job_role'],
            description=request.form['description'],
            eligibility_criteria=request.form['eligibility_criteria'],
            application_deadline=datetime.strptime(request.form['application_deadline'], '%Y-%m-%d'),
            status='Pending'
        )
        db.session.add(new_drive)
        db.session.commit()
        flash('Placement drive created and pending approval!')
        return redirect(url_for('company_dashboard'))
    
    return render_template('create_drive.html')

def init_db():  
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(email='admin@example.com').first():
            admin_user = User(
                email='admin@example.com',
                password=generate_password_hash('adminpassword'),
                role='admin',
                name='Admin User',
                is_approved=True
            )
            db.session.add(admin_user)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True) 