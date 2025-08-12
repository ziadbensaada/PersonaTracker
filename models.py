import os
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
import bcrypt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGODB_URI)
db = client['news_scraper_db']
users_collection = db['users']
search_history_collection = db['search_history']

# Create indexes
users_collection.create_index('username', unique=True)
users_collection.create_index('email', unique=True)

def get_user(username: str):
    """Retrieve a user by username."""
    return users_collection.find_one({"$or": [{"username": username}, {"email": username}]})

def verify_user(username: str, password: str):
    """Verify user credentials.
    
    Args:
        username: Username or email of the user
        password: Plain text password
        
    Returns:
        dict: User document if authentication succeeds, None otherwise
    """
    try:
        user = get_user(username)
        if not user:
            print(f"User not found: {username}")
            return None
            
        if not isinstance(user.get('password'), bytes):
            print("Invalid password format in database")
            return None
            
        if bcrypt.checkpw(password.encode('utf-8'), user['password']):
            print(f"User authenticated: {username}")
            # Remove password before returning
            user.pop('password', None)
            return user
        else:
            print(f"Invalid password for user: {username}")
            return None
            
    except Exception as e:
        print(f"Error in verify_user: {str(e)}")
        return None

def create_user(username: str, email: str, password: str, role: str = 'user'):
    """Create a new user with hashed password.
    
    Args:
        username: Unique username
        email: User's email
        password: Plain text password
        role: User role (default: 'user')
        
    Returns:
        tuple: (user_id, error_message) - user_id is None if creation failed
    """
    try:
        # Check if username or email already exists
        if users_collection.find_one({"$or": [{"username": username}, {"email": email}]}):
            return None, "Username or email already exists"
        
        # Hash the password
        password_bytes = password.encode('utf-8')
        hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        
        # Create user document
        user = {
            "username": username,
            "email": email,
            "password": hashed_password,
            "role": role,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "last_login": None
        }
        
        # Insert into database
        result = users_collection.insert_one(user)
        print(f"User created: {username}")
        return str(result.inserted_id), None
        
    except DuplicateKeyError:
        return None, "Username or email already exists"
    except Exception as e:
        print(f"Error creating user {username}: {str(e)}")
        return None, str(e)

def log_search(user_id: str, query: str, results_count: int):
    """Log a search query.
    
    Args:
        user_id: ID of the user who performed the search
        query: Search query
        results_count: Number of results returned
    """
    try:
        search_log = {
            "user_id": user_id,
            "query": query,
            "results_count": results_count,
            "timestamp": datetime.utcnow()
        }
        search_history_collection.insert_one(search_log)
    except Exception as e:
        print(f"Error logging search: {str(e)}")

def get_search_history(user_id: str, limit: int = 10):
    """Retrieve search history for a user.
    
    Args:
        user_id: ID of the user
        limit: Maximum number of history entries to return
        
    Returns:
        list: List of search history entries, most recent first
    """
    try:
        return list(search_history_collection
                  .find({"user_id": user_id})
                  .sort("timestamp", -1)
                  .limit(limit))
    except Exception as e:
        print(f"Error fetching search history: {str(e)}")
        return []

def create_admin_user():
    """Create an admin user if one doesn't exist."""
    try:
        admin_username = os.getenv('ADMIN_USERNAME', 'admin')
        admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        
        # Check if admin user already exists
        if not users_collection.find_one({"username": admin_username}):
            user_id, error = create_user(
                username=admin_username,
                email=admin_email,
                password=admin_password,
                role='admin'
            )
            if user_id:
                print(f"Admin user created with username: {admin_username}")
            else:
                print(f"Failed to create admin user: {error}")
        else:
            print("Admin user already exists")
    except Exception as e:
        print(f"Error creating admin user: {str(e)}")

# Create admin user on module import
create_admin_user()
