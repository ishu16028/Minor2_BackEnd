# app/routes/jobs.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.job import Job
from app.models.user import User
from app.services.job_scraper import LinkedInScraper, IndeedScraper, InternshalaScaper
from app import db

jobs_bp = Blueprint('jobs', __name__)

@jobs_bp.route('/scrape', methods=['POST'])
@jwt_required()
def scrape_jobs():
    # Check if user is admin
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user or user.role != 'admin':
        return jsonify({'message': 'Admin access required'}), 403

    # Get parameters from request
    data = request.get_json()
    sources = data.get('sources', ['linkedin', 'indeed', 'internshala'])
    keywords = data.get('keywords', [])
    location = data.get('location', '')

    scraped_jobs = []

    # Scrape from selected sources
    if 'linkedin' in sources:
        linkedin_scraper = LinkedInScraper()
        linkedin_jobs = linkedin_scraper.scrape(keywords, location)
        scraped_jobs.extend(linkedin_jobs)

    if 'indeed' in sources:
        indeed_scraper = IndeedScraper()
        indeed_jobs = indeed_scraper.scrape(keywords, location)
        scraped_jobs.extend(indeed_jobs)

    if 'internshala' in sources:
        internshala_scraper = InternshalaScaper()
        internshala_jobs = internshala_scraper.scrape(keywords, location)
        scraped_jobs.extend(internshala_jobs)

    # Save jobs to database
    new_jobs_count = 0
    for job_data in scraped_jobs:
        # Check if job already exists by URL
        existing_job = Job.query.filter_by(apply_url=job_data['apply_url']).first()
        if not existing_job:
            new_job = Job(
                title=job_data['title'],
                company=job_data['company'],
                location=job_data['location'],
                description=job_data['description'],
                apply_url=job_data['apply_url'],
                source=job_data['source'],
                job_mode=job_data.get('job_mode', 'Not specified'),
                working_hours=job_data.get('working_hours', 'Not specified'),
                salary=job_data.get('salary', 'Not specified'),
                skills=','.join(job_data.get('skills', [])),
                posted_date=job_data.get('posted_date')
            )
            db.session.add(new_job)
            new_jobs_count += 1

    db.session.commit()

    return jsonify({
        'message': f'Job scraping completed. Added {new_jobs_count} new jobs.',
        'total_scraped': len(scraped_jobs)
    }), 200

@jobs_bp.route('/list', methods=['GET'])
@jwt_required()
def list_jobs():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)

    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Get query parameters for filtering
    job_mode = request.args.get('job_mode', '')
    working_hours = request.args.get('working_hours', '')
    role = request.args.get('role', '')
    salary_min = request.args.get('salary_min', '')
    salary_max = request.args.get('salary_max', '')
    location = request.args.get('location', '')
    skills = request.args.getlist('skills')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))

    # Build query
    query = Job.query

    if job_mode:
        query = query.filter(Job.job_mode.ilike(f'%{job_mode}%'))
    if working_hours:
        query = query.filter(Job.working_hours.ilike(f'%{working_hours}%'))
    if role:
        query = query.filter(Job.title.ilike(f'%{role}%'))
    if location:
        query = query.filter(Job.location.ilike(f'%{location}%'))

    # Handle salary filter - parse numeric values from salary strings
    if salary_min or salary_max:
        pass  # Implement salary filter logic based on your data format

    # Filter by skills (if job has any of the required skills)
    if skills:
        for skill in skills:
            query = query.filter(Job.skills.ilike(f'%{skill}%'))

    # Get user's favorite companies
    favorite_companies = [fav.company_name.lower() for fav in user.favorites]

    # Get all jobs matching filters
    all_jobs = query.all()

    # Sort jobs - exact match favorited companies first, then partial match favorites
    exact_matches = []
    partial_matches = []
    others = []

    for job in all_jobs:
        company_name = job.company.lower()

        if company_name in favorite_companies:
            exact_matches.append(job)
        elif any(fav in company_name for fav in favorite_companies):
            partial_matches.append(job)
        else:
            others.append(job)

    # Combine all sorted results
    sorted_jobs = exact_matches + partial_matches + others

    # Paginate results
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_jobs = sorted_jobs[start_idx:end_idx]

    # Format jobs for response
    result = []
    for job in paginated_jobs:
        result.append({
            'id': job.id,
            'title': job.title,
            'company': job.company,
            'location': job.location,
            'description': job.description,
            'apply_url': job.apply_url,
            'source': job.source,
            'job_mode': job.job_mode,
            'working_hours': job.working_hours,
            'salary': job.salary,
            'skills': job.skills.split(',') if job.skills else [],
            'posted_date': job.posted_date.strftime('%Y-%m-%d') if job.posted_date else None,
            'is_favorite': job.company.lower() in favorite_companies or any(fav in job.company.lower() for fav in favorite_companies)
        })

    return jsonify({
        'jobs': result,
        'total': len(sorted_jobs),
        'page': page,
        'per_page': per_page,
        'total_pages': (len(sorted_jobs) + per_page - 1) // per_page
    }), 200