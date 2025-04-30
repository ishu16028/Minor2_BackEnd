# app/routes/email.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services.email_service import (
    get_gmail_service,
    get_available_templates,
    prepare_cold_email,
    create_email_draft
)
from app.models.user import User
from app.models.hr_contact import HRContact
from app import db

email_bp = Blueprint('email', __name__)


@email_bp.route('/templates', methods=['GET'])
@jwt_required()
def get_templates():
    """Get available email templates"""
    try:
        templates = get_available_templates()
        return jsonify({'templates': templates}), 200
    except Exception as e:
        current_app.logger.error(f"Error retrieving templates: {e}")
        return jsonify({'message': f'Error retrieving templates: {str(e)}'}), 500


@email_bp.route('/preview', methods=['POST'])
@jwt_required()
def preview_email():
    """Preview personalized email content"""
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or 'template_id' not in data:
        return jsonify({'message': 'Template ID is required'}), 400

    try:
        # Get template content and personalize it
        result = prepare_cold_email(
            data['template_id'],
            user_id,
            data.get('hr_contact_id'),
            data.get('company_name'),
            data.get('subject')
        )

        if not result['success']:
            return jsonify({'message': result['error']}), 400

        return jsonify({
            'to': result['to'],
            'subject': result['subject'],
            'body': result['body']
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error previewing email: {e}")
        return jsonify({'message': f'Error previewing email: {str(e)}'}), 500


@email_bp.route('/draft', methods=['POST'])
@jwt_required()
def create_draft():
    """Create Gmail draft with personalized content"""
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or 'template_id' not in data or 'to' not in data:
        return jsonify({'message': 'Missing required fields'}), 400

    try:
        # Get user to check for Google token
        user = User.query.get(user_id)
        if not user or not user.google_token:
            return jsonify({'message': 'Google account connection required'}), 403

        # Get email content
        result = prepare_cold_email(
            data['template_id'],
            user_id,
            data.get('hr_contact_id'),
            data.get('company_name'),
            data.get('subject')
        )

        if not result['success']:
            return jsonify({'message': result['error']}), 400

        # Create draft using Gmail API
        gmail_service = get_gmail_service(user.google_token)

        # Override recipient if provided
        to_email = data['to'] if 'to' in data else result['to']
        subject = data.get('subject', result['subject'])
        body = data.get('body', result['body'])

        draft_result = create_email_draft(
            gmail_service,
            to_email,
            subject,
            body
        )

        if not draft_result['success']:
            return jsonify({'message': draft_result['error']}), 500

        return jsonify({
            'message': 'Email draft created successfully',
            'draft_id': draft_result['draft_id']
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error creating email draft: {e}")
        return jsonify({'message': f'Error creating email draft: {str(e)}'}), 500


@email_bp.route('/hr-contacts', methods=['GET'])
@jwt_required()
def get_hr_contacts():
    """Get list of HR contacts for email drafting"""
    try:
        hr_contacts = HRContact.query.all()

        result = [{
            'id': contact.id,
            'company_name': contact.company_name,
            'contact_name': contact.contact_name,
            'email': contact.email,
            'position': contact.position
        } for contact in hr_contacts]

        return jsonify({'contacts': result}), 200

    except Exception as e:
        current_app.logger.error(f"Error retrieving HR contacts: {e}")
        return jsonify({'message': f'Error retrieving HR contacts: {str(e)}'}), 500