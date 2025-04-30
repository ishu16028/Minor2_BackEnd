from datetime import datetime
from app import db

class ApplicationStatus:
    """Enum for application statuses."""
    WISHLIST = 'wishlist'  # Interested but haven't applied
    APPLIED = 'applied'    # Applied
    WAITING = 'waiting'    # Waiting for response
    INTERVIEW = 'interview'  # Interview scheduled
    REJECTED = 'rejected'    # Rejected
    OFFER = 'offer'          # Offer received
    ACCEPTED = 'accepted'    # Offer accepted
    DECLINED = 'declined'    # Offer declined

class Application(db.Model):
    """Application model for tracking job applications."""
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=True)  # Nullable for manual entries
    
    # For manually added applications (not linked to scraped jobs)
    company_name = db.Column(db.String(100))
    job_title = db.Column(db.String(200))
    location = db.Column(db.String(100))
    job_mode = db.Column(db.String(20))
    
    # Application details
    status = db.Column(db.String(50), default=ApplicationStatus.WISHLIST)
    custom_tag = db.Column(db.String(50))  # For user-defined custom tags
    applied_date = db.Column(db.DateTime)
    next_followup_date = db.Column(db.DateTime)
    offer_details = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Application events (interviews, etc.)
    events = db.relationship('ApplicationEvent', backref='application', 
                           lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        job_name = self.job.title if self.job_id else self.job_title
        company = self.job.company_name if self.job_id else self.company_name
        return f'<Application for {job_name} at {company} - {self.status}>'

class ApplicationEvent(db.Model):
    """Events related to job applications (interviews, follow-ups, etc.)."""
    __tablename__ = 'application_events'
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False)
    
    event_type = db.Column(db.String(50), nullable=False)  # interview, followup, etc.
    event_date = db.Column(db.DateTime, nullable=False)
    details = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ApplicationEvent {self.event_type} on {self.event_date}>'