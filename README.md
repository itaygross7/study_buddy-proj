# StudyBuddyAI 🦉

**StudyBuddyAI is a local-first, AI-powered learning assistant designed for Hebrew-speaking students.**

This application provides a suite of tools to help students learn more effectively, including an interactive summarizer, a flashcard generator, a quiz builder, and a homework helper. The entire backend runs in Docker, ensuring data privacy and easy setup.

---

## 🔒 Transparency & Trust

**Open Source & Transparent:**
- 📖 **Full source code available**: [View on GitHub](https://github.com/itaygross7/study_buddy-proj)
- 🔍 **See exactly how your data is processed**
- 🔒 **Verify our privacy and security claims**
- 💬 **Contribute or report issues**

**Quality & Accuracy Guarantee:**
> 🎯 **Avner only uses YOUR documents for answers**
> 
> Unlike general AI that might "hallucinate" or make up information, StudyBuddy's Avner ensures:
> - ✅ **100% accurate to your documents** - All summaries, flashcards, and assessments are based solely on your uploaded materials
> - ✅ **No external information mixed in** - Avner won't add facts from the internet or other sources
> - ✅ **Transparent sources** - Every answer references your specific documents
> - ✅ **No hallucinations** - If information isn't in your document, Avner will say so
> 
> **Teaching Mode Exception:** Only the homework helper and tutor features may use general educational knowledge to teach concepts (clearly labeled when active).

**Privacy First:**
- 🔒 Your documents stay private
- 🔒 No data mixing between users
- 🔒 Local-first architecture
- 🔒 Complete user isolation

---

## ✨ Core Features

-   **Hebrew-First Interface**: The entire UI is in Hebrew and designed for RTL.
-   **Multi-Format File Uploads**: Supports `.pdf`, `.docx`, `.pptx`, `.txt`, and images (`.png`, `.jpg`).
-   **Async Processing**: "Lightning Fast" uploads stream directly to the database (GridFS), with AI processing handled in the background by RabbitMQ workers.
-   **AI-Powered Tools**:
    -   **סיכום חכם**: Condense long texts into key points (document-only)
    -   **כרטיסיות לימוד**: Automatically create Q&A flashcards (document-only)
    -   **בחן אותי**: Generate quizzes to test your knowledge (document-only)
    -   **עזרה בשיעורי בית**: Get step-by-step explanations (teaching mode)
-   **🎯 Smart Personalization**: Avner adapts to your learning level, style, and pace
-   **🧠 Continuous Learning**: Admin-guided improvements make Avner smarter over time
-   **PDF Export**: Save your generated flashcards for offline use.
-   **Bilingual Support**: Switch between Hebrew (default) and English.

## 🛠️ Tech Stack

-   **Backend**: Python, Flask, PyMongo (with GridFS)
-   **Frontend**: Jinja2, HTMX, Tailwind CSS
--   **Task Queue**: RabbitMQ with a custom `pika` worker.
-   **AI Integration**: OpenAI (GPT series), Google (Gemini Pro) with `tenacity` for retries.
-   **Containerization**: Docker & Docker Compose
-   **Dependency Management**: Pipenv

## 🚀 Production Setup & Deployment

### Prerequisites

-   [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/)
-   [Pipenv](https://pipenv.pypa.io/en/latest/installation/)
-   An `.env` file (see below)

### Configuration

1.  **Create an Environment File**: Copy the example file to create your local configuration.
    ```bash
    cp .env.example .env
    ```

2.  **Edit `.env`**: Open the `.env` file and fill in your secret keys and API credentials:
    -   `SECRET_KEY`: A long, random string for session security.
    -   `OPENAI_API_KEY`: Your key from OpenAI.
    -   `GEMINI_API_KEY`: Your key from Google AI Studio.
    -   Set `FLASK_ENV` to `production`.

### Running the Application

1.  **Build and Run with Docker Compose**: This single command builds the images, starts all services (web, worker, database, queue), and runs the application.
    ```bash
    docker-compose up --build -d
    ```
    The `-d` flag runs the containers in detached mode.

2.  **Access the Application**:
    -   **Web App**: `http://localhost:5000`
    -   **RabbitMQ Management UI**: `http://localhost:15672` (user: `user`, pass: `password`)

3.  **Viewing Logs**:
    ```bash
    docker-compose logs -f web
    docker-compose logs -f worker
    ```

4.  **Stopping the Application**:
    ```bash
    docker-compose down
    ```

### Troubleshooting Deployment Issues

If you encounter permission issues, auto-update failures, or Docker problems, use the hard restart script:

```bash
./deploy-hard-restart.sh
```

This comprehensive script will:
- Fix all permissions (Git, Docker, files)
- Clean and rebuild Docker state
- Verify deployment health
- Configure auto-update flow

For other issues, see the [Troubleshooting Guide](TROUBLESHOOTING.md).

## 🧪 Local Development & Testing

1.  **Install Dependencies**:
    ```bash
    pipenv install --dev
    ```

2.  **Activate Virtual Environment**:
    ```bash
    pipenv shell
    ```

3.  **Run Tests**:
    ```bash
    pytest
    ```

---

## 🔍 How It Works - Technical Deep Dive

### Document-Only AI Processing

StudyBuddy uses a **4-layer security system** to ensure AI responses come only from your documents:

1. **Layer 1: Prompt Optimizer** - Injects document-only constraints into every request
2. **Layer 2: Context Builder** - Wraps your document with strict boundaries
3. **Layer 3: AI Processing** - AI sees only your document content
4. **Layer 4: Response Validator** - Verifies no external information was added

**See the code yourself:**
- [AI Constraints System](src/utils/ai_constraints.py) - How we enforce document-only
- [AI Middleware](src/services/ai_middleware.py) - Smart personalization layer
- [Service Classification](src/services/) - See which services use which constraints

### Personalization System

Avner learns your preferences with consent:
1. **Polite consent request** - Explains benefits, completely optional
2. **Quick questions** (2-3 min) - Learn your study level, style, pace
3. **Continuous adaptation** - Every response tailored to you
4. **Privacy preserved** - Your preferences stay with you only

**Code transparency:**
- [Preference Consent](src/services/preference_consent.py) - How we ask permission
- [Preference Flow Guide](PREFERENCE_FLOW_GUIDE.py) - Complete integration guide

### Continuous Learning (Admin-Guided)

Admins can teach Avner to improve:
- **Teaching examples** - Show Avner better responses
- **Improvement rules** - Define when to enhance explanations
- **Usage analytics** - Learn from patterns (anonymized)
- **No user data training** - Only admin guidance

**Transparency:**
- [Avner Learning System](src/services/avner_learning.py) - How the learning works
- [Admin API](src/api/routes_admin_learning.py) - Admin teaching interface

### Open Source Benefits

✅ **Verify our claims** - Read the actual code
✅ **Audit security** - Check our constraints
✅ **Understand privacy** - See how data flows
✅ **Contribute** - Help improve StudyBuddy
✅ **Trust through transparency** - No hidden behavior

---

## 📄 License & Credits

This project is open source and built with a focus on:
- 🎓 **Quality education** through accurate AI
- 🔒 **Privacy** through local-first design
- 🌍 **Accessibility** through Hebrew-first UX
- 💡 **Transparency** through open source

---

This project is built with a focus on clean architecture, robustness, and a great user experience. Happy studying!
