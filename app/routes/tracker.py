# app/routes/tracker.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User
from app.models.application import Application, ApplicationStatus, CustomStatus
from app import db

tracker_bp = Blueprint('tracker', __name__)

@tracker_bp.route('/application', methods=['POST'])
@jwt_required()
def add_application():
    user_id = get_jwt_identity()
    data = request.get_json()

    new_application = Application(
        user_id=user_id,
        company=data['company'],
        position=data['position'],
        location=data.get('location', ''),
        apply_date=data.get('apply_date'),
        apply_url=data.get('apply_url', ''),
        job_description=data.get('job_description', ''),
        notes=data.get('notes', ''),
        status=data.get('status', 'wishlist')
    )

    db.session.add(new_application)
    db.session.commit()

    return jsonify({
        'message': 'Application tracked successfully',
        'application': {
            'id': new_application.id,
            'company': new_application.company,
            'position': new_application.position,
            'status': new_application.status,
            'apply_date': new_application.apply_date.strftime('%Y-%m-%d') if new_application.apply_date else None
        }
    }), 201

@tracker_bp.route('/application/<int:app_id>', methods=['PUT'])
@jwt_required()
def update_application(app_id):
    user_id = get_jwt_identity()
    data = request.get_json()

    application = Application.query.filter_by(id=app_id, user_id=user_id).first()

    if not application:
        return jsonify({'message': 'Application not found or unauthorized'}), 404

    # Update fields
    if 'company' in data:
        application.company = data['company']
    if 'position' in data:
        application.position = data['position']
    if 'location' in data:
        application.location = data['location']
    if 'apply_date' in data:
        application.apply_date = data['apply_date']
    if 'apply_url' in data:
        application.apply_url = data['apply_url']
    if 'job_description' in data:
        application.job_description = data['job_description']
    if 'notes' in data:
        application.notes = data['notes']
    if 'status' in data:
        application.status = data['status']

    db.session.commit()

    return jsonify({
        'message': 'Application updated successfully',
        'application': {
            'id': application.id,
            'company': application.company,
            'position': application.position,
            'status': application.status,
            'apply_date': application.apply_date.strftime('%Y-%m-%d') if application.apply_date else None
        }
    }), 200

@tracker_bp.route('/application/<int:app_id>', methods=['DELETE'])
@jwt_required()
def delete_application(app_id):
    user_id = get_jwt_identity()

    application = Application.query.filter_by(id=app_id, user_id=user_id).first()

    if not application:
        return jsonify({'message': 'Application not found or unauthorized'}), 404

    db.session.delete(application)
    db.session.commit()

    return jsonify({'message': 'Application deleted successfully'}), 200

@tracker_bp.route('/applications', methods=['GET'])
@jwt_required()
def get_applications():
    user_id = get_jwt_identity()

    # Filter parameters
    status = request.args.get('status', '')
    company = request.args.get('company', '')

    query = Application.query.filter_by(user_id=user_id)

    if status:
        query = query.filter_by(status=status)
    if company:
        query = query.filter(Application.company.ilike(f'%{company}%'))

    applications = query.order_by(Application.apply_date.desc()).all()

    result = []
    for app in applications:
        result.append({
            'id': app.id,
            'company': app.company,
            'position': app.position,
            'location': app.location,
            'apply_date': app.apply_date.strftime('%Y-%m-%d') if app.apply_date else None,
            'apply_url': app.apply_url,
            'job_description': app.job_description,
            'notes': app.notes,
            'status': app.status,
            'created_at': app.created_at.strftime('%Y-%m-%d')
        })

    return jsonify({'applications': result}), 200

@tracker_bp.route('/custom-status', methods=['POST'])
@jwt_required()
def add_custom_status():
    user_id = get_jwt_identity()
    data = request.get_json()

    new_status = CustomStatus(
        user_id=user_id,
        name=data['name'],
        color=data.get('color', '#cccccc')
    )

    db.session.add(new_status)
    db.session.commit()

    return jsonify({
        'message': 'Custom status created successfully',
        'status': {
            'id': new_status.id,
            'name': new_status.name,
            'color': new_status.color
        }
    }), 201

@tracker_bp.route('/custom-status', methods=['GET'])
@jwt_required()
def get_custom_statuses():
    user_id = get_jwt_identity()

    # Get default statuses
    default_statuses = [
        {'id': 'wishlist', 'name': 'Wishlist', 'color': '#FFD700', 'is_default': True},
        {'id': 'applied', 'name': 'Applied', 'color': '#1E90FF', 'is_default': True},
        {'id': 'waiting', 'name': 'Waiting', 'color': '#FFA500', 'is_default': True},
        {'id': 'interview', 'name': 'Interview Scheduled', 'color': '#9932CC', 'is_default': True},
        {'id': 'rejected', 'name': 'Rejected', 'color': '#FF0000', 'is_default': True},
        {'id': 'offer', 'name': 'Offer Received', 'color': '#008000', 'is_default': True}
    ]

    # Get user's custom statuses
    custom_statuses = CustomStatus.query.filter_by(user_id=user_id).all()

    # Format custom statuses
    custom_results = []
    for status in custom_statuses:
        custom_results.append({
            'id': status.id,
            'name': status.name,
            'color': status.color,
            'is_default': False
        })

    return jsonify({
        'statuses': default_statuses + custom_results
    }), 200