#!/usr/bin/env python3
"""
Configuration and API Key Validation Tool
Checks all required configurations for Cloudflare Tunnel setup
"""
import os
import sys
# Try to import dotenv, handle if missing
try:
    from dotenv import load_dotenv
except ImportError:
    print("❌ Error: python-dotenv not installed.")
    print("Run: pip install python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv()

def check_env_var(name, required=True, sensitive=False):
    """Check if an environment variable is set and valid."""
    value = os.getenv(name, '')
    
    if not value:
        status = "❌ MISSING" if required else "⚠️  OPTIONAL (not set)"
        return False, status, ""
    
    # Check for placeholder values
    placeholder_indicators = ['your_', 'change-this', 'example', 'here', 'paste_token']
    if any(indicator in value.lower() for indicator in placeholder_indicators):
        return False, "❌ PLACEHOLDER", value if not sensitive else "***"
    
    display_value = value if not sensitive else f"{value[:10]}..." if len(value) > 10 else "***"
    return True, "✅ SET", display_value

def main():
    print("=" * 70)
    print("StudyBuddy Configuration Check (Cloudflare Edition)")
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
        # ADDED: Essential for Cloudflare Tunnel
        ("TUNNEL_TOKEN", True, True), 
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
    print("\n📧 EMAIL CONFIGURATION")
    print("-" * 70)
    configs = [
        ("MAIL_USERNAME", False, True),
        ("MAIL_PASSWORD", False, True),
    ]
    
    for name, required, sensitive in configs:
        ok, status, value = check_env_var(name, required, sensitive)
        print(f"{name:30s} {status:20s} {value}")
    
    # Summary
    print("\n" + "=" * 70)
    if all_ok:
        print("✅ All required configurations are set!")
        return 0
    else:
        print("❌ Some required configurations are missing or invalid!")
        return 1

if __name__ == '__main__':
    sys.exit(main())
