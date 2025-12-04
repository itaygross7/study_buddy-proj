"""
Startup Configuration Validator
Checks critical configuration before app starts and provides helpful error messages
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

class ConfigurationError(Exception):
    """Raised when critical configuration is missing."""
    pass

def validate_configuration():
    """Validate all critical configuration and return helpful error messages."""
    errors = []
    warnings = []
    
    # Check AI providers
    openai_key = os.getenv('OPENAI_API_KEY', '')
    gemini_key = os.getenv('GEMINI_API_KEY', '')
    
    if not openai_key and not gemini_key:
        errors.append(
            "❌ NO AI PROVIDER CONFIGURED!\n"
            "   At least one AI provider must be configured:\n"
            "   - For OpenAI: Add OPENAI_API_KEY to .env (get from https://platform.openai.com/api-keys)\n"
            "   - For Gemini: Add GEMINI_API_KEY to .env (get from https://makersuite.google.com/app/apikey)\n"
            "   \n"
            "   Gemini is recommended (free tier available)."
        )
    
    if openai_key and any(x in openai_key.lower() for x in ['your_', 'example', 'here']):
        errors.append(
            "❌ OPENAI_API_KEY contains placeholder value!\n"
            "   Replace with actual API key from https://platform.openai.com/api-keys"
        )
    
    if gemini_key and any(x in gemini_key.lower() for x in ['your_', 'example', 'here']):
        errors.append(
            "❌ GEMINI_API_KEY contains placeholder value!\n"
            "   Replace with actual API key from https://makersuite.google.com/app/apikey"
        )
    
    # Check BASE_URL
    base_url = os.getenv('BASE_URL', '')
    if not base_url:
        warnings.append(
            "⚠️  BASE_URL not set in .env\n"
            "   This is needed for:\n"
            "   - Email verification links\n"
            "   - Google OAuth redirects\n"
            "   \n"
            "   Set to your domain or http://localhost:5000 for development"
        )
    
    # Check OAuth if configured
    google_id = os.getenv('GOOGLE_CLIENT_ID', '')
    google_secret = os.getenv('GOOGLE_CLIENT_SECRET', '')
    
    if google_id and not google_secret:
        warnings.append(
            "⚠️  GOOGLE_CLIENT_ID is set but GOOGLE_CLIENT_SECRET is missing\n"
            "   Google Sign-In will not work without both values"
        )
    elif google_secret and not google_id:
        warnings.append(
            "⚠️  GOOGLE_CLIENT_SECRET is set but GOOGLE_CLIENT_ID is missing\n"
            "   Google Sign-In will not work without both values"
        )
    
    if google_id and google_secret:
        if not base_url:
            warnings.append(
                "⚠️  Google OAuth configured but BASE_URL not set\n"
                "   OAuth callback will fail without proper BASE_URL"
            )
    
    # Check Email configuration
    mail_user = os.getenv('MAIL_USERNAME', '')
    mail_pass = os.getenv('MAIL_PASSWORD', '')
    
    if mail_user and not mail_pass:
        warnings.append(
            "⚠️  MAIL_USERNAME set but MAIL_PASSWORD missing\n"
            "   Email verification will not work"
        )
    elif mail_pass and not mail_user:
        warnings.append(
            "⚠️  MAIL_PASSWORD set but MAIL_USERNAME missing\n"
            "   Email verification will not work"
        )
    
    # Check SECRET_KEY
    secret_key = os.getenv('SECRET_KEY', '')
    if not secret_key or 'change-this' in secret_key.lower():
        warnings.append(
            "⚠️  SECRET_KEY not properly configured\n"
            "   Using default or placeholder value is insecure\n"
            "   Generate secure key: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
    
    return errors, warnings

def print_validation_results():
    """Print validation results and exit if critical errors found."""
    print("=" * 70)
    print("StudyBuddy Configuration Validation")
    print("=" * 70)
    print()
    
    errors, warnings = validate_configuration()
    
    if warnings:
        print("WARNINGS:")
        print("-" * 70)
        for warning in warnings:
            print(warning)
            print()
    
    if errors:
        print("CRITICAL ERRORS:")
        print("-" * 70)
        for error in errors:
            print(error)
            print()
        
        print("=" * 70)
        print("❌ Configuration validation FAILED!")
        print("=" * 70)
        print()
        print("Fix the errors above and restart the application.")
        print()
        print("Quick start:")
        print("  1. Copy .env.example to .env: cp .env.example .env")
        print("  2. Edit .env and add your API keys")
        print("  3. Restart: docker compose restart app")
        print()
        print("For detailed help, see TROUBLESHOOTING.md")
        print()
        
        return False
    
    if warnings:
        print("=" * 70)
        print("⚠️  Configuration validation completed with WARNINGS")
        print("=" * 70)
        print()
        print("The application will start, but some features may not work.")
        print("Review the warnings above and update your .env file.")
        print()
    else:
        print("=" * 70)
        print("✅ Configuration validation PASSED!")
        print("=" * 70)
        print()
    
    return True

if __name__ == '__main__':
    success = print_validation_results()
    sys.exit(0 if success else 1)
