import hashlib

from flask import Flask, render_template, request, redirect, url_for,session,flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
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
    __tablename__ = 'placementDrive'
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(100), nullable=False)
    job_role = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    eligibility_criteria = db.Column(db.Text, nullable=False)
    application_deadline = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(50), default='Pending')
    company_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey('placementDrive.id'), nullable=False)
    status = db.Column(db.String(50), default='Applied')
    applied_on = db.Column(db.DateTime, default=datetime.utcnow)    


class companyProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    hr = db.Column(db.String(100), nullable=True)
    website = db.Column(db.String(255), nullable=True)

class studentProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    roll_number = db.Column(db.String(20), nullable=True)
    department = db.Column(db.String(50), nullable=True)
    year_of_study = db.Column(db.Integer, nullable=True)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/', methods=['GET', 'POST'])
def home():
    return login()

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
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            if not user.is_approved:
                flash('Your account is pending approval. Please wait for an admin to approve your account.')
                return render_template('login.html')
            
            login_user(user)
            flash('SUCCESS - redirecting...')  
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'student':
                return redirect(url_for('student_dashboard'))
            elif user.role == 'company':
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
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    stats={'students': User.query.filter_by(role='student').count(),
           'companies': User.query.filter_by(role='company').count(),
           'drives': placementDrive.query.count(),
           'applications': Application.query.count()}
    pending_users = User.query.filter_by(is_approved=False, is_active=True).all()
    pending_drives = placementDrive.query.filter_by(status='Pending').all()
    all_users = User.query.filter(User.role != 'admin').all()
    all_drives = placementDrive.query.all()
    return render_template('admin_dash.html', stats=stats, pending_users=pending_users, pending_drives=pending_drives, all_users=all_users, all_drives=all_drives)

@app.route('/admin/approve_user/<int:user_id>')
@login_required
def approve_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    user = User.query.get(user_id)
    if user:
        user.is_approved = True
        db.session.commit()
        flash(f'User {user.name} approved successfully!')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/approve_drive/<int:drive_id>')
