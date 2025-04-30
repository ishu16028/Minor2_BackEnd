from datetime import datetime
from app import db

class JobSource:
    """Enum for job listing sources."""
    LINKEDIN = 'linkedin'
    INDEED = 'indeed'
    INTERNSHALA = 'internshala'
    GLASSDOOR = 'glassdoor'
    MONSTER = 'monster'
    OTHER = 'other'

class JobMode:
    """Enum for job modes."""
    REMOTE = 'remote'
    ONSITE = 'onsite'
    HYBRID = 'hybrid'

# Job-Skills association table
job_skills = db.Table('job_skills',
    db.Column('job_id', db.Integer, db.ForeignKey('jobs.id'), primary_key=True),
    db.Column('skill_name', db.String(50), primary_key=True)
)

class Job(db.Model):
    """Job model for storing job listings."""
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100))
    description = db.Column(db.Text)
    salary_min = db.Column(db.Float)
    salary_max = db.Column(db.Float)
    salary_currency = db.Column(db.String(10), default='USD')
    job_mode = db.Column(db.String(20))  # remote, onsite, hybrid
    working_hours = db.Column(db.String(100))  # e.g., "40 hours/week", "Part-time"
    application_url = db.Column(db.String(500))
    source = db.Column(db.String(50))  # linkedin, indeed, etc.
    source_job_id = db.Column(db.String(100))  # ID from the source platform
    posted_date = db.Column(db.DateTime)
    expiry_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    skills = db.relationship('Skill', secondary=job_skills, lazy='subquery',
                           backref=db.backref('jobs', lazy=True))
    applications = db.relationship('Application', backref='job', lazy=True)
    
    def __repr__(self):
        return f'<Job {self.title} at {self.company_name}>'

class Skill(db.Model):
    """Skill model for storing skills required by jobs."""
    __tablename__ = 'skills'
    
    name = db.Column(db.String(50), primary_key=True)
    category = db.Column(db.String(50))  # technical, soft skill, etc.
    
    def __repr__(self):
        return f'<Skill {self.name}>'