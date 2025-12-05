"""Tests for context processor functionality in app.py"""
import pytest
from unittest.mock import patch, MagicMock


class TestContextProcessor:
    """Test the context processor that injects OAuth configuration."""

    @patch('app.settings')
    def test_google_oauth_enabled_when_both_credentials_present(self, mock_settings):
        """Test google_oauth_enabled is True when both GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are set."""
        mock_settings.GOOGLE_CLIENT_ID = "test_client_id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test_client_secret"
        mock_settings.APPLE_CLIENT_ID = ""
        mock_settings.APPLE_TEAM_ID = ""
        
        from app import create_app
        app = create_app()
        
        with app.test_request_context('/'):
            # Get the context processor result
            context = {}
            for func in app.template_context_processors[None]:
                context.update(func())
            
            assert context['google_oauth_enabled'] is True
            assert context['apple_oauth_enabled'] is False

    @patch('app.settings')
    def test_google_oauth_disabled_when_client_id_missing(self, mock_settings):
        """Test google_oauth_enabled is False when GOOGLE_CLIENT_ID is missing."""
        mock_settings.GOOGLE_CLIENT_ID = ""
        mock_settings.GOOGLE_CLIENT_SECRET = "test_client_secret"
        mock_settings.APPLE_CLIENT_ID = ""
        mock_settings.APPLE_TEAM_ID = ""
        
        from app import create_app
        app = create_app()
        
        with app.test_request_context('/'):
            context = {}
            for func in app.template_context_processors[None]:
                context.update(func())
            
            assert context['google_oauth_enabled'] is False

    @patch('app.settings')
    def test_google_oauth_disabled_when_client_secret_missing(self, mock_settings):
        """Test google_oauth_enabled is False when GOOGLE_CLIENT_SECRET is missing."""
        mock_settings.GOOGLE_CLIENT_ID = "test_client_id"
        mock_settings.GOOGLE_CLIENT_SECRET = ""
        mock_settings.APPLE_CLIENT_ID = ""
        mock_settings.APPLE_TEAM_ID = ""
        
        from app import create_app
        app = create_app()
        
        with app.test_request_context('/'):
            context = {}
            for func in app.template_context_processors[None]:
                context.update(func())
            
            assert context['google_oauth_enabled'] is False

    @patch('app.settings')
    def test_google_oauth_disabled_when_credentials_are_none(self, mock_settings):
        """Test google_oauth_enabled is False when credentials are None."""
        mock_settings.GOOGLE_CLIENT_ID = None
        mock_settings.GOOGLE_CLIENT_SECRET = None
        mock_settings.APPLE_CLIENT_ID = None
        mock_settings.APPLE_TEAM_ID = None
        
        from app import create_app
        app = create_app()
        
        with app.test_request_context('/'):
            context = {}
            for func in app.template_context_processors[None]:
                context.update(func())
            
            assert context['google_oauth_enabled'] is False
            assert context['apple_oauth_enabled'] is False

    @patch('app.settings')
    def test_apple_oauth_enabled_when_both_credentials_present(self, mock_settings):
        """Test apple_oauth_enabled is True when both APPLE_CLIENT_ID and APPLE_TEAM_ID are set."""
        mock_settings.GOOGLE_CLIENT_ID = ""
        mock_settings.GOOGLE_CLIENT_SECRET = ""
        mock_settings.APPLE_CLIENT_ID = "test_apple_client_id"
        mock_settings.APPLE_TEAM_ID = "test_team_id"
        
        from app import create_app
        app = create_app()
        
        with app.test_request_context('/'):
            context = {}
            for func in app.template_context_processors[None]:
                context.update(func())
            
            assert context['google_oauth_enabled'] is False
            assert context['apple_oauth_enabled'] is True

    @patch('app.settings')
    def test_apple_oauth_disabled_when_client_id_missing(self, mock_settings):
        """Test apple_oauth_enabled is False when APPLE_CLIENT_ID is missing."""
        mock_settings.GOOGLE_CLIENT_ID = ""
        mock_settings.GOOGLE_CLIENT_SECRET = ""
        mock_settings.APPLE_CLIENT_ID = ""
        mock_settings.APPLE_TEAM_ID = "test_team_id"
        
        from app import create_app
        app = create_app()
        
        with app.test_request_context('/'):
            context = {}
            for func in app.template_context_processors[None]:
                context.update(func())
            
            assert context['apple_oauth_enabled'] is False

    @patch('app.settings')
    def test_apple_oauth_disabled_when_team_id_missing(self, mock_settings):
        """Test apple_oauth_enabled is False when APPLE_TEAM_ID is missing."""
        mock_settings.GOOGLE_CLIENT_ID = ""
        mock_settings.GOOGLE_CLIENT_SECRET = ""
        mock_settings.APPLE_CLIENT_ID = "test_apple_client_id"
        mock_settings.APPLE_TEAM_ID = ""
        
        from app import create_app
        app = create_app()
        
        with app.test_request_context('/'):
            context = {}
            for func in app.template_context_processors[None]:
                context.update(func())
            
            assert context['apple_oauth_enabled'] is False

    @patch('app.settings')
    def test_both_oauth_providers_enabled_independently(self, mock_settings):
        """Test that both Google and Apple OAuth can be enabled at the same time."""
        mock_settings.GOOGLE_CLIENT_ID = "test_google_client_id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test_google_secret"
        mock_settings.APPLE_CLIENT_ID = "test_apple_client_id"
        mock_settings.APPLE_TEAM_ID = "test_team_id"
        
        from app import create_app
        app = create_app()
        
        with app.test_request_context('/'):
            context = {}
            for func in app.template_context_processors[None]:
                context.update(func())
            
            assert context['google_oauth_enabled'] is True
            assert context['apple_oauth_enabled'] is True

    @patch('app.settings')
    def test_both_oauth_providers_disabled(self, mock_settings):
        """Test that both providers can be disabled at the same time."""
        mock_settings.GOOGLE_CLIENT_ID = ""
        mock_settings.GOOGLE_CLIENT_SECRET = ""
        mock_settings.APPLE_CLIENT_ID = ""
        mock_settings.APPLE_TEAM_ID = ""
        
        from app import create_app
        app = create_app()
        
        with app.test_request_context('/'):
            context = {}
            for func in app.template_context_processors[None]:
                context.update(func())
            
            assert context['google_oauth_enabled'] is False
            assert context['apple_oauth_enabled'] is False

    @patch('app.settings')
    def test_context_processor_includes_current_user(self, mock_settings):
        """Test that context processor still includes current_user."""
        mock_settings.GOOGLE_CLIENT_ID = ""
        mock_settings.GOOGLE_CLIENT_SECRET = ""
        mock_settings.APPLE_CLIENT_ID = ""
        mock_settings.APPLE_TEAM_ID = ""
        
        from app import create_app
        app = create_app()
        
        with app.test_request_context('/'):
            context = {}
            for func in app.template_context_processors[None]:
                context.update(func())
            
            # current_user should be in context
            assert 'current_user' in context
