# StudyBuddyAI - Application Map

## Overview

StudyBuddyAI is a Hebrew-focused educational web application that helps students learn more effectively using AI-powered tools. The application features "Avner" - a friendly capybara mascot that guides students through their learning journey.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Flask/Jinja2)                  │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│  │  Home   │ │ Summary  │ │Flashcards│ │ Assess   │ │Homework │ │
│  └────┬────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬────┘ │
│       └───────────┴────────────┴────────────┴────────────┘      │
│                               │ HTMX                             │
└───────────────────────────────┼──────────────────────────────────┘
                                │
┌───────────────────────────────┼──────────────────────────────────┐
│                         Flask API Layer                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ /summary │ │/flashcards│ │ /assess  │ │/homework │ │ /tasks │ │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └───┬────┘ │
│       └───────────┴────────────┴────────────┴────────────┘      │
│                               │                                  │
└───────────────────────────────┼──────────────────────────────────┘
                                │
┌───────────────────────────────┼──────────────────────────────────┐
│                         RabbitMQ Queue                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │summarize │ │flashcards│ │  assess  │ │ homework │            │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘            │
└───────┼────────────┼────────────┼────────────┼───────────────────┘
        └────────────┴────────────┴────────────┘
                                │
┌───────────────────────────────┼──────────────────────────────────┐
│                         Worker Process (worker.py)                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              src/workers/task_handlers.py                    │ │
│  │  ┌───────────────────────────────────────────────────────┐  │ │
│  │  │              Service Layer (src/services/)             │  │ │
│  │  │  ┌──────────────┐  ┌──────────────┐                   │  │ │
│  │  │  │   OpenAI     │  │    Gemini    │                   │  │ │
│  │  │  │ (SB_OPENAI_  │  │ (SB_GEMINI_  │                   │  │ │
│  │  │  │    MODEL)    │  │    MODEL)    │                   │  │ │
│  │  │  └──────────────┘  └──────────────┘                   │  │ │
│  │  └───────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└───────────────────────────────┼──────────────────────────────────┘
                                │
┌───────────────────────────────┼──────────────────────────────────┐
│                          MongoDB                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │documents │ │ tasks    │ │summaries │ │flashcards│ │assess  │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
study_buddy-proj/
├── app.py                    # Main Flask application entry point
├── worker.py                 # Background task worker (RabbitMQ consumer)
├── docker-compose.yml        # Docker services configuration
├── Dockerfile                # Application container image
├── requirements.txt          # Python dependencies
├── Pipfile                   # Pipenv dependencies
│
├── src/                      # Source code
│   ├── api/                  # API routes (Blueprints)
│   │   ├── routes_summary.py
│   │   ├── routes_flashcards.py
│   │   ├── routes_assess.py
│   │   ├── routes_homework.py
│   │   ├── routes_task.py    # Task polling endpoint
│   │   ├── routes_upload.py
│   │   ├── routes_auth.py
│   │   ├── routes_library.py
│   │   └── ...
│   │
│   ├── services/             # Business logic
│   │   ├── ai_client.py      # Unified AI client (OpenAI/Gemini)
│   │   ├── summary_service.py
│   │   ├── flashcards_service.py
│   │   ├── assess_service.py
│   │   ├── homework_service.py
│   │   ├── file_service.py
│   │   └── ...
│   │
│   ├── domain/               # Domain models
│   │   ├── models/           # Pydantic models (db_models.py, api_models.py)
│   │   ├── errors.py         # Custom exceptions
│   │   └── repositories/     # Repository interfaces
│   │
│   ├── infrastructure/       # Infrastructure layer
│   │   ├── config.py         # Settings (includes SB_* env vars)
│   │   ├── database.py       # MongoDB connection
│   │   ├── rabbitmq.py       # RabbitMQ publisher
│   │   └── repositories/     # Data access layer implementations
│   │
│   ├── utils/                # Utility functions
│   │   ├── file_processing.py
│   │   ├── smart_parser.py
│   │   └── ...
│   │
│   └── workers/              # Worker task handlers
│       └── task_handlers.py  # Task processing logic
│
├── ui/                       # Frontend assets
│   ├── Avner/               # Avner mascot images (57 images)
│   ├── templates/           # Jinja2 templates
│   │   ├── base.html        # Base layout (RTL, Hebrew)
│   │   ├── index.html       # Home page
│   │   ├── tool_*.html      # Tool pages
│   │   └── task_status.html # Task polling partial
│   │
│   └── static/              # Static assets
│       ├── css/styles.css   # Tailwind CSS (compiled)
│       └── img/             # UI images
│
├── sb_utils/                 # Shared utilities
│   ├── ai_safety.py         # AI safety guards
│   ├── logger_utils.py      # Logging configuration
│   └── validation.py        # Input validation
│
├── tests/                    # Test suite
│   ├── conftest.py          # Pytest fixtures
│   └── test_*.py            # Test files
│
└── docs/                     # Documentation
    ├── app_map.md           # This file
    ├── DEPLOYMENT.md        # Deployment guide
    ├── HEALTH_AND_MONITORING.md  # Health checks
    ├── ARCHIVE/             # Archived/outdated docs
    └── ...
```

## Key Features

### 1. Summarizer (מסכם)
- Upload text or documents (PDF, Word, TXT)
- AI generates concise bullet-point summaries
- Follow-up questions for understanding

### 2. Flashcards (כרטיסיות)
- Generate Q&A flashcards from content
- Interactive flip cards
- Shuffle mode for practice

### 3. Assess Me (בחן אותי)
- Generate multiple-choice quizzes
- Automatic grading with score
- Visual feedback with Avner reactions

### 4. Homework Helper (עוזר שיעורים)
- Describe a problem in text
- Step-by-step solution breakdown
- Tips and guidance

## Background Task Flow

1. User submits content via API
2. Task created in MongoDB with PENDING status
3. Message published to RabbitMQ queue
4. Worker picks up message and processes with AI
5. Result saved to MongoDB
6. Task status updated to COMPLETED
7. Frontend polls `/api/tasks/<id>` for status

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| SB_OPENAI_MODEL | OpenAI model name | gpt-4o-mini |
| SB_GEMINI_MODEL | Gemini model name | gemini-1.5-flash-latest |
| SB_DEFAULT_PROVIDER | Default AI provider | gemini |
| SB_BASE_URL | Custom API base URL | (empty) |
| OPENAI_API_KEY | OpenAI API key | - |
| GEMINI_API_KEY | Gemini API key | - |
| MONGO_URI | MongoDB connection string | mongodb://localhost:27017/studybuddy |
| RABBITMQ_URI | RabbitMQ connection string | amqp://guest:guest@localhost:5672/ |

## UI Design

- **Theme**: Cozy study room aesthetic (warm yellows, browns, cream)
- **Language**: Hebrew RTL with English brand name "StudyBuddyAI"
- **Layout**: Responsive (desktop top nav + grid, mobile hamburger + stacked)
- **Mascot**: Avner the capybara (57 images for various states)
