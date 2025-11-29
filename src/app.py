"""
Study Buddy Application

This module contains the main application entrypoint and core functionality.
"""

from typing import Optional


def greet(name: str) -> str:
    """
    Generate a greeting message for the given name.

    Args:
        name: The name of the person to greet.

    Returns:
        A greeting string.
    """
    return f"Hi, {name}"


def main() -> None:
    """
    Main entrypoint for the Study Buddy application.
    """
    message = greet("Study Buddy User")
    print(message)


if __name__ == "__main__":
    main()
