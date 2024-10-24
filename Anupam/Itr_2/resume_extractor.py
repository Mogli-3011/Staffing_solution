import os
import re
import pdfplumber
import docx
import pandas as pd
import spacy
import streamlit as st

# Load SpaCy NLP model
nlp = spacy.load('en_core_web_sm')

# Updated Regex patterns for contact extraction
phone_pattern = r'(\(\+91\)\s?\d{5}-\d{5})|(\+91-\d{10})|(\+91\s?\d{10})|(\+91\d{10})|(\d{10})|' \
                r'(\+1\s\(\d{3}\)\s\d{3}-\d{4})|(\+1\s\d{3}-\d{3}-\d{4})|(\+1\s\d{3}\s\d{3}-\d{4})|' \
                r'(\+1\s\d{3}\s\d{4})|(\+1-\d{3}-\d{3}-\d{4})|(\d{3}-\d{3}-\d{4})|(\d{3}\s\d{3}-\d{4})|' \
                r'(\+1\s\d{3}\d{7})|(\+1\(\d{3}\)\d{7})|(\+1\(\d{3}\)\s\d{7})|(\+1\(\d{3}\)\s\d{3}-\d{4})|' \
                r'(\+1\(\d{3}\)\s\d{3}\d{4})|(\+1\s\d{3}-\d{3}\d{4})|' \
                r'(\d{3}\s?\d{3}\s?\d{4})|' \
                r'(\d{10},\d{10})'  # New pattern to capture concatenated phone numbers

email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}'

# Function to extract text from PDF
def extract_text_from_pdf(file_path):
    text = ''
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ''  # Handle potential None from extract_text()
    return text

# Function to extract text from Word files
def extract_text_from_word(file_path):
    doc = docx.Document(file_path)
    return '\n'.join([para.text for para in doc.paragraphs])

# Function to extract name from text
def extract_name_from_text(text):
    name = re.split(r'\n|\s+', text.strip())[:2]
    return ' '.join(name)

# Function to extract name from file name
def extract_name_from_filename(file_name):
    name_part = re.sub(r'[_-]', ' ', os.path.splitext(file_name)[0])  # Replace underscores and dashes with space
    name_part = re.sub(r'\W+', ' ', name_part)  # Remove other special characters
    name_part = re.sub(r'\b(resume|cv|curriculum vitae)\b', '', name_part, flags=re.IGNORECASE)  # Remove keywords
    name_part = re.sub(r'\s+', ' ', name_part).strip()  # Remove extra spaces
    return name_part

# Function to extract emails and phone numbers from text
def extract_contact_info(text):
    emails = re.findall(email_pattern, text)
    
    # Extract phone numbers using the updated phone pattern
    phone_matches = re.findall(phone_pattern, text)
    # Flatten the tuples returned by findall
    phones = [match[0] or match[1] or match[2] or match[3] or match[4] or match[5] or match[6] or match[7] or match[8] or match[9] or match[10] or match[11] or match[12] or match[13] for match in phone_matches]
    
    # Handle concatenated phone numbers (e.g., "9570298107,8851649905")
    if ',' in text:
        concatenated_phones = re.findall(r'(\d{10})(,\d{10})+', text)
        for match in concatenated_phones:
            phones.extend(match)
    
    return emails, list(set(phones))  # Return unique phone numbers

# Function to normalize and extract skills
def extract_skills(text, user_skills):
    text = text.lower()
    matched_skills = []

    # Normalize user skills to handle variations
    normalized_skills = {
        'generative ai': ['generative ai', 'gen ai', 'genai', 'generativeai'],
        # Add more skills and their variations here as needed
    }

    for skill in user_skills:
        skill = skill.lower()
        for normalized_skill, variations in normalized_skills.items():
            if skill in variations:
                if any(var in text for var in variations):
                    matched_skills.append(normalized_skill)
                    break
        else:  # If skill is not in normalized_skills, check directly
            if skill in text:
                matched_skills.append(skill)

    return matched_skills

# Function to check for experience
def check_experience(text, experience_required):
    # Updated regex to match various expressions of experience
    experience_pattern = r'(\d+\s*\+?\s*years?\s*of\s*experience?|\d+\s*\+?\s*years?)'
    matches = re.findall(experience_pattern, text, re.IGNORECASE)

    for match in matches:
        # Extract years before plus sign if exists
        years = re.findall(r'\d+', match)  # Find all digits in the match
        if years:
            # If a "+" is present, consider only the first number before it
            total_years = int(years[0]) if '+' not in match else int(years[0]) + 1  # Treat "8+" as "9"
            if total_years >= experience_required:
                return True
            
    return False

# Streamlit UI setup
st.title("Staffing Solution 💼")
st.write("Upload resumes and specify the skills and experience you're looking for.")

# User input for skills
skills_input = st.text_input("Enter skills (comma-separated, can include spaces):")
user_skills = [skill.strip().lower() for skill in skills_input.split(',')] if skills_input else []

# User input for required experience in years
experience_required = st.number_input("Enter required years of experience:", min_value=0, value=3)

# File uploader for resumes
uploaded_files = st.file_uploader("Upload resumes", type=['pdf', 'docx'], accept_multiple_files=True)

# Initialize session state for extracted data
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = []

if uploaded_files:
    extracted_data = []
    for uploaded_file in uploaded_files:
        # Extract text based on file type
        if uploaded_file.name.endswith('.pdf'):
            text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.name.endswith('.docx'):
            text = extract_text_from_word(uploaded_file)

        # Extract information
        name_from_text = extract_name_from_text(text)  # Try to extract name from text
        name_from_file = extract_name_from_filename(uploaded_file.name)  # Extract name from filename

        emails, phones = extract_contact_info(text)
        matched_skills = extract_skills(text, user_skills)
        has_required_experience = check_experience(text, experience_required)

        extracted_data.append({
            'Name from Text': name_from_text,
            'Name from File': name_from_file,
            'Emails': ', '.join(emails),
            'Phone Numbers': ', '.join(phones),
            'Matched Skills': ', '.join(matched_skills),
            'Meets Experience Requirement': 'Yes' if has_required_experience else 'No'
        })

    # Store the extracted data in the session state
    st.session_state.extracted_data = extracted_data

    # Display the extracted data as a DataFrame
    df = pd.DataFrame(st.session_state.extracted_data)
    st.write(df)

    # Option to download the results as a CSV
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name='extracted_contact_info.csv',
        mime='text/csv'
    )