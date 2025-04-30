# app/services/auth_service.py
from flask import current_app, request, url_for
import requests
from datetime import datetime, timedelta
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json

def generate_jwt_token(user_id, role, expires_in=86400):
    """Generate a JWT token for the user"""
    payload = {
        'exp': datetime.utcnow() + timedelta(seconds=expires_in),
        'iat': datetime.utcnow(),
        'sub': user_id,
        'role': role
    }
    return jwt.encode(
        payload,
        current_app.config.get('SECRET_KEY'),
        algorithm='HS256'
    )

def decode_jwt_token(token):
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(
            token,
            current_app.config.get('SECRET_KEY'),
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        return {'error': 'Token expired'}
    except jwt.InvalidTokenError:
        return {'error': 'Invalid token'}

def hash_password(password):
    """Hash a password using werkzeug's security functions"""
    return generate_password_hash(password)

def verify_password(hashed_password, password):
    """Verify password against hashed version"""
    return check_password_hash(hashed_password, password)

def get_google_auth_url():
    """Generate Google OAuth authorization URL"""
    google_client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    redirect_uri = url_for('auth.google_callback', _external=True)

    # Google OAuth2 endpoints
    auth_url = 'https://accounts.google.com/o/oauth2/auth'

    # Parameters for authorization request
    params = {
        'client_id': google_client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile https://www.googleapis.com/auth/gmail.compose',
        'access_type': 'offline',
        'prompt': 'consent'  # Always ask for consent to get refresh token
    }

    # Convert parameters to query string
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])

    return f"{auth_url}?{query_string}"

def exchange_code_for_tokens(code):
    """Exchange authorization code for access and refresh tokens"""
    google_client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    google_client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
    redirect_uri = url_for('auth.google_callback', _external=True)

    # Google OAuth2 token endpoint
    token_url = 'https://oauth2.googleapis.com/token'

    # Parameters for token request
    data = {
        'client_id': google_client_id,
        'client_secret': google_client_secret,
        'code': code,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code'
    }

    response = requests.post(token_url, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        current_app.logger.error(f"Error exchanging code for tokens: {response.text}")
        return None

def get_google_user_info(access_token):
    """Get user info from Google using access token"""
    user_info_url = 'https://www.googleapis.com/oauth2/v3/userinfo'
    headers = {'Authorization': f'Bearer {access_token}'}

    response = requests.get(user_info_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        current_app.logger.error(f"Error getting user info: {response.text}")
        return None