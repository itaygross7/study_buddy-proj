#!/usr/bin/env python3
"""
Configuration and API Key Validation Tool
Checks all required configurations and provides actionable feedback
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_env_var(name, required=True, sensitive=False):
    """Check if an environment variable is set and valid."""
    value = os.getenv(name, '')
    
    if not value:
        status = "❌ MISSING" if required else "⚠️  OPTIONAL (not set)"
        return False, status, ""
    
    # Check for placeholder values
    placeholder_indicators = ['your_', 'change-this', 'example', 'here']
    if any(indicator in value.lower() for indicator in placeholder_indicators):
        return False, "❌ PLACEHOLDER", value if not sensitive else "***"
    
    display_value = value if not sensitive else f"{value[:10]}..." if len(value) > 10 else "***"
    return True, "✅ SET", display_value

def main():
    print("=" * 70)
    print("StudyBuddy Configuration Check")
    print("=" * 70)
    
    all_ok = True
    
    # Core Configuration
    print("\n📋 CORE CONFIGURATION")
    print("-" * 70)
    configs = [
        ("FLASK_ENV", False, False),
        ("SECRET_KEY", True, True),
        ("DOMAIN", True, False),
        ("BASE_URL", True, False),
    ]
    
    for name, required, sensitive in configs:
        ok, status, value = check_env_var(name, required, sensitive)
        print(f"{name:30s} {status:20s} {value}")
        if required and not ok:
            all_ok = False
    
    # Database & Queue
    print("\n🗄️  DATABASE & QUEUE")
    print("-" * 70)
    configs = [
        ("MONGO_URI", True, False),
        ("RABBITMQ_URI", True, False),
    ]
    
    for name, required, sensitive in configs:
        ok, status, value = check_env_var(name, required, sensitive)
        print(f"{name:30s} {status:20s} {value}")
        if required and not ok:
            all_ok = False
    
    # AI Services
    print("\n🤖 AI SERVICES")
    print("-" * 70)
    configs = [
        ("OPENAI_API_KEY", True, True),
        ("GEMINI_API_KEY", True, True),
        ("SB_OPENAI_MODEL", False, False),
        ("SB_GEMINI_MODEL", False, False),
        ("SB_DEFAULT_PROVIDER", False, False),
    ]
    
    openai_ok = gemini_ok = False
    for name, required, sensitive in configs:
        ok, status, value = check_env_var(name, required, sensitive)
        print(f"{name:30s} {status:20s} {value}")
        if name == "OPENAI_API_KEY":
            openai_ok = ok
        elif name == "GEMINI_API_KEY":
            gemini_ok = ok
        if required and not ok:
            all_ok = False
    
    if not openai_ok and not gemini_ok:
        print("\n⚠️  WARNING: At least one AI provider (OpenAI or Gemini) must be configured!")
        all_ok = False
    
    # Email Configuration
    print("\n📧 EMAIL CONFIGURATION (for verification)")
    print("-" * 70)
    configs = [
        ("MAIL_SERVER", False, False),
        ("MAIL_PORT", False, False),
        ("MAIL_USE_TLS", False, False),
        ("MAIL_USERNAME", False, True),
        ("MAIL_PASSWORD", False, True),
        ("MAIL_DEFAULT_SENDER", False, False),
    ]
    
    email_configured = True
    for name, required, sensitive in configs:
        ok, status, value = check_env_var(name, required, sensitive)
        print(f"{name:30s} {status:20s} {value}")
        if not ok:
            email_configured = False
    
    if not email_configured:
        print("\n⚠️  Email not fully configured - verification emails won't be sent")
    
    # OAuth Configuration
    print("\n🔐 OAUTH CONFIGURATION (Google Sign-In)")
    print("-" * 70)
    configs = [
        ("GOOGLE_CLIENT_ID", False, True),
        ("GOOGLE_CLIENT_SECRET", False, True),
    ]
    
    google_oauth_ok = True
    for name, required, sensitive in configs:
        ok, status, value = check_env_var(name, required, sensitive)
        print(f"{name:30s} {status:20s} {value}")
        if not ok:
            google_oauth_ok = False
    
    if not google_oauth_ok:
        print("\n⚠️  Google OAuth not configured - Google Sign-In won't work")
        print("   Get credentials from: https://console.cloud.google.com/")
        print(f"   Redirect URI: {os.getenv('BASE_URL', 'https://yourdomain.com')}/oauth/google/callback")
    
    # Admin Configuration
    print("\n👑 ADMIN CONFIGURATION")
    print("-" * 70)
    configs = [
        ("ADMIN_EMAIL", False, False),
        ("ADMIN_PASSWORD", False, True),
    ]
    
    for name, required, sensitive in configs:
        ok, status, value = check_env_var(name, required, sensitive)
        print(f"{name:30s} {status:20s} {value}")
    
    # Summary
    print("\n" + "=" * 70)
    if all_ok:
        print("✅ All required configurations are set!")
    else:
        print("❌ Some required configurations are missing or invalid!")
        print("\nPlease check the issues above and update your .env file.")
        print("Copy .env.example to .env and fill in your values:")
        print("  cp .env.example .env")
        print("  nano .env")
    
    print("=" * 70)
    
    # Test AI connections if keys are available
    if openai_ok or gemini_ok:
        print("\n🧪 TESTING AI CONNECTIONS")
        print("-" * 70)
        print("Note: This tests actual API connectivity with minimal requests")
        print()
        
        if openai_ok:
            print("Testing OpenAI connection...")
            try:
                import openai
                client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                # Test with models list endpoint (doesn't consume credits)
                models = client.models.list()
                print("✅ OpenAI connection successful!")
            except Exception as e:
                print(f"❌ OpenAI connection failed: {e}")
                all_ok = False
        
        if gemini_ok:
            print("Testing Gemini connection...")
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
                # List models to test connection (minimal API usage)
                models = genai.list_models()
                # Check if we have access to at least one model
                model_count = sum(1 for _ in models)
                if model_count > 0:
                    print("✅ Gemini connection successful!")
                else:
                    print("⚠️  Gemini API key valid but no models available")
            except Exception as e:
                print(f"❌ Gemini connection failed: {e}")
                all_ok = False
    
    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())
