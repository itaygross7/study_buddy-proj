# Test cases for app module

def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'


def test_index_page(client):
    """Test the index page loads."""
    response = client.get('/')
    assert response.status_code == 200
