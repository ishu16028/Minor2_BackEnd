from app import db
from datetime import datetime
from sqlalchemy.dialects.mysql import JSON


class Resume(db.Model):
    """Model for user resumes and parsed data"""
    __tablename__ = 'resumes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_name = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)  # pdf or docx
    
    # Parsed data stored as JSON
    parsed_data = db.Column(JSON, nullable=True)
    
    # Specific extracted fields for easy querying
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    linkedin_url = db.Column(db.String(255), nullable=True)
    github_url = db.Column(db.String(255), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('resumes', lazy=True))
    skills = db.relationship('ResumeSkill', back_populates='resume', cascade='all, delete-orphan')
    education = db.relationship('Education', back_populates='resume', cascade='all, delete-orphan')
    projects = db.relationship('Project', back_populates='resume', cascade='all, delete-orphan')
    achievements = db.relationship('Achievement', back_populates='resume', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Resume {self.file_name} for user {self.user_id}>'
    
    def to_dict(self):
        """Convert resume data to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'file_name': self.file_name,
            'file_type': self.file_type,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'linkedin_url': self.linkedin_url,
            'github_url': self.github_url,
            'skills': [skill.to_dict() for skill in self.skills],
            'education': [edu.to_dict() for edu in self.education],
            'projects': [project.to_dict() for project in self.projects],
            'achievements': [achievement.name for achievement in self.achievements],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @classmethod
    def from_parsed_data(cls, user_id, file_path, file_name, file_type, parsed_data):
        """Create a resume instance and related models from parsed data"""
        resume = cls(
            user_id=user_id,
            file_path=file_path,
            file_name=file_name,
            file_type=file_type,
            parsed_data=parsed_data,
            name=parsed_data.get('name', ''),
            email=parsed_data.get('contact_details', {}).get('email', ''),
            phone=parsed_data.get('contact_details', {}).get('phone', ''),
            linkedin_url=parsed_data.get('social_links', {}).get('LinkedIn', ''),
            github_url=parsed_data.get('social_links', {}).get('GitHub', '')
        )
        
        return resume


class ResumeSkill(db.Model):
    """Model for skills extracted from resume"""
    __tablename__ = 'resume_skills'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_soft_skill = db.Column(db.Boolean, default=False)
    
    # Relationship
    resume = db.relationship('Resume', back_populates='skills')
    
    def __repr__(self):
        return f'<ResumeSkill {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'is_soft_skill': self.is_soft_skill
        }


class Education(db.Model):
    """Model for education details extracted from resume"""
    __tablename__ = 'education'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    degree = db.Column(db.String(255), nullable=False)
    institution = db.Column(db.String(255), nullable=False)
    cgpa = db.Column(db.String(10), nullable=True)
    start_date = db.Column(db.String(50), nullable=True)
    end_date = db.Column(db.String(50), nullable=True)
    
    # Relationship
    resume = db.relationship('Resume', back_populates='education')
    
    def __repr__(self):
        return f'<Education {self.degree} at {self.institution}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'degree': self.degree,
            'institution': self.institution,
            'cgpa': self.cgpa,
            'start_date': self.start_date,
            'end_date': self.end_date
        }


class Project(db.Model):
    """Model for projects extracted from resume"""
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    tech_stack = db.Column(db.String(255), nullable=True)
    
    # Relationship
    resume = db.relationship('Resume', back_populates='projects')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'tech_stack': self.tech_stack
        }


class Achievement(db.Model):
    """Model for achievements extracted from resume"""
    __tablename__ = 'achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'), nullable=False)
    name = db.Column(db.Text, nullable=False)
    
    # Relationship
    resume = db.relationship('Resume', back_populates='achievements')
    
    def __repr__(self):
        return f'<Achievement for resume {self.resume_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name
        }
