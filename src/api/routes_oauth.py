"""OAuth routes for Google and Apple Sign-In."""
import uuid
from datetime import datetime, timezone
from flask import Blueprint, redirect, url_for, flash, session, request
from flask_login import login_user
from authlib.integrations.flask_client import OAuth

from src.infrastructure.config import settings
from src.infrastructure.database import db
from src.domain.models.db_models import User, UserRole
from src.services import auth_service, email_service
from sb_utils.logger_utils import logger

oauth_bp = Blueprint('oauth', __name__)

# Initialize OAuth
oauth = OAuth()

def init_oauth(app):
    """Initialize OAuth with the Flask app."""
    oauth.init_app(app)
    
    # Register Google OAuth
    if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
        oauth.register(
            name='google',
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
        logger.info("Google OAuth configured")
    
    # Register Apple OAuth (if configured)
    if settings.APPLE_CLIENT_ID and settings.APPLE_TEAM_ID:
        oauth.register(
            name='apple',
            client_id=settings.APPLE_CLIENT_ID,
            client_secret=_generate_apple_client_secret(),
            authorize_url='https://appleid.apple.com/auth/authorize',
            access_token_url='https://appleid.apple.com/auth/token',
            client_kwargs={
                'scope': 'name email',
                'response_mode': 'form_post'
            }
        )
        logger.info("Apple OAuth configured")


def _generate_apple_client_secret():
    """Generate Apple client secret JWT (required for Apple Sign-In)."""
    if not settings.APPLE_PRIVATE_KEY:
        return ''
    
    import jwt
    import time
    
    headers = {
        'kid': settings.APPLE_KEY_ID,
        'alg': 'ES256'
    }
    
    payload = {
        'iss': settings.APPLE_TEAM_ID,
        'iat': int(time.time()),
        'exp': int(time.time()) + 86400 * 180,  # 6 months
        'aud': 'https://appleid.apple.com',
        'sub': settings.APPLE_CLIENT_ID
    }
    
    return jwt.encode(payload, settings.APPLE_PRIVATE_KEY, algorithm='ES256', headers=headers)


def _get_or_create_oauth_user(email: str, name: str, provider: str):
    """Get existing user or create new one from OAuth data."""
    # Check if user exists
    existing_user = db.users.find_one({"email": email.lower()})
    
    if existing_user:
        # Update last login
        db.users.update_one(
            {"_id": existing_user["_id"]},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )
        user = User(**existing_user)
        logger.info(f"OAuth login: {email} via {provider}")
        return user
    
    # Create new user (auto-verified since OAuth verified email)
    user_id = str(uuid.uuid4())
    is_admin = email.lower() == settings.ADMIN_EMAIL.lower() if settings.ADMIN_EMAIL else False
    
    user = User(
        _id=user_id,
        email=email.lower(),
        password_hash="",  # No password for OAuth users
        name=name or email.split('@')[0],
        role=UserRole.ADMIN if is_admin else UserRole.USER,
        is_verified=True,  # OAuth users are pre-verified
        created_at=datetime.now(timezone.utc),
        last_login=datetime.now(timezone.utc)
    )
    
    db.users.insert_one(user.to_dict())
    logger.info(f"New OAuth user created: {email} via {provider}")
    
    # Send notification to admin
    if settings.ADMIN_EMAIL and not is_admin:
        try:
            email_service.send_new_user_notification(user)
        except Exception as e:
            logger.warning(f"Failed to send new user notification: {e}")
    
    return user


# ============ Google OAuth Routes ============

@oauth_bp.route('/google/login')
def google_login():
    """Initiate Google OAuth login."""
    if not settings.GOOGLE_CLIENT_ID:
        flash('התחברות עם Google לא מוגדרת', 'error')
        return redirect(url_for('auth.login'))
    
    redirect_uri = url_for('oauth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@oauth_bp.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback."""
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if not user_info or not user_info.get('email'):
            flash('לא הצלחנו לקבל מידע מ-Google', 'error')
            return redirect(url_for('auth.login'))
        
        email = user_info['email']
        name = user_info.get('name', '')
        
        # Get or create user
        user = _get_or_create_oauth_user(email, name, 'google')
        
        # Check if user is active
        if not user.is_active:
            flash('החשבון שלך מושהה. פנה למנהל.', 'error')
            return redirect(url_for('auth.login'))
        
        # Create user wrapper and login
        user_wrapper = auth_service.UserWrapper(user)
        login_user(user_wrapper, remember=True)
        
        flash(f'שלום {user.name}! התחברת בהצלחה 🦫', 'success')
        return redirect(url_for('library.index'))
        
    except Exception as e:
        logger.error(f"Google OAuth error: {e}", exc_info=True)
        flash('שגיאה בהתחברות עם Google. נסה שוב.', 'error')
        return redirect(url_for('auth.login'))


# ============ Apple OAuth Routes ============

@oauth_bp.route('/apple/login')
def apple_login():
    """Initiate Apple Sign-In."""
    if not settings.APPLE_CLIENT_ID:
        flash('התחברות עם Apple לא מוגדרת', 'error')
        return redirect(url_for('auth.login'))
    
    redirect_uri = url_for('oauth.apple_callback', _external=True)
    return oauth.apple.authorize_redirect(redirect_uri)


@oauth_bp.route('/apple/callback', methods=['GET', 'POST'])
def apple_callback():
    """Handle Apple Sign-In callback."""
    try:
        token = oauth.apple.authorize_access_token()
        
        # Apple returns user info in id_token
        id_token = token.get('id_token')
        if not id_token:
            flash('לא הצלחנו לקבל מידע מ-Apple', 'error')
            return redirect(url_for('auth.login'))
        
        # Decode the id_token (Apple uses JWT)
        import jwt
        # Note: In production, verify the token signature
        user_info = jwt.decode(id_token, options={"verify_signature": False})
        
        email = user_info.get('email')
        if not email:
            flash('לא הצלחנו לקבל את האימייל מ-Apple', 'error')
            return redirect(url_for('auth.login'))
        
        # Apple only sends name on first login
        name = ''
        if 'user' in request.form:
            import json
            user_data = json.loads(request.form['user'])
            name = f"{user_data.get('name', {}).get('firstName', '')} {user_data.get('name', {}).get('lastName', '')}".strip()
        
        # Get or create user
        user = _get_or_create_oauth_user(email, name, 'apple')
        
        # Check if user is active
        if not user.is_active:
            flash('החשבון שלך מושהה. פנה למנהל.', 'error')
            return redirect(url_for('auth.login'))
        
        # Create user wrapper and login
        user_wrapper = auth_service.UserWrapper(user)
        login_user(user_wrapper, remember=True)
        
        flash(f'שלום {user.name}! התחברת בהצלחה 🦫', 'success')
        return redirect(url_for('library.index'))
        
    except Exception as e:
        logger.error(f"Apple OAuth error: {e}", exc_info=True)
        flash('שגיאה בהתחברות עם Apple. נסה שוב.', 'error')
        return redirect(url_for('auth.login'))
