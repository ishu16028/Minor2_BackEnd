# app/routes/favorites.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app.models.favorites import Favorite
from app import db

favorites_bp = Blueprint('favorites', __name__)

@favorites_bp.route('/', methods=['POST'])
@jwt_required()
def add_favorite():
    user_id = get_jwt_identity()
    data = request.get_json()

    # Check if company already in favorites
    existing = Favorite.query.filter_by(
        user_id=user_id,
        company_name=data['company_name']
    ).first()

    if existing:
        return jsonify({'message': 'Company already in favorites'}), 409

    # Add to favorites
    favorite = Favorite(
        user_id=user_id,
        company_name=data['company_name'],
        notes=data.get('notes', '')
    )

    db.session.add(favorite)
    db.session.commit()

    return jsonify({
        'message': 'Company added to favorites',
        'favorite': {
            'id': favorite.id,
            'company_name': favorite.company_name,
            'notes': favorite.notes
        }
    }), 201

@favorites_bp.route('/<int:favorite_id>', methods=['DELETE'])
@jwt_required()
def remove_favorite(favorite_id):
    user_id = get_jwt_identity()

    favorite = Favorite.query.filter_by(id=favorite_id, user_id=user_id).first()

    if not favorite:
        return jsonify({'message': 'Favorite not found or unauthorized'}), 404

    db.session.delete(favorite)
    db.session.commit()

    return jsonify({'message': 'Company removed from favorites'}), 200

@favorites_bp.route('/', methods=['GET'])
@jwt_required()
def get_favorites():
    user_id = get_jwt_identity()

    favorites = Favorite.query.filter_by(user_id=user_id).all()

    result = []
    for fav in favorites:
        result.append({
            'id': fav.id,
            'company_name': fav.company_name,
            'notes': fav.notes,
            'created_at': fav.created_at.strftime('%Y-%m-%d')
        })

    return jsonify({'favorites': result}), 200