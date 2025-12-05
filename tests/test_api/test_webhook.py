"""Tests for webhook endpoints."""
import json
import hmac
import hashlib
from unittest.mock import patch, MagicMock
from flask.testing import FlaskClient


def test_webhook_health(client: FlaskClient):
    """Test webhook health endpoint."""
    response = client.get('/webhook/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'


def test_webhook_update_wrong_branch(client: FlaskClient):
    """Test webhook update endpoint ignores non-master branches."""
    with patch('src.api.routes_webhook.WEBHOOK_SECRET', None):
        payload = {
            'ref': 'refs/heads/develop',
            'commits': [{'id': 'abc123'}]
        }
        response = client.post(
            '/webhook/update',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == 200
        assert response.json['status'] == 'ignored'
        assert 'Not a push to master branch' in response.json['message']


def test_webhook_update_master_branch(client: FlaskClient):
    """Test webhook update endpoint triggers update for master branch."""
    with patch('src.api.routes_webhook.WEBHOOK_SECRET', None), \
         patch('subprocess.Popen') as mock_popen:
        
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        payload = {
            'ref': 'refs/heads/master',
            'commits': [{'id': 'abc123'}],
            'forced': False
        }
        response = client.post(
            '/webhook/update',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == 200
        assert response.json['status'] == 'success'
        assert response.json['message'] == 'Update triggered'
        mock_popen.assert_called_once()


def test_webhook_update_force_push(client: FlaskClient):
    """Test webhook update endpoint handles force pushes."""
    with patch('src.api.routes_webhook.WEBHOOK_SECRET', None), \
         patch('subprocess.Popen') as mock_popen:
        
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        payload = {
            'ref': 'refs/heads/master',
            'commits': [{'id': 'abc123'}],
            'forced': True
        }
        response = client.post(
            '/webhook/update',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == 200
        assert response.json['status'] == 'success'
        mock_popen.assert_called_once()


def test_webhook_signature_verification(client: FlaskClient):
    """Test webhook signature verification."""
    secret = 'test-secret-key'
    payload = {
        'ref': 'refs/heads/master',
        'commits': [{'id': 'abc123'}]
    }
    payload_bytes = json.dumps(payload).encode()
    
    # Generate valid signature
    mac = hmac.new(secret.encode(), msg=payload_bytes, digestmod=hashlib.sha256)
    signature = 'sha256=' + mac.hexdigest()
    
    with patch('src.api.routes_webhook.WEBHOOK_SECRET', secret), \
         patch('subprocess.Popen') as mock_popen:
        
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_popen.return_value = mock_process
        
        response = client.post(
            '/webhook/update',
            data=payload_bytes,
            content_type='application/json',
            headers={'X-Hub-Signature-256': signature}
        )
        assert response.status_code == 200
        assert response.json['status'] == 'success'


def test_webhook_invalid_signature(client: FlaskClient):
    """Test webhook rejects invalid signature."""
    secret = 'test-secret-key'
    payload = {
        'ref': 'refs/heads/master',
        'commits': [{'id': 'abc123'}]
    }
    payload_bytes = json.dumps(payload).encode()
    
    with patch('src.api.routes_webhook.WEBHOOK_SECRET', secret):
        response = client.post(
            '/webhook/update',
            data=payload_bytes,
            content_type='application/json',
            headers={'X-Hub-Signature-256': 'sha256=invalid'}
        )
        assert response.status_code == 403
        assert 'error' in response.json
