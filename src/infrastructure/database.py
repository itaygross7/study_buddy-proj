from flask import current_app
from pymongo import MongoClient
from werkzeug.local import LocalProxy

def get_db():
    """
    Returns a proxy to the MongoDB client.
    """
    if 'mongo_client' not in current_app.extensions:
        current_app.extensions['mongo_client'] = MongoClient(current_app.config['MONGO_URI'])
    
    # The database name is expected to be part of the MONGO_URI
    # e.g., mongodb://host:port/dbname
    return current_app.extensions['mongo_client'].get_database()

# Use a LocalProxy to access the db connection within the application context
db = LocalProxy(get_db)
