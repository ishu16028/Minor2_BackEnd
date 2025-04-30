import re
import json
import PyPDF2
import docx


def extract_text_from_pdf(pdf_path):
    text = ""
    hyperlinks = []
    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page_num, page in enumerate(reader.pages):
                # Extract text
                text += page.extract_text() + "\n"

                # Extract annotations (which include hyperlinks)
                if "/Annots" in page:
                    annotations = page["/Annots"]
                    if annotations:
                        for annotation in annotations:
                            annotation_object = annotation.get_object()
                            if annotation_object["/Subtype"] == "/Link":
                                if "/A" in annotation_object:
                                    uri = annotation_object["/A"].get("/URI", "")
                                    if uri:
                                        hyperlinks.append(uri)
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        return text

    # Append hyperlinks to text if found
    if hyperlinks:
        text += "\nHyperlinks:\n" + "\n".join(hyperlinks)

    return text


def extract_text_from_docx(docx_path):
    doc = docx.Document(docx_path)
    return "\n".join([para.text for para in doc.paragraphs])


def extract_name(text):
    match = re.search(r"(?i)^([A-Z][a-z]+\s[A-Z][a-z]+)", text)
    return match.group(0) if match else ""


def extract_contact_details(text):
    email = re.search(r"[\w.-]+@[\w.-]+\.[a-zA-Z]{2,4}", text)

    # Clean text to normalize whitespace before searching
    cleaned_text = re.sub(r'\s+', ' ', text)

    # Look for 10 consecutive digits with optional whitespace
    phone = re.search(r"\s\d{10}\b", cleaned_text)

    # If not found, try with word boundaries
    if not phone:
        phone = re.search(r"\b\d{10}\b", text)

    # If still not found, try more complex patterns with country codes and separators
    if not phone:
        phone = re.search(r"\+?\d{1,3}?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b", text)

    return {
        "email": email.group(0) if email else "",
        "phone": phone.group(0).strip() if phone else ""
    }

def extract_social_links(text):
    social_patterns = {
        "LinkedIn": r"https?://(www\.)?linkedin\.com/in/[\w-]+",
        "GitHub": r"https?://(www\.)?github\.com/[\w-]+"
    }

    social_links = {platform: re.search(pattern, text) for platform, pattern in social_patterns.items()}
    return {platform: match.group(0) if match else "" for platform, match in social_links.items()}


