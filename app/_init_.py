from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from .config import config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
bcrypt = Bcrypt()
jwt = JWTManager()

def create_app(config_name='development'):
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])
    
    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(app)
    
    # Setup login configuration
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.jobs import jobs_bp
    from .routes.tracker import tracker_bp
    from .routes.favorites import favorites_bp
    from .routes.resume import resume_bp
    from .routes.email import email_bp
    from .routes.admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(tracker_bp)
    app.register_blueprint(favorites_bp)
    app.register_blueprint(resume_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(admin_bp)
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
    
    return app