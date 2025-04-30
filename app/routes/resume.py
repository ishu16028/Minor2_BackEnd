# app/routes/resume.py
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from app.models.user import User
from app.models.resume import Resume
from app.services.resume_parser import parse_resume
from app import db
import os
import json

resume_bp = Blueprint('resume', __name__)

ALLOWED_EXTENSIONS = {'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@resume_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_resume():
    user_id = get_jwt_identity()

    # Check if file was included
    if 'file' not in request.files:
        return jsonify({'message': 'No file provided'}), 400

    file = request.files['file']

    # Check if filename is empty
    if file.filename == '':
        return jsonify({'message': 'No file selected'}), 400

    # Check if file extension is allowed
    if not allowed_file(file.filename):
        return jsonify({'message': 'File type not supported. Please upload PDF or DOCX.'}), 400

    # Generate secure filename
    filename = secure_filename(file.filename)
    file_ext = filename.rsplit('.', 1)[1].lower()

    # Create path for resume file
    upload_folder = current_app.config['UPLOAD_FOLDER']
    user_folder = os.path.join(upload_folder, f'user_{user_id}')

    # Create user folder if it doesn't exist
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

    # Save file path
    file_path = os.path.join(user_folder, filename)

    # Save file to disk
    file.save(file_path)

    try:
        # Parse resume
        parsed_data = parse_resume(file_path)
        parsed_json = json.loads(parsed_data)

        # Return parsed data
        return jsonify({
            'message': 'Resume uploaded and parsed successfully',
            'resumeData': parsed_json
        }), 200

    except Exception as e:
        # If parsing fails, return error
        return jsonify({
            'message': f'Error parsing resume: {str(e)}',
            'resumePath': file_path
        }), 500

@resume_bp.route('/save', methods=['POST'])
@jwt_required()
def save_resume_data():
    user_id = get_jwt_identity()
    data = request.get_json()

    # Check if user has existing resume data
    existing_resume = Resume.query.filter_by(user_id=user_id).first()

    if existing_resume:
        # Update existing resume data
        existing_resume.name = data.get('name', '')
        existing_resume.email = data.get('contact_details', {}).get('email', '')
        existing_resume.phone = data.get('contact_details', {}).get('phone', '')
        existing_resume.linkedin = data.get('social_links', {}).get('LinkedIn', '')
        existing_resume.github = data.get('social_links', {}).get('GitHub', '')
        existing_resume.education = json.dumps(data.get('education', []))
        existing_resume.skills = json.dumps(data.get('skills', []))
        existing_resume.soft_skills = json.dumps(data.get('soft_skills', []))
        existing_resume.projects = json.dumps(data.get('projects', []))
        existing_resume.achievements = json.dumps(data.get('achievements', []))
        existing_resume.file_path = data.get('resumePath', existing_resume.file_path)

        db.session.commit()

        return jsonify({
            'message': 'Resume data updated successfully',
            'id': existing_resume.id
        }), 200
    else:
        # Create new resume data
        new_resume = Resume(
            user_id=user_id,
            name=data.get('name', ''),
            email=data.get('contact_details', {}).get('email', ''),
            phone=data.get('contact_details', {}).get('phone', ''),
            linkedin=data.get('social_links', {}).get('LinkedIn', ''),
            github=data.get('social_links', {}).get('GitHub', ''),
            education=json.dumps(data.get('education', [])),
            skills=json.dumps(data.get('skills', [])),
            soft_skills=json.dumps(data.get('soft_skills', [])),
            projects=json.dumps(data.get('projects', [])),
            achievements=json.dumps(data.get('achievements', [])),
            file_path=data.get('resumePath', '')
        )

        db.session.add(new_resume)
        db.session.commit()

        return jsonify({
            'message': 'Resume data saved successfully',
            'id': new_resume.id
        }), 201

@resume_bp.route('/', methods=['GET'])
@jwt_required()
def get_resume_data():
    user_id = get_jwt_identity()

    resume = Resume.query.filter_by(user_id=user_id).first()

    if not resume:
        return jsonify({'message': 'No resume data found'}), 404

    return jsonify({
        'resumeData': {
            'name': resume.name,
            'contact_details': {
                'email': resume.email,
                'phone': resume.phone
            },
            'social_links': {
                'LinkedIn': resume.linkedin,
                'GitHub': resume.github
            },
            'education': json.loads(resume.education) if resume.education else [],
            'skills': json.loads(resume.skills) if resume.skills else [],
            'soft_skills': json.loads(resume.soft_skills) if resume.soft_skills else [],
            'projects': json.loads(resume.projects) if resume.projects else [],
            'achievements': json.loads(resume.achievements) if resume.achievements else []
        }
    }), 200