def extract_education(text):
        predefined_degrees = [
            "Bachelor of Engineering", "Bachelor of Technology", "Bachelor of Science", "Bachelor of Arts",
            "Bachelor of Commerce", "Master of Engineering", "Master of Technology", "Master of Science",
            "Master of Arts", "Master of Commerce", "PhD in Engineering", "PhD in Technology", "PhD in Science",
            "PhD in Arts", "PhD in Commerce", "Diploma in Engineering", "Diploma in Technology", "Diploma in Science",
            "Diploma in Arts", "Diploma in Commerce", r"B\s*\.?\s*E\s*\.?", r"B\s*\.?\s*Tech\s*\.?", r"B\s*\.?\s*Sc\s*\.?",
            r"B\s*\.?\s*A\s*\.?", r"B\s*\.?\s*Com\s*\.?", r"M\s*\.?\s*E\s*\.?", r"M\s*\.?\s*Tech\s*\.?",
            r"M\s*\.?\s*Sc\s*\.?", r"M\s*\.?\s*A\s*\.?", r"M\s*\.?\s*Com\s*\.?", r"PhD", r"Diploma"
        ]

        ignore_words = ["present", "current", "ongoing", "pursuing", "duration", "year", "semester",
                        "jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec",
                        "january", "february", "march", "april", "june", "july", "august", "september",
                        "october", "november", "december"]

        education_section = re.search(r'(?i)EDUCATION(.*?)(?:SKILLS|PROJECTS|EXPERIENCE|$)', text, re.DOTALL)
        if not education_section:
            return []

        education_text = education_section.group(1).strip()
        result = []

        education_blocks = re.split(r'\n\s*\n', education_text)

        for block in education_blocks:
            lines = block.strip().split('\n')
            institution = None
            degree = None
            cgpa = None

            for line in lines:
                # Clean the line by removing dates and ignore words
                cleaned_line = line
                cleaned_line = re.sub(r'\d{1,2}[/-]\d{2,4}', '', cleaned_line)
                cleaned_line = re.sub(r'\d{2,4}[/-]\d{1,2}', '', cleaned_line)
                cleaned_line = re.sub(r'\d{4}\s*[-–]\s*\d{4}|\d{4}\s*[-–]\s*(Present|Current|Ongoing)', '', cleaned_line)
                cleaned_line = re.sub(r'\b\d{4}\b', '', cleaned_line)

                # Look for institution name
                institution_keywords = ["University", "Institute", "College", "School"]
                for keyword in institution_keywords:
                    if keyword in cleaned_line:
                        if not any(word in cleaned_line.lower() for word in ignore_words):
                            # Find the position of the keyword
                            keyword_pos = cleaned_line.find(keyword)

                            # For embedded keywords, scan backwards until a special character
                            if keyword_pos > 0:
                                # Get text before keyword up to a special character
                                text_before = cleaned_line[:keyword_pos].rstrip()
                                last_special_char_pos = max(
                                    text_before.rfind('\n'),
                                    text_before.rfind('\t'),
                                    text_before.rfind(',')
                                )

                                # If special char found, start from after it, otherwise from beginning
                                start_pos = last_special_char_pos + 1 if last_special_char_pos >= 0 else 0
                                prefix = cleaned_line[start_pos:keyword_pos].strip()

                                # For text after keyword, grab until next special character
                                after_keyword = cleaned_line[keyword_pos + len(keyword):].lstrip()
                                next_special_char_pos = min(
                                    after_keyword.find('\n') if after_keyword.find('\n') >= 0 else len(after_keyword),
                                    after_keyword.find('\t') if after_keyword.find('\t') >= 0 else len(after_keyword),
                                    after_keyword.find(',') if after_keyword.find(',') >= 0 else len(after_keyword)
                                )

                                suffix = after_keyword[:next_special_char_pos].strip()

                                # Combine all parts
                                institution = f"{prefix} {keyword} {suffix}".strip()
                            else:
                                # If keyword is at the beginning, just capture until next special char
                                after_keyword = cleaned_line[len(keyword):].lstrip()
                                next_special_char_pos = min(
                                    after_keyword.find('\n') if after_keyword.find('\n') >= 0 else len(after_keyword),
                                    after_keyword.find('\t') if after_keyword.find('\t') >= 0 else len(after_keyword),
                                    after_keyword.find(',') if after_keyword.find(',') >= 0 else len(after_keyword)
                                )

                                suffix = after_keyword[:next_special_char_pos].strip()
                                institution = f"{keyword} {suffix}".strip()
                            break

                # Look for CGPA
                cgpa_match = re.search(r'(?:CGPA|GPA|Grade)[^\n]*?[:]\s*(\d+\.?\d*)', line, re.IGNORECASE)
                if cgpa_match:
                    cgpa = cgpa_match.group(1).strip()
                else:
                    # Try alternative patterns for CGPA
                    cgpa_match = re.search(r'(?:CGPA|GPA|Grade)[^\n]*?[\s:]\s*(\d+\.?\d*)/\d+', line, re.IGNORECASE)
                    if cgpa_match:
                        cgpa = cgpa_match.group(1).strip()

                # Look for course/degree
                course_match = re.search(r'(?:Course|Degree|Program|Major)\s*[:]\s*([^:\n]+)', line, re.IGNORECASE)
                if course_match:
                    degree = course_match.group(1).strip()

                # Check for predefined degrees in the line
                if not degree:
                    for deg in predefined_degrees:
                        if isinstance(deg, str) and re.search(rf'\b{re.escape(deg)}\b', line, re.IGNORECASE):
                            degree = deg
                            break
                        elif not isinstance(deg, str) and re.search(deg, line, re.IGNORECASE):
                            degree = re.search(deg, line, re.IGNORECASE).group(0)
                            break

            if institution or degree or cgpa:
                result.append({
                    "degree": degree if degree else "Degree not specified",
                    "institution": institution if institution else "",
                    "cgpa": cgpa if cgpa else ""
                })

        return result
