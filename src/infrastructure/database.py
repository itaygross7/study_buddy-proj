from flask import current_app, g
from pymongo import MongoClient
from werkzeug.local import LocalProxy

def get_db():
    """
    Returns a proxy to the MongoDB database.
    Uses Flask's application context to manage the connection.
    """
    if 'db' not in g:
        if 'mongo_client' not in current_app.extensions:
            current_app.extensions['mongo_client'] = MongoClient(current_app.config['MONGO_URI'])
        
        # The database name is expected to be part of the MONGO_URI
        # e.g., mongodb://host:port/dbname
        g.db = current_app.extensions['mongo_client'].get_database()
    
    return g.db

def init_app(app):
    """Initialize the database with the Flask app."""
    # Close the database connection when the app context tears down
    @app.teardown_appcontext
    def close_db(exception):
        db = g.pop('db', None)
        # Note: We don't close the client here as it's shared via extensions

# Use a LocalProxy to access the db connection within the application context
db = LocalProxy(get_db)
