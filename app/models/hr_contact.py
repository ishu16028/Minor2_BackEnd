from datetime import datetime
from app import db

class HRContact(db.Model):
    """HR Contact model for cold emailing functionality."""
    __tablename__ = 'hr_contacts'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), nullable=False, unique=True)
    company_name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100))
    linkedin_url = db.Column(db.String(200))
    department = db.Column(db.String(100))
    notes = db.Column(db.Text)
    
    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<HRContact {self.name} at {self.company_name}>'

class EmailTemplate(db.Model):
    """Email templates for cold emailing."""
    __tablename__ = 'email_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    
    # For user-specific templates
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<EmailTemplate {self.name}>'

class EmailDraft(db.Model):
    """Stored email drafts sent to Gmail."""
    __tablename__ = 'email_drafts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    hr_contact_id = db.Column(db.Integer, db.ForeignKey('hr_contacts.id'))
    
    recipient_email = db.Column(db.String(120), nullable=False)
    recipient_name = db.Column(db.String(100))
    subject = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    
    gmail_draft_id = db.Column(db.String(100))  # ID returned by Gmail API
    status = db.Column(db.String(20))  # draft, sent, error
    error_message = db.Column(db.Text)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    hr_contact = db.relationship('HRContact', backref='email_drafts')
    
    def __repr__(self):
        return f'<EmailDraft to {self.recipient_email} - {self.status}>'