def extract_skills(text):
    predefined_skills = [
        "Python", "Java", "C++", "JavaScript", "SQL", "HTML", "CSS", "React", "Node.js", "Django",
        "Flask", "Ruby on Rails", "Angular", "Vue.js", "Git", "Docker", "Kubernetes", "AWS", "Azure",
        "GCP", "Machine Learning", "Deep Learning", "Data Science", "Pandas", "NumPy", "TensorFlow",
        "Keras", "PyTorch", "Natural Language Processing", "Computer Vision", "Agile", "Scrum",
        "C#", "PHP", "Swift", "Objective-C", "R", "MATLAB", "Scala", "Perl", "Go", "Rust", "Hadoop",
        "Spark", "Tableau", "Power BI", "Excel", "Linux", "Unix", "Shell Scripting", "Jenkins",
        "CI/CD", "Terraform", "Ansible", "Chef", "Puppet", "Salesforce", "SAP", "Oracle", "SQL Server",
        "MongoDB", "PostgreSQL", "SQLite", "Firebase", "Redis", "Elasticsearch", "GraphQL", "REST API",
        "SOAP", "Microservices", "Blockchain", "IoT", "Cybersecurity", "Penetration Testing", "DevOps",
        "Big Data", "Data Analytics", "Business Intelligence", "Project Management", "JIRA", "Confluence"
    ]

    skills_section = re.search(r"(?i)Skills\n(.*?)(?:\n\n|$)", text, re.DOTALL)
    if not skills_section:
        return []

    skills_text = skills_section.group(1).strip()
    skills_text = re.sub(r'\s+', ' ', skills_text)

    matched_skills = [skill for skill in predefined_skills if
                      re.search(rf'\b{re.escape(skill)}\b', skills_text, re.IGNORECASE)]
    return matched_skills


def extract_achievements(text):
    # Look for achievements section with multiple possible section headers that could follow it
    achievements_section = re.search(
        r'(?i)ACHIEVEMENT[S]?.*?\n+(.*?)(?:EDUCATION|SKILLS|PROJECTS|EXPERIENCE|CONTACT|SOCIAL|LANGUAGES|\Z)',
        text,
        re.DOTALL
    )

    if not achievements_section:
        print("Achievements section not found.")
        return []

    achievements_text = achievements_section.group(1).strip()

    # Split text into lines and handle different bullet point styles
    lines = achievements_text.split('\n')
    achievements = []

    for line in lines:
        # Remove bullet points, numbers, and other markers at the start
        clean_line = re.sub(r'^[\s•●★\-\*\d\.\)\→\>\✓\✔]+\s*', '', line.strip())

        # Skip empty lines and common section markers
        if (clean_line and
            not any(header.lower() in clean_line.lower()
                   for header in ['education', 'skills', 'projects', 'experience'])):
            achievements.append(clean_line)

    return [ach for ach in achievements if ach]  # Remove any empty strings
def extract_projects(text):
    projects_section = re.search(r'(?i)PROJECTS(.*?)(?:EDUCATION|SKILLS|EXPERIENCE|ACHIEVEMENTS|$)', text, re.DOTALL)

    if not projects_section:
        return []

    projects_text = projects_section.group(1).strip() if projects_section.group(1) else ""

    projects_text = re.sub(r'\s+', ' ', projects_text)
    projects_text = re.sub(r'\s*\n\s*', '\n', projects_text)

    project_entries = re.findall(r'([A-Za-z0-9\s&.()/-]+?)[:•](.*?)(?=\n[A-Za-z0-9][A-Za-z0-9\s&.()/-]+?[:•]|\Z)',
                                 '\n' + projects_text, re.DOTALL)

    if not project_entries:
        project_entries = re.findall(
            r'([A-Za-z0-9\s&.()/-]+?)(?:\n|\s{2,})(.*?)(?=\n[A-Za-z0-9][A-Za-z0-9\s&.()/-]+?(?:\n|\s{2,})|\Z)',
            '\n' + projects_text, re.DOTALL)

    result = []
    for name, desc in project_entries:
        name = name.strip()
        desc = desc.strip()

        tech_stack = ""
        tech_match = re.search(r'\(([^)]+)\)|\busing\s+([^.]+)|\bwith\s+([^.]+)|\btechnologies:?\s+([^.]+)', desc,
                               re.IGNORECASE)
        if tech_match:
            for group in tech_match.groups():
                if group:
                    tech_stack = group.strip()
                    break

        result.append({
            "name": name,
            "description": desc.replace('\n', ' '),
            "tech_stack": tech_stack
        })

    return result

