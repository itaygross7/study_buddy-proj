# User Preference Flow

How StudyBuddy collects consent, stores preferences, and personalizes AI responses.

## Overview

1. User is asked for consent (optional, Hebrew prompts).
2. Quick preference questions (study level, style, pace).
3. Preferences are stored per user.
4. `ai_middleware` injects preferences into prompts.
5. Responses are adapted to the user's profile.

## Key modules

| Module | Role |
|--------|------|
| `src/services/preference_consent.py` | Consent prompts, `consent_manager`, question flow |
| `src/services/ai_middleware.py` | `prepare_request`, `finalize_response`, `UserPreferences` |
| `src/services/ai_client.py` | LLM calls after middleware prepares the prompt |

## Flow (high level)

### 1. Check consent

Call `consent_manager.should_ask_for_consent(user_id)`. If true, show `get_consent_prompt_hebrew()`.

### 2. Handle consent response

- **yes** → show `get_quick_questions_hebrew()`
- **later** → `consent_manager.mark_asked(user_id)`, continue without preferences
- **no** → save declined consent, continue without collection

### 3. Save preferences

Pass answers to `process_preference_responses(responses, user_id)`, then mark consent allowed and clear the middleware preference cache for that user.

### 4. AI calls

For each interaction:

```python
request_data = ai_middleware.prepare_request(
    user_request=...,
    document_content=...,
    task_type=...,
    user_id=...,
)
ai_response = ai_client.generate_text(
    prompt=request_data["prompt"],
    context=request_data["context"],
    task_type=...,
)
final = ai_middleware.finalize_response(ai_response=ai_response, request_data=request_data)
```

Document-only constraints still apply via the middleware and `src/utils/ai_constraints.py`.

## UI integration checklist

- [ ] Onboarding: check consent status before first AI use
- [ ] Consent UI: yes / later / no
- [ ] Preference form: collect and POST to your preference endpoint
- [ ] Settings: load/save via `ai_middleware.prefs_service`
- [ ] Privacy page: explain stored data; allow export/delete

## Privacy

Preferences stay per user. They are not used to train shared models. See [SECURITY_SUMMARY.md](../SECURITY_SUMMARY.md).
