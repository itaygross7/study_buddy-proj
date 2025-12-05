# StudyBuddyAI 🦉

**StudyBuddyAI is a local-first, AI-powered learning assistant designed for Hebrew-speaking students.**

This application provides a suite of tools to help students learn more effectively, including an interactive summarizer, a flashcard generator, a quiz builder, and a homework helper. The entire backend runs in Docker, ensuring data privacy and easy setup.

## ✨ Core Features

-   **Hebrew-First Interface**: The entire UI is in Hebrew and designed for RTL.
-   **Multi-Format File Uploads**: Supports `.pdf`, `.docx`, `.pptx`, `.txt`, and images (`.png`, `.jpg`).
-   **Async Processing**: "Lightning Fast" uploads stream directly to the database (GridFS), with AI processing handled in the background by RabbitMQ workers.
-   **AI-Powered Tools**:
    -   **סיכום חכם**: Condense long texts into key points.
    -   **כרטיסיות לימוד**: Automatically create Q&A flashcards.
    -   **בחן אותי**: Generate quizzes to test your knowledge.
    -   **עזרה בשיעורי בית**: Get step-by-step explanations.
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
This project is built with a focus on clean architecture, robustness, and a great user experience. Happy studying!
