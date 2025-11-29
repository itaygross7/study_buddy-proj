# StudyBuddyAI 🦉

**Your local-first, AI-powered learning assistant.**

StudyBuddyAI is a web application designed to help students and learners with a variety of tasks using generative AI. It runs entirely on your local machine via Docker, ensuring your data stays private.

## ✨ Features

-   **Interactive Summarizer**: Condense long texts or documents into key points and ask follow-up questions.
-   **Flashcards Generator**: Automatically create Q&A flashcards from your study materials.
-   **Assess-Me Quiz Builder**: Generate quizzes from content to test your knowledge.
-   **Homework Helper**: Get step-by-step explanations for difficult problems.
-   **Local-First**: All services (backend, database, queue) run locally in Docker containers.
-   **PDF Export**: Save your generated flashcards and summaries as PDFs for offline use.

## 🛠️ Tech Stack

-   **Backend**: Python, Flask
-   **Frontend**: HTMX, TailwindCSS
-   **AI Integration**: OpenAI (GPT series), Google (Gemini Pro)
-   **Database**: MongoDB
-   **Task Queue**: RabbitMQ with Celery
-   **Containerization**: Docker & Docker Compose
-   **Dependency Management**: Pipenv

## 🚀 Getting Started

### Prerequisites

-   [Docker](https://www.docker.com/get-started) and [Docker Compose](https://docs.docker.com/compose/install/)
-   [Node.js](https://nodejs.org/en/download/) and npm (for TailwindCSS)
-   [Pipenv](https://pipenv.pypa.io/en/latest/installation/)

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/studybuddyai.git
    cd studybuddyai
    ```

2.  **Set up environment variables:**
    Copy the example environment file and fill in your API keys.
    ```bash
    cp .env.example .env
    ```
    Edit `.env` and add your `OPENAI_API_KEY` and `GEMINI_API_KEY`.

3.  **Install Python dependencies:**
    ```bash
    pipenv install --dev
    ```

4.  **Install frontend dependencies:**
    ```bash
    npm install
    ```

5.  **Build and run the application:**
    This command will build the Docker images, start all services, and build the TailwindCSS assets.
    ```bash
    docker-compose up --build
    ```

6.  **Access the application:**
    Open your web browser and navigate to `http://localhost:5000`.

    You can also access the RabbitMQ Management UI at `http://localhost:15672` (user: `user`, pass: `password`).

### Development Workflow

-   **Activate Virtual Environment**: `pipenv shell`
-   **Run Tests**: `pytest`
-   **Check Test Coverage**: `pytest --cov=src`
-   **Build TailwindCSS Manually**: `npm run tailwind:build`

## 📂 Project Structure

The project follows a clean, modular architecture:

```
/src            # Core application source code
  /api          # Flask API endpoints
  /domain       # Business models, entities, and logic
  /services     # Business logic and AI clients
  /infrastructure # Database, queue, and config
  /workers      # Celery background workers
/ui             # Frontend templates and static assets
/sb_utils       # Shared project-wide utilities
/tests          # Unit and integration tests
/docker         # Docker-related scripts
```

## 🔐 AI Safety

The AI client includes several safety mechanisms:
-   **System Prompts**: Instructions to prevent harmful or off-topic responses.
-   **Retry Logic**: Uses `tenacity` to handle transient API errors.
-   **Fallbacks**: Provides a graceful failure message if the AI service is unavailable.

---

Happy Studying!
