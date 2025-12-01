"""Authentication routes for login, signup, and user management."""
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from src.infrastructure.database import db
from src.services import auth_service, email_service
from src.domain.models.db_models import UserRole
from sb_utils.logger_utils import logger

auth_bp = Blueprint('auth', __name__)

# Initialize Login Manager
login_manager = LoginManager()


class FlaskUser:
    """Flask-Login compatible user wrapper."""
    def __init__(self, user):
        self.user = user
        self.id = user.id
        self.is_authenticated = True
        self.is_active = user.is_active
        self.is_anonymous = False
        
    def get_id(self):
        return self.id


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    user = auth_service.get_user_by_id(db, user_id)
    if user:
        return FlaskUser(user)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    """Handle unauthorized access."""
    if request.path.startswith('/api/'):
        return jsonify({"error": "Authentication required"}), 401
    flash('יש להתחבר כדי לגשת לעמוד זה', 'warning')
    return redirect(url_for('auth.login', next=request.url))


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.user.role != UserRole.ADMIN:
            flash('אין לך הרשאה לגשת לעמוד זה', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not email or not password:
            flash('יש למלא את כל השדות', 'error')
            return render_template('auth/login.html')
        
        user = auth_service.authenticate_user(db, email, password)
        if user:
            if not user.is_verified:
                flash('יש לאמת את האימייל לפני ההתחברות', 'warning')
                return render_template('auth/login.html')
            
            login_user(FlaskUser(user), remember=bool(remember))
            logger.info(f"User logged in: {email}")
            
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            flash('אימייל או סיסמה שגויים', 'error')
    
    return render_template('auth/login.html')


@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    """Signup page and handler."""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        name = request.form.get('name', '').strip()
        
        # Validation
        if not email or not password:
            flash('יש למלא את כל השדות', 'error')
            return render_template('auth/signup.html')
        
        if password != confirm_password:
            flash('הסיסמאות אינן תואמות', 'error')
            return render_template('auth/signup.html')
        
        if len(password) < 8:
            flash('הסיסמה חייבת להכיל לפחות 8 תווים', 'error')
            return render_template('auth/signup.html')
        
        try:
            user = auth_service.create_user(db, email, password, name)
            
            # Send verification email
            base_url = request.url_root.rstrip('/')
            email_service.send_verification_email(email, user.verification_token, base_url)
            
            # Notify admin of new user
            email_service.send_new_user_notification(email, name)
            
            flash('נרשמת בהצלחה! בדוק את האימייל שלך לאימות', 'success')
            return redirect(url_for('auth.login'))
            
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            logger.error(f"Signup error: {e}", exc_info=True)
            email_service.send_error_notification("Signup Error", str(e))
            flash('אירעה שגיאה, נסה שוב מאוחר יותר', 'error')
    
    return render_template('auth/signup.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout the current user."""
    logout_user()
    flash('התנתקת בהצלחה', 'success')
    return redirect(url_for('index'))


@auth_bp.route('/verify/<token>')
def verify_email(token):
    """Verify user email with token."""
    if auth_service.verify_user_email(db, token):
        flash('האימייל אומת בהצלחה! כעת ניתן להתחבר', 'success')
    else:
        flash('קישור האימות אינו תקף או שהאימייל כבר אומת', 'error')
    return redirect(url_for('auth.login'))


@auth_bp.route('/resend-verification', methods=['POST'])
def resend_verification():
    """Resend verification email."""
    email = request.form.get('email', '').strip()
    if not email:
        flash('יש להזין כתובת אימייל', 'error')
        return redirect(url_for('auth.login'))
    
    user = auth_service.get_user_by_email(db, email)
    if user and not user.is_verified and user.verification_token:
        base_url = request.url_root.rstrip('/')
        email_service.send_verification_email(email, user.verification_token, base_url)
        flash('אימייל אימות נשלח מחדש', 'success')
    else:
        flash('לא נמצא משתמש עם אימייל זה או שהאימייל כבר אומת', 'error')
    
    return redirect(url_for('auth.login'))
