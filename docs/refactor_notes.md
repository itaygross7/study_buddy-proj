# StudyBuddyAI - Refactor Notes

## Overview

This document tracks technical debt, refactoring opportunities, and architectural improvements for StudyBuddyAI.

---

## 1. Completed Refactoring

### AI Client Modernization ✅
**Date**: Current PR

**Changes**:
- Updated OpenAI client from deprecated `Completion.create()` to new `chat.completions.create()`
- Added configurable model names via `SB_*` environment variables
- Centralized AI provider configuration in `config.py`

**Environment Variables Added**:
```python
SB_OPENAI_MODEL = "gpt-4o-mini"      # Configurable OpenAI model
SB_GEMINI_MODEL = "gemini-1.5-flash" # Configurable Gemini model
SB_DEFAULT_PROVIDER = "gemini"        # Default AI provider
SB_BASE_URL = ""                      # Custom API base URL
```

---

## 2. Technical Debt

### High Priority

#### TD-1: Celery vs RabbitMQ Direct
**Current**: Using RabbitMQ directly with pika
**Issue**: Celery is in requirements.txt but not used
**Options**:
1. Remove Celery from dependencies (current approach works)
2. Migrate to Celery for better task management, retries, monitoring

**Recommendation**: Keep current approach for simplicity; Celery adds complexity

#### TD-2: Database Connection Management
**Current**: Worker creates MongoDB connection at module level
**Issue**: Connection might stale on long-running worker
**Recommendation**: Add connection health check and reconnection logic

#### TD-3: Error Message Sanitization
**Current**: Manual sanitization in worker.py
**Recommendation**: Create utility function for consistent error handling

### Medium Priority

#### TD-4: Duplicate Repository Pattern
**Current**: `MongoTaskRepository` and `task_service.py` have overlapping code
**Recommendation**: Consolidate to use repository pattern consistently

#### TD-5: Template Duplication
**Current**: Tool templates share significant HTML structure
**Recommendation**: Extract common components (file picker, form, results pane)

#### TD-6: JavaScript Duplication
**Current**: Similar validation code in each tool page
**Recommendation**: Extract to shared module

### Low Priority

#### TD-7: Unused Legacy Files
**Files to Review**:
- `infra/mongo_client.py` - May be unused
- `templates/home.html` - Old template, check if needed
- `services/ai_service.py` - Check usage

#### TD-8: Test Coverage
**Current**: Basic unit tests exist
**Missing**: Integration tests, E2E tests
**Recommendation**: Add pytest-asyncio for async tests

---

## 3. Architecture Improvements

### Proposed: Service Layer Abstraction
```
Current:
  Routes → Services → AI Client → MongoDB

Proposed:
  Routes → Use Cases → Services → Repositories
                    ↓
                AI Gateway
```

### Proposed: Event-Driven Results
Instead of polling, consider:
- Server-Sent Events (SSE) for task status
- WebSocket for real-time updates
- Push notifications when complete

### Proposed: Caching Layer
- Redis for session data
- Cache AI responses for identical inputs
- Rate limiting with Redis

---

## 4. Code Quality Improvements

### Linting & Formatting
- [ ] Add `ruff` or `flake8` configuration
- [ ] Add `black` for code formatting
- [ ] Add `mypy` for type checking
- [ ] Pre-commit hooks configuration

### Testing Improvements
- [ ] Add `pytest-cov` for coverage reporting
- [ ] Add `pytest-asyncio` for async tests
- [ ] Add mock factories for common test data
- [ ] Add integration test fixtures

### Documentation
- [ ] Add docstrings to all public functions
- [ ] Add type hints throughout
- [ ] Generate API documentation (OpenAPI/Swagger)

---

## 5. Performance Optimizations

### Database
- [ ] Add indexes on frequently queried fields
- [ ] Consider TTL indexes for task expiration
- [ ] Connection pooling configuration

### API
- [ ] Add response compression
- [ ] Consider pagination for list endpoints
- [ ] Add ETag caching for static content

### Worker
- [ ] Tune prefetch count based on load
- [ ] Consider multiple worker instances
- [ ] Add dead letter queue for failed tasks

---

## 6. Security Improvements

### Authentication
- [ ] Add JWT or session-based auth
- [ ] Implement rate limiting
- [ ] Add CSRF protection for forms

### Input Validation
- [ ] Stricter content validation
- [ ] HTML sanitization for user content
- [ ] File content scanning

### Monitoring
- [ ] Add structured logging
- [ ] Error tracking (Sentry)
- [ ] Performance monitoring (APM)

---

## 7. UI/UX Improvements

### Avner Image Variety
**Current**: Limited set of Avner images in use
**Available**: 57 images in `ui/Avner/`
**Recommendation**: Map more images to UI states

**Proposed Image Mapping**:
| State | Current | Proposed Additional |
|-------|---------|---------------------|
| Home welcome | avner_wave | avner_waving |
| Processing | avner_thinking | avner_studing, avner_reading |
| Success | avner_celebrate | avner_celebrating, avner_horay |
| Error | avner_cry_laugh | avner_confused_reading, avner_dont_understand |
| Empty | avner_sleep | avner_yaning, avner_tierd |
| Loading | avner_thinking | avner_looking_at_page |

### Accessibility
- [ ] Add skip navigation link
- [ ] Improve color contrast ratios
- [ ] Add keyboard shortcuts
- [ ] Screen reader announcements for dynamic content

### Mobile Experience
- [ ] Test on various device sizes
- [ ] Add pull-to-refresh for results
- [ ] Optimize touch targets

---

## 8. Infrastructure Improvements

### Docker
- [ ] Multi-stage build for smaller image
- [ ] Health checks in compose file
- [ ] Resource limits for containers

### CI/CD
- [ ] Add GitHub Actions for testing
- [ ] Automated deployment pipeline
- [ ] Staging environment

### Monitoring
- [ ] Add Prometheus metrics
- [ ] Grafana dashboards
- [ ] Log aggregation (ELK stack or Loki)

---

## 9. Migration Notes

### OpenAI API Migration
The OpenAI library was updated from v0.x to v1.x pattern:

**Before**:
```python
openai.api_key = api_key
response = openai.Completion.create(
    engine="text-davinci-003",
    prompt=prompt,
    max_tokens=1500
)
text = response.choices[0].text
```

**After**:
```python
client = openai.OpenAI(api_key=api_key)
response = client.chat.completions.create(
    model="gpt-4o-mini",  # Configurable via SB_OPENAI_MODEL
    messages=[{"role": "user", "content": prompt}],
    max_tokens=1500
)
text = response.choices[0].message.content
```

---

## 10. Future Considerations

### Feature Requests
- Export to PDF functionality
- User accounts and history
- Collaboration features
- Offline mode (PWA)
- Multiple language support

### Technical Evolution
- Consider FastAPI for async performance
- GraphQL for flexible queries
- Vector database for semantic search
- ML model fine-tuning for Hebrew
