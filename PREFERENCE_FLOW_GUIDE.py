"""
Complete User Preference Flow - From Consent to Personalized Prompts

This document shows how user preferences flow through the system:
1. User gives consent
2. Preferences are collected  
3. Preferences are stored
4. Optimizer receives preferences
5. Prompts are personalized

🎯 COMPLETE INTEGRATION GUIDE
"""

from typing import Dict, Any
from src.services.preference_consent import (
    consent_manager,
    get_consent_prompt_hebrew,
    get_quick_questions_hebrew,
    process_preference_responses
)
from src.services.ai_middleware import ai_middleware, UserPreferences


# ============================================================================
# STEP 1: CHECK IF USER HAS GIVEN CONSENT
# ============================================================================

def check_user_consent_status(user_id: str) -> Dict[str, Any]:
    """
    Check if we should ask user for preferences.
    
    Returns:
        {
            "should_ask": bool,
            "has_preferences": bool,
            "consent_prompt": dict (if should_ask)
        }
    """
    # Check if we should ask for consent
    should_ask = consent_manager.should_ask_for_consent(user_id)
    
    if not should_ask:
        # User already has preferences or declined recently
        return {
            "should_ask": False,
            "has_preferences": True,
            "message": "User already configured"
        }
    
    # Get the consent prompt to show user
    consent_prompt = get_consent_prompt_hebrew()
    
    return {
        "should_ask": True,
        "has_preferences": False,
        "consent_prompt": consent_prompt
    }


# ============================================================================
# STEP 2: USER RESPONDS TO CONSENT PROMPT
# ============================================================================

def handle_consent_response(user_id: str, response: str) -> Dict[str, Any]:
    """
    Handle user's consent response.
    
    Args:
        user_id: User ID
        response: "yes", "later", or "no"
        
    Returns:
        Next action to take
    """
    if response == "yes":
        # User agreed! Show preference questions
        questions = get_quick_questions_hebrew()
        
        return {
            "action": "show_questions",
            "questions": questions,
            "message": get_consent_prompt_hebrew()["yes_response"]
        }
    
    elif response == "later":
        # User wants to skip for now
        consent_manager.mark_asked(user_id)
        
        return {
            "action": "continue",
            "message": get_consent_prompt_hebrew()["later_response"]
        }
    
    else:  # "no"
        # User declined
        from src.services.preference_consent import ConsentStatus
        consent = ConsentStatus(user_id=user_id)
        consent.preferences_collection_allowed = False
        consent_manager.save_consent(consent)
        
        return {
            "action": "continue",
            "message": get_consent_prompt_hebrew()["no_response"]
        }


# ============================================================================
# STEP 3: USER ANSWERS PREFERENCE QUESTIONS
# ============================================================================

