from datetime import datetime
from flask_login import UserMixin
from app import db, login_manager, bcrypt

# User role enum
class UserRole:
    ADMIN = 'admin'
    USER = 'user'

# User-favorite companies association table
user_favorite_companies = db.Table('user_favorite_companies',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
    db.Column('company_name', db.String(100), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)

class User(db.Model, UserMixin):
    """User model for authentication and profile data."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    role = db.Column(db.String(20), default=UserRole.USER)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Google OAuth data
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    google_refresh_token = db.Column(db.Text, nullable=True)
    
    # LinkedIn OAuth data (future implementation)
    linkedin_id = db.Column(db.String(100), unique=True, nullable=True)
    
    # Relationships
    applications = db.relationship('Application', backref='user', lazy=True, cascade='all, delete-orphan')
    resume = db.relationship('Resume', backref='user', lazy=True, uselist=False, cascade='all, delete-orphan')
    favorite_companies = db.relationship('Company', 
                                       secondary=user_favorite_companies,
                                       lazy='subquery',
                                       backref=db.backref('favorited_by', lazy=True))
    
    def set_password(self, password):
        """Hash and set the user password."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check if the provided password matches the hash."""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def is_admin(self):
        """Check if the user has admin role."""
        return self.role == UserRole.ADMIN
    
    def __repr__(self):
        return f'<User {self.email}>'

# Company model for favorite companies functionality
class Company(db.Model):
    """Company model for storing company information."""
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    website = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Company {self.name}>'

@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))