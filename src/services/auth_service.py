"""Authentication service for user management."""
import uuid
import secrets
from datetime import datetime, timezone
from typing import Optional
import bcrypt

from src.domain.models.db_models import User, UserRole
from src.infrastructure.config import settings
from sb_utils.logger_utils import logger


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))


def generate_verification_token() -> str:
    """Generate a secure verification token."""
    return secrets.token_urlsafe(32)


def create_user(db, email: str, password: str, name: str = "") -> User:
    """Create a new user."""
    # Check if user already exists
    existing = db.users.find_one({"email": email.lower()})
    if existing:
        raise ValueError("Email already registered")
    
    # Determine role (admin if email matches ADMIN_EMAIL)
    role = UserRole.ADMIN if email.lower() == settings.ADMIN_EMAIL.lower() and settings.ADMIN_EMAIL else UserRole.USER
    
    user = User(
        _id=str(uuid.uuid4()),
        email=email.lower(),
        password_hash=hash_password(password),
        name=name,
        role=role,
        is_verified=False,
        verification_token=generate_verification_token(),
        created_at=datetime.now(timezone.utc)
    )
    
    db.users.insert_one(user.to_dict())
    logger.info(f"Created new user: {email} with role: {role.value}")
    return user


def authenticate_user(db, email: str, password: str) -> Optional[User]:
    """Authenticate a user by email and password."""
    user_data = db.users.find_one({"email": email.lower()})
    if not user_data:
        return None
    
    user = User(**user_data)
    if not verify_password(password, user.password_hash):
        return None
    
    if not user.is_active:
        return None
    
    # Update last login
    db.users.update_one(
        {"_id": user.id},
        {"$set": {"last_login": datetime.now(timezone.utc)}}
    )
    
    logger.info(f"User authenticated: {email}")
    return user


def get_user_by_id(db, user_id: str) -> Optional[User]:
    """Get a user by their ID."""
    user_data = db.users.find_one({"_id": user_id})
    return User(**user_data) if user_data else None


def get_user_by_email(db, email: str) -> Optional[User]:
    """Get a user by their email."""
    user_data = db.users.find_one({"email": email.lower()})
    return User(**user_data) if user_data else None


def verify_user_email(db, token: str) -> bool:
    """Verify a user's email using their verification token."""
    result = db.users.update_one(
        {"verification_token": token, "is_verified": False},
        {"$set": {"is_verified": True, "verification_token": None}}
    )
    if result.modified_count > 0:
        logger.info("User email verified successfully")
        return True
    return False


def get_all_users(db, skip: int = 0, limit: int = 50):
    """Get all users (for admin panel)."""
    users = []
    for user_data in db.users.find().skip(skip).limit(limit):
        users.append(User(**user_data))
    return users


def get_user_count(db) -> int:
    """Get total user count."""
    return db.users.count_documents({})


def update_user_status(db, user_id: str, is_active: bool) -> bool:
    """Update a user's active status."""
    result = db.users.update_one(
        {"_id": user_id},
        {"$set": {"is_active": is_active}}
    )
    return result.modified_count > 0


def delete_user(db, user_id: str) -> bool:
    """Delete a user."""
    result = db.users.delete_one({"_id": user_id})
    return result.deleted_count > 0


def increment_prompt_count(db, user_id: str) -> int:
    """Increment user's prompt count and return new count."""
    result = db.users.find_one_and_update(
        {"_id": user_id},
        {"$inc": {"prompt_count": 1}},
        return_document=True
    )
    return result.get("prompt_count", 0) if result else 0


def reset_password(db, email: str, new_password: str) -> bool:
    """Reset a user's password."""
    result = db.users.update_one(
        {"email": email.lower()},
        {"$set": {"password_hash": hash_password(new_password)}}
    )
    return result.modified_count > 0
