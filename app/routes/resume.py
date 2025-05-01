# app/routes/resume.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import json
from werkzeug.utils import secure_filename
from app.models.user import User
from app.models.resume import Resume
from app.services.resume_parser import parse_resume
from app import db
import uuid

resume_bp = Blueprint('resume', __name__)

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'pdf', 'docx'}

@resume_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_resume():
    """Upload and parse resume"""
    user_id = get_jwt_identity()

    # Check if file is in request
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400

    file = request.files['file']

    # Check if file is empty
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    # Check if file type is allowed
    if not allowed_file(file.filename):
        return jsonify({'message': 'File type not allowed. Please upload PDF or DOCX file'}), 400

    try:
        # Generate unique filename to avoid conflicts
        original_filename = secure_filename(file.filename)
        filename = f"{uuid.uuid4()}_{original_filename}"

        # Ensure upload directory exists
        upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'resumes', str(user_id))
        os.makedirs(upload_dir, exist_ok=True)

        # Save file
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)

        # Parse resume
        parsed_data = parse_resume(file_path)

        # Convert string to JSON if needed
        if isinstance(parsed_data, str):
            parsed_data = json.loads(parsed_data)

        # Return parsed data to user for review/confirmation
        return jsonify({
            'message': 'Resume uploaded and parsed successfully',
            'data': parsed_data,
            'resume_path': file_path
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error parsing resume: {e}")
        return jsonify({'message': f'Error parsing resume: {str(e)}'}), 500

@resume_bp.route('/save', methods=['POST'])
@jwt_required()
def save_resume_data():
    """Save or update parsed resume data"""
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data:
        return jsonify({'message': 'No data provided'}), 400

    try:
        # Check if user already has a resume
        existing_resume = Resume.query.filter_by(user_id=user_id).first()

        if existing_resume:
            # Update existing resume
            existing_resume.data = data
            existing_resume.updated_at = db.func.now()
            db.session.commit()
            return jsonify({'message': 'Resume data updated successfully'}), 200
        else:
            # Create new resume
            file_path = data.pop('resume_path', None)
            new_resume = Resume(
                user_id=user_id,
                file_path=file_path,
                data=data
            )
            db.session.add(new_resume)
            db.session.commit()
            return jsonify({'message': 'Resume data saved successfully'}), 201

    except Exception as e:
        current_app.logger.error(f"Error saving resume data: {e}")
        return jsonify({'message': f'Error saving resume data: {str(e)}'}), 500

@resume_bp.route('/', methods=['GET'])
@jwt_required()
def get_resume_data():
    """Get user's resume data"""
    user_id = get_jwt_identity()

    resume = Resume.query.filter_by(user_id=user_id).first()

    if not resume:
        return jsonify({'message': 'No resume found for this user'}), 404

    return jsonify({
        'resume_id': resume.id,
        'data': resume.data,
        'created_at': resume.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': resume.updated_at.strftime('%Y-%m-%d %H:%M:%S') if resume.updated_at else None
    }), 200

@resume_bp.route('/', methods=['DELETE'])
@jwt_required()
def delete_resume():
    """Delete user's resume"""
    user_id = get_jwt_identity()

    resume = Resume.query.filter_by(user_id=user_id).first()

    if not resume:
        return jsonify({'message': 'No resume found for this user'}), 404

    try:
        # Delete file if it exists
        if resume.file_path and os.path.exists(resume.file_path):
            os.remove(resume.file_path)

        # Delete database record
        db.session.delete(resume)
        db.session.commit()

        return jsonify({'message': 'Resume deleted successfully'}), 200

    except Exception as e:
        current_app.logger.error(f"Error deleting resume: {e}")
        return jsonify({'message': f'Error deleting resume: {str(e)}'}), 500