def extract_soft_skills(text):
    # List of common soft skills to identify
    predefined_soft_skills = [
        "Communication", "Leadership", "Teamwork", "Problem Solving", "Time Management",
        "Adaptability", "Critical Thinking", "Creativity", "Emotional Intelligence",
        "Conflict Resolution", "Decision Making", "Organization", "Flexibility",
        "Patience", "Empathy", "Negotiation", "Persuasion", "Collaboration",
        "Interpersonal Skills", "Public Speaking", "Presentation Skills", "Active Listening",
        "Work Ethic", "Attention to Detail", "Customer Service", "Project Management",
        "Strategic Planning", "Analytical Skills", "Mentoring", "Coaching"
    ]

    # Various section headers that might indicate soft skills
    section_headers = [
        r"Soft Skills", r"People Skills", r"Professional Skills", r"Interpersonal Skills",
        r"Core Competencies", r"Personal Skills", r"Key Skills", r"Transferable Skills",
        r"Personal Attributes", r"Professional Attributes"
    ]

    # Create regex pattern for section headers
    section_pattern = '|'.join(section_headers)

    # Try to find a soft skills section
    soft_skills_section = re.search(
        rf"(?i)({section_pattern}).*?\n+(.*?)(?:\n\n|\n(?:Technical|Hard|Programming|Language|Tool|Framework|Platform|Education|Experience|Project|Achievement|Contact|Reference)s?|\Z)",
        text,
        re.DOTALL
    )

    matched_soft_skills = []

    if soft_skills_section:
        soft_skills_text = soft_skills_section.group(2).strip()

        # Extract skills from the section
        lines = soft_skills_text.split('\n')
        for line in lines:
            # Remove bullet points and other markers
            clean_line = re.sub(r'^[\s•●★\-\*\d\.\)\→\>\✓\✔]+\s*', '', line.strip())

            if clean_line:
                # Look for predefined soft skills
                for skill in predefined_soft_skills:
                    if re.search(rf'\b{re.escape(skill)}\b', clean_line, re.IGNORECASE):
                        matched_soft_skills.append(skill)

                # Also add anything separated by commas as potential soft skills
                comma_separated = re.split(r'\s*,\s*|\s+and\s+|\s*[/|]\s*', clean_line)
                for item in comma_separated:
                    if item.strip() and len(item.strip()) > 3:  # Avoid very short terms
                        matched_soft_skills.append(item.strip())

    # If no dedicated section found, scan the entire resume for soft skills
    if not matched_soft_skills:
        for skill in predefined_soft_skills:
            if re.search(rf'\b{re.escape(skill)}\b', text, re.IGNORECASE):
                matched_soft_skills.append(skill)

    # Remove duplicates and format consistently
    return list(set(skill.title() for skill in matched_soft_skills))

def parse_resume(file_path):
    # Normalize file path
    file_path = file_path.strip().replace('\\', '/')

    # Check file extension and extract text accordingly
    if file_path.lower().endswith('.pdf'):
        text = extract_text_from_pdf(file_path)
    elif file_path.lower().endswith('.docx'):
        text = extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file format. Please provide a PDF or DOCX file.")

    if not text:
        raise ValueError("Failed to extract text from the file.")

    parsed_data = {
        "name": extract_name(text),
        "contact_details": extract_contact_details(text),
        "social_links": extract_social_links(text),
        "education": extract_education(text),
        "skills": extract_skills(text),
        "soft_skills": extract_soft_skills(text),  # Add this line
        "projects": extract_projects(text),
        "achievements": extract_achievements(text)
    }

    return json.dumps(parsed_data, indent=4)


print(parse_resume(r"C:\Users\ishuj\Desktop\Ishu\Ishuresume.docx"))