def handle_preference_responses(user_id: str, responses: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process user's preference responses and save them.
    
    Args:
        user_id: User ID
        responses: Dict of question_id -> answer
        
    Example responses:
        {
            "study_level": "high_school",
            "proficiency_level": "intermediate",
            "explanation_style": "step_by_step",
            "learning_preferences": ["examples", "practice"],
            "learning_pace": "moderate"
        }
        
    Returns:
        Success status and message
    """
    # Process and save preferences
    result = process_preference_responses(responses, user_id)
    
    if result["success"]:
        # Mark that user gave consent
        from src.services.preference_consent import ConsentStatus
        consent = ConsentStatus(user_id=user_id)
        consent.preferences_collection_allowed = True
        consent_manager.save_consent(consent)
        
        # Clear preferences cache so new ones are loaded
        ai_middleware.prefs_service.clear_cache(user_id)
        
        return {
            "success": True,
            "message": """
🎉 מעולה! ההעדפות נשמרו בהצלחה!

מעכשיו כל התשובות יהיו מותאמות אישית בשבילך:
✨ ברמה המתאימה לך
✨ בסגנון שאת/ה אוהב/ת
✨ עם דוגמאות שיעזרו לך
✨ בקצב הנכון בשבילך

בואו נתחיל ללמוד! 📚
            """
        }
    else:
        return {
            "success": False,
            "message": "שגיאה בשמירת ההעדפות. אנא נסה/י שוב.",
            "error": result.get("error")
        }


# ============================================================================
# STEP 4: USE PREFERENCES IN AI CALLS
# ============================================================================

def make_personalized_ai_call(
    user_id: str,
    user_request: str,
    document_content: str,
    task_type: str
) -> str:
    """
    Make an AI call with full personalization based on user preferences.
    
    This is the COMPLETE FLOW showing how preferences are used:
    
    1. Load user preferences (from consent system)
    2. Prepare request with middleware (injects preferences into prompt)
    3. AI processes with personalized prompt
    4. Adapt response based on preferences
    5. Return personalized result
    
    Args:
        user_id: User ID
        user_request: What user wants
        document_content: User's document (for document-only constraint)
        task_type: Type of task
        
    Returns:
        Fully personalized AI response
    """
    from src.services.ai_client import ai_client
    
    # STEP 4A: Prepare request with middleware
    # This automatically loads user preferences and injects them
    request_data = ai_middleware.prepare_request(
        user_request=user_request,
        document_content=document_content,
        task_type=task_type,
        user_id=user_id
    )
    
    # At this point, request_data contains:
    # - Optimized prompt (personalized based on preferences)
    # - Constrained context (with document-only enforcement)
    # - User preferences (for response adaptation)
    
    # STEP 4B: Call main AI with personalized prompt
    ai_response = ai_client.generate_text(
        prompt=request_data['prompt'],  # Already personalized!
        context=request_data['context'],  # Already constrained!
        task_type=task_type
    )
    
    # STEP 4C: Adapt response for user
    final_response = ai_middleware.finalize_response(
        ai_response=ai_response,
        request_data=request_data
    )
    
    return final_response


# ============================================================================
# COMPLETE EXAMPLE FLOW
# ============================================================================

def complete_example_flow():
    """
    Example showing the COMPLETE flow from consent to personalized response.
    """
    user_id = "user_abc123"
    
    # ===== FIRST TIME USER =====
    print("📱 User opens app for first time")
    
    # Check if should ask for consent
    consent_check = check_user_consent_status(user_id)
    
    if consent_check["should_ask"]:
        print("\n💬 Showing consent prompt...")
        print(consent_check["consent_prompt"]["message"])
        
        # User clicks "Yes"
        response = handle_consent_response(user_id, "yes")
        
        print("\n📝 Showing preference questions...")
        for q in response["questions"]:
            print(f"  Q: {q['question']}")
        
        # User answers questions
        user_responses = {
            "study_level": "high_school",
            "proficiency_level": "intermediate",
            "explanation_style": "step_by_step",
            "learning_preferences": ["examples", "practice", "analogies"],
            "learning_pace": "moderate"
        }
        
        result = handle_preference_responses(user_id, user_responses)
        print(f"\n✅ {result['message']}")
    
    # ===== NOW USER USES THE APP =====
    print("\n\n📚 User uploads a document and asks a question...")
    
    document = """
    Photosynthesis is the process by which plants convert light energy into chemical energy.
    The process occurs in chloroplasts and requires carbon dioxide, water, and sunlight.
    The main product is glucose, which plants use for energy.
    """
    
    user_question = "Explain photosynthesis"
    
    # Make personalized AI call
    response = make_personalized_ai_call(
        user_id=user_id,
        user_request=user_question,
        document_content=document,
        task_type="summary"
    )
    
    print("\n🤖 AI Response (personalized):")
    print(response)
    
    print("\n✨ Response was personalized based on:")
    print("  - Study level: high_school")
    print("  - Knowledge: intermediate")
    print("  - Style: step_by_step")
    print("  - Includes: examples, practice, analogies")
    print("  - Pace: moderate")
    print("  - Language: Hebrew")
    print("  - Document-only constraint: ENFORCED")


# ============================================================================
# INTEGRATION CHECKLIST FOR UI DEVELOPERS
# ============================================================================

"""
UI INTEGRATION CHECKLIST:
========================

[ ] 1. On app first use / onboarding:
    - Call check_user_consent_status(user_id)
    - If should_ask=True, show consent_prompt
    
[ ] 2. When user responds to consent:
    - Call handle_consent_response(user_id, response)
    - If action="show_questions", display questions
    - If action="continue", proceed to app
    
[ ] 3. When user answers questions:
    - Collect all responses in a dict
    - Call handle_preference_responses(user_id, responses)
    - Show success message
    
[ ] 4. For every AI interaction:
    - Just call make_personalized_ai_call()
    - Preferences are automatically applied!
    
[ ] 5. Settings page:
    - Allow user to view/edit preferences
    - Load: ai_middleware.prefs_service.get(user_id)
    - Save: ai_middleware.prefs_service.save(preferences)
    - Clear cache after save
    
[ ] 6. Privacy page:
    - Show what data is stored
    - Allow export/delete
    - Update consent status

THAT'S IT! The middleware handles everything else automatically.
"""


# ============================================================================
# QUICK API REFERENCE
# ============================================================================

"""
QUICK API REFERENCE:
==================

# Check consent
check_user_consent_status(user_id) -> dict

# Handle responses
handle_consent_response(user_id, "yes|later|no") -> dict
handle_preference_responses(user_id, responses_dict) -> dict

# Make AI calls (automatic personalization)
make_personalized_ai_call(user_id, request, document, task_type) -> str

# Direct middleware access
ai_middleware.prepare_request(...)  # Prepares with preferences
ai_middleware.finalize_response(...)  # Adapts with preferences

# Preferences service
ai_middleware.prefs_service.get(user_id)  # Load
ai_middleware.prefs_service.save(prefs)   # Save
ai_middleware.prefs_service.clear_cache(user_id)  # Clear

# Consent service
consent_manager.should_ask_for_consent(user_id)
consent_manager.get_consent_status(user_id)
consent_manager.save_consent(consent)
"""


if __name__ == "__main__":
    # Run the complete example
    print("=" * 60)
    print("COMPLETE PREFERENCE FLOW DEMONSTRATION")
    print("=" * 60)
    complete_example_flow()
