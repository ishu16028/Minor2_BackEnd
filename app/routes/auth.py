# app/routes/auth.py
from flask import Blueprint, request, jsonify, redirect, url_for, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models.user import User, Role
from app.services.auth_service import (
    hash_password,
    verify_password,
    get_google_auth_url,
    exchange_code_for_tokens,
    get_google_user_info
)
from app import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()

    # Validate required fields
    if not all(k in data for k in ['email', 'password', 'name']):
        return jsonify({'message': 'Missing required fields'}), 400

    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'User already exists with this email'}), 409

    # Create new user
    new_user = User(
        name=data['name'],
        email=data['email'],
        password_hash=hash_password(data['password']),
        role=Role.USER
    )

    db.session.add(new_user)
    db.session.commit()

    # Generate access token
    access_token = create_access_token(identity=new_user.id)

    return jsonify({
        'message': 'User registered successfully',
        'access_token': access_token,
        'user': {
            'id': new_user.id,
            'name': new_user.name,
            'email': new_user.email,
            'role': new_user.role.value
        }
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login user with email and password"""
    data = request.get_json()

    # Validate required fields
    if not all(k in data for k in ['email', 'password']):
        return jsonify({'message': 'Missing email or password'}), 400

    # Find user by email
    user = User.query.filter_by(email=data['email']).first()

    # Check if user exists and password is correct
    if not user or not verify_password(user.password_hash, data['password']):
        return jsonify({'message': 'Invalid email or password'}), 401

    # Generate access token
    access_token = create_access_token(identity=user.id)

    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role.value
        }
    }), 200

@auth_bp.route('/google-auth-url', methods=['GET'])
def google_auth_url():
    """Get Google OAuth authorization URL"""
    auth_url = get_google_auth_url()
    return jsonify({'auth_url': auth_url}), 200

@auth_bp.route('/google-callback', methods=['GET'])
def google_callback():
    """Handle Google OAuth callback"""
    code = request.args.get('code')
    if not code:
        return jsonify({'message': 'Authorization code not provided'}), 400

    # Exchange code for tokens
    token_data = exchange_code_for_tokens(code)
    if not token_data:
        return jsonify({'message': 'Failed to exchange code for tokens'}), 400

    # Get user information from Google
    user_info = get_google_user_info(token_data['access_token'])
    if not user_info:
        return jsonify({'message': 'Failed to get user info from Google'}), 400

    # Check if user already exists
    user = User.query.filter_by(email=user_info['email']).first()

    if user:
        # Update existing user with Google token
        user.google_token = token_data
        user.name = user_info.get('name', user.name)
        db.session.commit()
    else:
        # Create new user
        new_user = User(
            name=user_info.get('name', 'Google User'),
            email=user_info['email'],
            google_token=token_data,
            role=Role.USER
        )
        db.session.add(new_user)
        db.session.commit()
        user = new_user

    # Generate access token
    access_token = create_access_token(identity=user.id)

    # For API, return JSON. For web, redirect to frontend with token
    if request.headers.get('Accept') == 'application/json':
        return jsonify({
            'message': 'Google login successful',
            'access_token': access_token,
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': user.role.value
            }
        }), 200
    else:
        # Redirect to frontend with token
        frontend_url = current_app.config.get('FRONTEND_URL', 'http://localhost:3000')
        return redirect(f"{frontend_url}/auth/callback?token={access_token}")

@auth_bp.route('/user', methods=['GET'])
@jwt_required()
def get_user():
    """Get current user information"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'message': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'name': user.name,
        'email': user.email,
        'role': user.role.value,
        'has_google_connection': bool(user.google_token),
        'created_at': user.created_at.strftime('%Y-%m-%d')
    }), 200

@auth_bp.route('/user', methods=['PUT'])
@jwt_required()
def update_user():
    """Update user profile"""
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'message': 'User not found'}), 404

    data = request.get_json()

    # Update fields if provided
    if 'name' in data:
        user.name = data['name']

    # Update password if provided
    if 'password' in data and data['password']:
        user.password_hash = hash_password(data['password'])

    db.session.commit()

    return jsonify({
        'message': 'User profile updated successfully',
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role.value
        }
    }), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout user (client should discard token)"""
    return jsonify({'message': 'Logout successful'}), 200