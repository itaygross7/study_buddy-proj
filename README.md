# Study Buddy Project

A Python project for study assistance and learning tools.

## Project Structure

```
study_buddy-proj/
├── src/
│   ├── __init__.py     # Source package initialization
│   └── app.py          # Main application module
├── tests/
│   ├── __init__.py     # Tests package initialization
│   └── test_app.py     # Unit tests for app module
├── main.py             # Legacy entrypoint (PyCharm generated)
├── Pipfile             # Pipenv dependency management
├── requirements.txt    # Pip dependency management
├── .gitignore          # Git ignore patterns
└── README.md           # This file
```

## Setup

### Using pip

```bash
pip install -r requirements.txt
```

### Using pipenv

```bash
pipenv install
pipenv shell
```

## Usage

Run the main application:

```bash
python -m src.app
```

## Testing

Run the test suite:

```bash
python -m pytest tests/
# or
python -m unittest discover tests/
```

## Development

### Code Style

- Follow PEP 8 style guidelines
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes

### Workflow

1. Create a feature branch
2. Make changes following SOLID principles
3. Write/update tests
4. Submit a pull request for review

## License

MIT License
