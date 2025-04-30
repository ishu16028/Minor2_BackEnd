# app/routes/admin.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User, Role
from app.models.hr_contact import HRContact
from app.models.job import Job
from app.services.job_scraper import trigger_job_scraping
from app import db
from datetime import datetime
import json

admin_bp = Blueprint('admin', __name__)

# Decorator to check if user is admin
def admin_required(fn):
    def wrapper(*args, **kwargs):
        user_id = get_jwt_identity()
        user = User.query.get(user_id)

        if not user or user.role != Role.ADMIN:
            return jsonify({'message': 'Admin access required'}), 403

        return fn(*args, **kwargs)

    wrapper.__name__ = fn.__name__
    return wrapper

@admin_bp.route('/users', methods=['GET'])
@jwt_required()
@admin_required
def get_users():
    """Get all users (admin only)"""
    users = User.query.all()

    result = [{
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'role': user.role.value,
        'created_at': user.created_at.strftime('%Y-%m-%d')
    } for user in users]

    return jsonify({'users': result}), 200

@admin_bp.route('/user/<int:user_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_user(user_id):
    """Delete a user (admin only)"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    db.session.delete(user)
    db.session.commit()

    return jsonify({'message': 'User deleted successfully'}), 200

# HR Contact Management
@admin_bp.route('/hr-contacts', methods=['POST'])
@jwt_required()
@admin_required
def add_hr_contact():
    """Add a new HR contact (admin only)"""
    data = request.get_json()

    # Validate required fields
    if not all(k in data for k in ['company_name', 'contact_name', 'email']):
        return jsonify({'message': 'Missing required fields'}), 400

    # Create new HR contact
    new_contact = HRContact(
        company_name=data['company_name'],
        contact_name=data['contact_name'],
        email=data['email'],
        position=data.get('position', ''),
        notes=data.get('notes', '')
    )

    db.session.add(new_contact)
    db.session.commit()

    return jsonify({
        'message': 'HR contact added successfully',
        'contact': {
            'id': new_contact.id,
            'company_name': new_contact.company_name,
            'contact_name': new_contact.contact_name,
            'email': new_contact.email
        }
    }), 201

@admin_bp.route('/hr-contact/<int:contact_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_hr_contact(contact_id):
    """Update an HR contact (admin only)"""
    contact = HRContact.query.get(contact_id)
    if not contact:
        return jsonify({'message': 'HR contact not found'}), 404

    data = request.get_json()

    # Update fields if provided
    if 'company_name' in data:
        contact.company_name = data['company_name']
    if 'contact_name' in data:
        contact.contact_name = data['contact_name']
    if 'email' in data:
        contact.email = data['email']
    if 'position' in data:
        contact.position = data['position']
    if 'notes' in data:
        contact.notes = data['notes']

    db.session.commit()

    return jsonify({
        'message': 'HR contact updated successfully',
        'contact': {
            'id': contact.id,
            'company_name': contact.company_name,
            'contact_name': contact.contact_name,
            'email': contact.email,
            'position': contact.position
        }
    }), 200

@admin_bp.route('/hr-contact/<int:contact_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_hr_contact(contact_id):
    """Delete an HR contact (admin only)"""
    contact = HRContact.query.get(contact_id)
    if not contact:
        return jsonify({'message': 'HR contact not found'}), 404

    db.session.delete(contact)
    db.session.commit()

    return jsonify({'message': 'HR contact deleted successfully'}), 200

# Job Scraping Controls
@admin_bp.route('/jobs/scrape', methods=['POST'])
@jwt_required()
@admin_required
def scrape_jobs():
    """Trigger job scraping (admin only)"""
    data = request.get_json()
    sources = data.get('sources', ['linkedin', 'indeed', 'internshala'])
    limit = data.get('limit', 100)

    try:
        result = trigger_job_scraping(sources, limit)
        return jsonify({
            'message': 'Job scraping completed',
            'jobs_added': result['jobs_added'],
            'sources': result['sources']
        }), 200
    except Exception as e:
        return jsonify({'message': f'Job scraping failed: {str(e)}'}), 500

@admin_bp.route('/jobs/manage', methods=['GET'])
@jwt_required()
@admin_required
def get_all_jobs():
    """Get all scraped jobs (admin only)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    jobs = Job.query.paginate(page=page, per_page=per_page)

    result = {
        'total': jobs.total,
        'pages': jobs.pages,
        'current_page': jobs.page,
        'jobs': [{
            'id': job.id,
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'job_type': job.job_type,
            'salary': job.salary,
            'url': job.url,
            'source': job.source,
            'posted_date': job.posted_date.strftime('%Y-%m-%d') if job.posted_date else None,
            'scraped_date': job.scraped_date.strftime('%Y-%m-%d')
        } for job in jobs.items]
    }

    return jsonify(result), 200

@admin_bp.route('/jobs/<int:job_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_job(job_id):
    """Delete a job listing (admin only)"""
    job = Job.query.get(job_id)
    if not job:
        return jsonify({'message': 'Job not found'}), 404

    db.session.delete(job)
    db.session.commit()

    return jsonify({'message': 'Job deleted successfully'}), 200

@admin_bp.route('/stats', methods=['GET'])
@jwt_required()
@admin_required
def get_admin_stats():
    """Get admin dashboard statistics"""
    total_users = User.query.count()
    total_jobs = Job.query.count()
    total_hr_contacts = HRContact.query.count()

    # Get recent jobs
    recent_jobs = Job.query.order_by(Job.scraped_date.desc()).limit(5).all()
    recent_jobs_data = [{
        'id': job.id,
        'title': job.title,
        'company': job.company,
        'source': job.source,
        'scraped_date': job.scraped_date.strftime('%Y-%m-%d')
    } for job in recent_jobs]

    # Get user registration stats (last 7 days)
    user_stats = db.session.query(
        db.func.date(User.created_at),
        db.func.count(User.id)
    ).group_by(db.func.date(User.created_at)).order_by(db.func.date(User.created_at).desc()).limit(7).all()

    user_stats_data = [{
        'date': date.strftime('%Y-%m-%d') if date else None,
        'count': count
    } for date, count in user_stats]

    return jsonify({
        'total_users': total_users,
        'total_jobs': total_jobs,
        'total_hr_contacts': total_hr_contacts,
        'recent_jobs': recent_jobs_data,
        'user_stats': user_stats_data
    }), 200