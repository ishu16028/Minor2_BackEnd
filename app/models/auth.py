from flask import Blueprint, request, jsonify, session, current_app, url_for, redirect
from flask_login import login_user, logout_user, login_required, current_user
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import os
import json
import requests
from oauthlib.oauth2 import WebApplicationClient
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app import db, bcrypt
from app.models.user import User, UserRole

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GOOGLE_DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

# Initialize OAuth client
google_client = WebApplicationClient(GOOGLE_CLIENT_ID) if GOOGLE_CLIENT_ID else None

def get_google_provider_cfg():
    """Get Google's OAuth 2.0 endpoints."""
    return requests.get(GOOGLE_DISCOVERY_URL).json()

@auth_bp.route('/admin/check', methods=['GET'])
@jwt_required()
def check_admin():
    """Check if current user is admin."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'is_admin': user.is_admin()
    }), 200

# Admin role required decorator
def admin_required(f):
    """Decorator to require admin role for a route."""
    @jwt_required()
    def decorated_function(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or not user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(*args, **kwargs)
    
    # Preserve the original function name and docstring
    decorated_function.__name__ = f.__name__
    decorated_function.__doc__ = f.__doc__
    
    return decorated_functionbp.route('/login', methods=['POST'])
def login():
    """Login a user."""
    data = request.get_json()
    
    # Find user by email
    user = User.query.filter_by(email=data['email']).first()
    
    # Check if user exists and password is correct
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401
    
    # Login user with Flask-Login
    login_user(user)
    
    # Create access token
    access_token = create_access_token(identity=user.id)
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role
        },
        'access_token': access_token
    }), 200

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Logout a user."""
    logout_user()
    return jsonify({'message': 'Logout successful'}), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get current user info."""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role
        }
    }), 200

@auth_bp.route('/google/login')
def google_login():
    """Initiate Google OAuth login flow."""
    if not google_client:
        return jsonify({'error': 'Google OAuth not configured'}), 500
    
    # Find out what URL to hit for Google login
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for login and provide
    # scopes that let you retrieve user's profile from Google
    request_uri = google_client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile", "https://www.googleapis.com/auth/gmail.compose"],
    )
    return redirect(request_uri)

@auth_bp.route('/google/login/callback')
def google_callback():
    """Handle Google OAuth callback."""
    if not google_client:
        return jsonify({'error': 'Google OAuth not configured'}), 500
    
    # Get authorization code Google sent back
    code = request.args.get("code")
    
    # Find out what URL to hit to get tokens that allow you to ask for
    # things on behalf of a user
    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]
    
    # Prepare and send request to get tokens
    token_url, headers, body = google_client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code,
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
    )
    
    # Parse the tokens
    google_client.parse_request_body_response(json.dumps(token_response.json()))
    
    # Get user info from Google
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = google_client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    
    # Verify the user
    if userinfo_response.json().get("email_verified"):
        google_id = userinfo_response.json()["sub"]
        email = userinfo_response.json()["email"]
        first_name = userinfo_response.json().get("given_name", "")
        last_name = userinfo_response.json().get("family_name", "")
    else:
        return jsonify({'error': 'User email not verified by Google'}), 400
    
    # Create or update user
    user = User.query.filter_by(email=email).first()
    if not user:
        # Create new user
        user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            google_id=google_id,
            google_refresh_token=token_response.json().get('refresh_token')
        )
        # Make the first user an admin
        if User.query.count() == 0:
            user.role = UserRole.ADMIN
        db.session.add(user)
    else:
        # Update existing user with Google info
        user.google_id = google_id
        user.first_name = first_name or user.first_name
        user.last_name = last_name or user.last_name
        if token_response.json().get('refresh_token'):
            user.google_refresh_token = token_response.json().get('refresh_token')
    
    db.session.commit()
    
    # Log in the user
    login_user(user)
    
    # Create access token
    access_token = create_access_token(identity=user.id)
    
    # Redirect to frontend with token
    frontend_url = current_app.config.get('FRONTEND_URL', '/')
    redirect_url = f"{frontend_url}?token={access_token}"
    return redirect(redirect_url)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()
    
    # Check if email already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    # Create new user
    user = User(
        email=data['email'],
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', '')
    )
    user.set_password(data['password'])
    
    # Make the first user an admin
    if User.query.count() == 0:
        user.role = UserRole.ADMIN
    
    # Save user to database
    db.session.add(user)
    db.session.commit()
    
    # Create access token
    access_token = create_access_token(identity=user.id)
    
    return jsonify({
        'message': 'User registered successfully',
        'user': {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role
        },
        'access_token': access_token
    }), 201

@auth_