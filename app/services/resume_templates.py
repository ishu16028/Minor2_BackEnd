# app/services/resume_templates.py

import os
from flask import current_app, send_file, abort
import uuid

def get_available_templates():
    """Return a list of available resume templates"""
    template_dir = os.path.join(current_app.static_folder, 'resume_templates')
    if not os.path.exists(template_dir):
        return []

    templates = []
    for filename in os.listdir(template_dir):
        if filename.endswith(('.docx', '.pdf')):
            file_path = os.path.join('resume_templates', filename)
            name = os.path.splitext(filename)[0].replace('_', ' ').title()
            templates.append({
                'id': filename,
                'name': name,
                'file_path': file_path,
                'type': os.path.splitext(filename)[1][1:].upper()
            })

    return templates

def get_template(template_id):
    """Return the file path for a specific template"""
    template_dir = os.path.join(current_app.static_folder, 'resume_templates')
    template_path = os.path.join(template_dir, template_id)

    if not os.path.exists(template_path):
        return None

    return template_path

def add_template(file, name=None):
    """Add a new resume template"""
    if not file or not file.filename:
        return False, "No file provided"

    if not file.filename.endswith(('.docx', '.pdf')):
        return False, "Only .docx and .pdf files are supported"

    # Generate template name from filename if not provided
    if not name:
        name = os.path.splitext(file.filename)[0]

    # Sanitize name for filename
    safe_name = name.lower().replace(' ', '_')
    extension = os.path.splitext(file.filename)[1]
    filename = f"{safe_name}{extension}"

    template_dir = os.path.join(current_app.static_folder, 'resume_templates')

    # Create directory if it doesn't exist
    if not os.path.exists(template_dir):
        os.makedirs(template_dir)

    # If file with same name exists, create unique name
    if os.path.exists(os.path.join(template_dir, filename)):
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{safe_name}_{unique_id}{extension}"

    file_path = os.path.join(template_dir, filename)
    file.save(file_path)

    return True, filename

def delete_template(template_id):
    """Delete a resume template"""
    template_dir = os.path.join(current_app.static_folder, 'resume_templates')
    template_path = os.path.join(template_dir, template_id)

    if not os.path.exists(template_path):
        return False, "Template not found"

    try:
        os.remove(template_path)
        return True, "Template deleted successfully"
    except Exception as e:
        return False, f"Error deleting template: {str(e)}"