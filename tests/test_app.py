"""
Unit tests for the app module.
"""

import unittest
from src.app import greet


class TestGreet(unittest.TestCase):
    """Test cases for the greet function."""

    def test_greet_returns_greeting(self) -> None:
        """Test that greet returns a proper greeting message."""
        result = greet("Alice")
        self.assertEqual(result, "Hi, Alice")

    def test_greet_with_empty_string(self) -> None:
        """Test that greet handles empty string."""
        result = greet("")
        self.assertEqual(result, "Hi, ")

    def test_greet_with_special_characters(self) -> None:
        """Test that greet handles special characters."""
        result = greet("User@123")
        self.assertEqual(result, "Hi, User@123")


if __name__ == "__main__":
    unittest.main()
