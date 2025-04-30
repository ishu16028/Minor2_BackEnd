# app/routes/auth.py
from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from app.models.user import User
from app import db
import requests
import json
from oauthlib.oauth2 import WebApplicationClient
import os

auth_bp = Blueprint('auth', __name__)
client = WebApplicationClient(current_app.config['GOOGLE_CLIENT_ID'])

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    # Check if user exists
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({'message': 'Email already registered'}), 409

    # Create new user
    new_user = User(
        email=data['email'],
        password=generate_password_hash(data['password']),
        first_name=data['first_name'],
        last_name=data['last_name'],
        role='user'
    )

    db.session.add(new_user)
    db.session.commit()

    # Create token
    access_token = create_access_token(identity=new_user.id)

    return jsonify({
        'message': 'User registered successfully',
        'access_token': access_token,
        'user': {
            'id': new_user.id,
            'email': new_user.email,
            'first_name': new_user.first_name,
            'last_name': new_user.last_name,
            'role': new_user.role
        }
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    user = User.query.filter_by(email=data['email']).first()

    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401

    access_token = create_access_token(identity=user.id)

    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role
        }
    }), 200

@auth_bp.route('/google', methods=['GET'])
def google_login():
    # Google OAuth configuration
    google_provider_cfg = requests.get(current_app.config['GOOGLE_DISCOVERY_URL']).json()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    # Use library to construct the request for Google login
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=request.base_url + "/callback",
        scope=["openid", "email", "profile"],
    )

    return jsonify({'redirect_url': request_uri})

@auth_bp.route('/google/callback', methods=['GET'])
def google_callback():
    # Get authorization code from request
    code = request.args.get("code")

    # Get Google provider configuration
    google_provider_cfg = requests.get(current_app.config['GOOGLE_DISCOVERY_URL']).json()
    token_endpoint = google_provider_cfg["token_endpoint"]

    # Prepare and send request to get tokens
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(current_app.config['GOOGLE_CLIENT_ID'], current_app.config['GOOGLE_CLIENT_SECRET']),
    )

    # Parse token response
    client.parse_request_body_response(json.dumps(token_response.json()))

    # Get user info using token
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    # Make sure the email is verified
    user_info = userinfo_response.json()
    if not user_info.get("email_verified"):
        return jsonify({'message': 'Email not verified with Google'}), 400

    # Find or create user
    user = User.query.filter_by(email=user_info["email"]).first()
    if not user:
        user = User(
            email=user_info["email"],
            first_name=user_info.get("given_name", ""),
            last_name=user_info.get("family_name", ""),
            password=None,  # No password for OAuth
            oauth_provider="google",
            role="user"
        )
        db.session.add(user)
        db.session.commit()

    # Create token
    access_token = create_access_token(identity=user.id)

    return jsonify({
        'message': 'Google login successful',
        'access_token': access_token,
        'user': {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role
        }
    }), 200

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'message': 'User not found'}), 404

    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role
        }
    }), 200