@login_required
def approve_drive(drive_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    drive = placementDrive.query.get(drive_id)
    if drive:
        drive.status = 'Approved'
        db.session.commit()
        flash(f'Placement drive for {drive.job_role} approved successfully!')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject_drive/<int:drive_id>')
@login_required
def reject_drive(drive_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    drive = placementDrive.query.get(drive_id)
    if drive:
        drive.status = 'Rejected'
        db.session.commit()
        flash(f'Placement drive for {drive.job_role} rejected.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject_user/<int:user_id>')
@login_required
def reject_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if user:
        user.is_approved = False
        db.session.commit()
        flash(f'User {user.name} rejected.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/search', methods=['GET'])
@login_required
def search():
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    query = request.args.get('query')
    if query:
        users = User.query.filter(User.name.contains(query) | User.email.contains(query)).all()
        drives = placementDrive.query.filter(placementDrive.job_role.contains(query)).all()
    else:
        users = []
        drives = []

    return render_template('admin_search.html', users=users, drives=drives)
@app.route('/admin/all_users')
@login_required
def all_users():
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    users = User.query.filter(User.role != 'admin').all()
    return render_template('admin_all_users.html', users=users)

@app.route('/admin/all_drives')
@login_required
def all_drives():
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    drives = placementDrive.query.all()
    return render_template('admin_all_drives.html', drives=drives)

@app.route('/admin/blacklist_user/<int:user_id>')
@login_required
def blacklist_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if user:
        user.is_approved = False
        db.session.commit()
        flash(f'User {user.name} blacklisted.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/unblacklist_user/<int:user_id>')
@login_required
def unblacklist_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if user:
        user.is_approved = True
        db.session.commit()
        flash(f'User {user.name} unblacklisted.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/blacklist_drive/<int:drive_id>')
@login_required
def blacklist_drive(drive_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    drive = placementDrive.query.get(drive_id)
    if drive:
        drive.status = 'Rejected'
        db.session.commit()
        flash(f'Placement drive for {drive.job_role} blacklisted.')
    return redirect(url_for('admin_dashboard')) 

@app.route('/admin/unblacklist_drive/<int:drive_id>')
@login_required
def unblacklist_drive(drive_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    drive = placementDrive.query.get(drive_id)
    if drive:
        drive.status = 'Approved'
        db.session.commit()
        flash(f'Placement drive for {drive.job_role} unblacklisted.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.name} deleted.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_drive/<int:drive_id>')
@login_required 
def delete_drive(drive_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    drive = placementDrive.query.get(drive_id)
    if drive:
        db.session.delete(drive)
        db.session.commit()
        flash(f'Placement drive for {drive.job_role} deleted.')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/search_users', methods=['GET'])
@login_required
def search_users():
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    query = request.args.get('query')
    if query:
        users = User.query.filter(User.name.contains(query) | User.email.contains(query)).all()
    else:
        users = []
    return render_template('admin_search_users.html', users=users)

@app.route('/admin/user_details/<int:user_id>')
@login_required
def user_details(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user:
        flash('User not found.')
    profile=None
    if user.role == 'student':
        profile = studentProfile.query.filter_by(user_id=user.id).first()
    elif user.role == 'company':
        profile = companyProfile.query.filter_by(user_id=user.id).first()
    html = f"""
    <div class="detail-row"><span class="detail-label">Name:</span><span class="detail-value">{user.name}</span></div>
    <div class="detail-row"><span class="detail-label">Email:</span><span class="detail-value">{user.email}</span></div>
    <div class="detail-row"><span class="detail-label">Role:</span><span class="detail-value">{user.role.title()}</span></div>
    <div class="detail-row"><span class="detail-label">Status:</span>
        <span class="detail-value">
            {'Approved & Active' if user.is_approved and user.is_active else 
             'Pending Approval' if not user.is_approved else 'Blacklisted'}
        </span>
    </div>
    """
    
    if profile:
        if user.role == 'student':
            html += f"""
            <div class="detail-row"><span class="detail-label">Roll No:</span><span class="detail-value">{profile.roll_number or 'N/A'}</span></div>
            <div class="detail-row"><span class="detail-label">Department:</span><span class="detail-value">{profile.department or 'N/A'}</span></div>
            <div class="detail-row"><span class="detail-label">Year:</span><span class="detail-value">{profile.year_of_study or 'N/A'}</span></div>
            """
        elif user.role == 'company':
            html += f"""
            <div class="detail-row"><span class="detail-label">HR Contact:</span><span class="detail-value">{profile.hr or 'N/A'}</span></div>
            <div class="detail-row"><span class="detail-label">Website:</span><span class="detail-value">{profile.website or 'N/A'}</span></div>
            """
    apps_count = Application.query.filter_by(student_id=user_id).count() if user.role == 'student' else 0
    if apps_count:
        html += f'<div class="detail-row"><span class="detail-label">Applications:</span><span class="detail-value">{apps_count}</span></div>'
    
    return html 

@app.route('/admin/drive_details/<int:drive_id>')
@login_required
def drive_details(drive_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))

    drive = placementDrive.query.get(drive_id)
    if not drive:
        flash('Drive not found.')
        return redirect(url_for('admin_dashboard'))

    apps_count = Application.query.filter_by(drive_id=drive_id).count()
    company = User.query.get(drive.company_id)
    
    html = f"""
    <div class="detail-row"><span class="detail-label">Company:</span><span class="detail-value">{drive.company_name}</span></div>
    <div class="detail-row"><span class="detail-label">Job Role:</span><span class="detail-value">{drive.job_role}</span></div>
    <div class="detail-row"><span class="detail-label">Status:</span><span class="detail-value">{drive.status}</span></div>
    <div class="detail-row"><span class="detail-label">Deadline:</span><span class="detail-value">{drive.application_deadline.strftime('%Y-%m-%d %H:%M')}</span></div>
    <div class="detail-row"><span class="detail-label">Applications:</span><span class="detail-value">{apps_count}</span></div>
    <div class="detail-row"><span class="detail-label">Description:</span><span class="detail-value">{drive.description[:200]}{'...' if len(drive.description) > 200 else ''}</span></div>
    <div class="detail-row"><span class="detail-label">Eligibility:</span><span class="detail-value">{drive.eligibility_criteria[:200]}{'...' if len(drive.eligibility_criteria) > 200 else ''}</span></div>
    """
    
    if company:
        html += f'<div class="detail-row"><span class="detail-label">Company Email:</span><span class="detail-value">{company.email}</span></div>'
    
    return html

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

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    if current_user.role != 'student':
        return redirect(url_for('login'))
    
    profile = studentProfile.query.filter_by(user_id=current_user.id).first()
    if not profile:
        profile = studentProfile(user_id=current_user.id)
        db.session.add(profile)
        db.session.commit()

    if request.method == 'POST':
        profile.roll_number = request.form['roll_number']
        profile.department = request.form['department']
        profile.year_of_study = int(request.form['year_of_study'])
        db.session.commit()
        flash('Profile updated successfully!')
        return redirect(url_for('student_profile'))

    return render_template('student_profile.html', profile=profile)

@app.route('/company/dashboard')
@login_required
def company_dashboard():
    if current_user.role != 'company' or not current_user.is_approved:
        return redirect(url_for('login'))
    drives = placementDrive.query.filter_by(company_id=current_user.id).all()
    apps = Application.query.join(placementDrive).filter(placementDrive.company_id == current_user.id).all()
    return render_template('company_dash.html', drives=drives, applications=apps)

@app.route('/company/create_drive', methods=['GET', 'POST'])
@login_required
def create_drive():
    if current_user.role != 'company' or not current_user.is_approved:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        new_drive = placementDrive(
            company_id=current_user.id,
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

@app.route('/company/update_app_status/<int:app_id>', methods=['GET', 'POST'])
@login_required
def update_app_status(app_id):
    if current_user.role != 'company' or not current_user.is_approved:
        return redirect(url_for('login'))

    application = Application.query.get(app_id)
    if request.method == 'POST':
        application.status = request.form['status']
        db.session.commit()
        flash('Application status updated!')
    return redirect(url_for('company_dashboard'))

def init_db():  
    with app.app_context():
        db.create_all()
        admin_count = User.query.filter_by(email='admin@example.com').count()
        if admin_count == 0:
            admin_user = User(
                email='admin@example.com',
                password=generate_password_hash('adminpassword'),
                role='admin',
                name='Admin User',
                is_approved=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print('Admin user created with email: admin@example.com and password: adminpassword')

if __name__ == '__main__':
    init_db()
    app.run(debug=True) 