import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

# Debug print (remove in production)
print(f"SUPABASE_URL: {SUPABASE_URL}")
print(f"SUPABASE_KEY length: {len(SUPABASE_KEY) if SUPABASE_KEY else 'None'}")

# Create Supabase client
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase client created successfully")
except Exception as e:
    print(f"Error creating Supabase client: {e}")
    raise

# Create admin client with service role key for server-side operations
def get_admin_client():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Helper functions for authentication
def verify_jwt(request_or_token):
    """Verify JWT token from request or token string and return user data"""
    try:
        # Handle both request objects and token strings
        if hasattr(request_or_token, 'headers'):
            # Extract token from Authorization header
            auth_header = request_or_token.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return None
            token = auth_header.split(' ')[1]
        else:
            # Direct token string
            token = request_or_token
            
        if not token:
            return None
        
        # Use admin client to verify the JWT token
        admin_client = get_admin_client()
        response = admin_client.auth.get_user(token)
        return response.user if response else None
    except Exception as e:
        print(f"Error verifying JWT: {e}")
        return None

# Helper functions for database operations
def get_user_profile(user_id):
    """Get user profile from database"""
    try:
        response = supabase.table('profiles').select('*').eq('id', user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error getting user profile: {e}")
        return None

def update_user_profile(user_id, data):
    """Update user profile in database"""
    try:
        response = supabase.table('profiles').update(data).eq('id', user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error updating user profile: {e}")
        return None

def get_interview_results(user_id):
    """Get all interview results for a user"""
    try:
        response = supabase.table('interview_results').select('*').eq('user_id', user_id).execute()
        return response.data
    except Exception as e:
        print(f"Error getting interview results: {e}")
        return []

def save_interview_result(user_id, question, user_answer, feedback, score):
    """Save interview result to database"""
    try:
        data = {
            'user_id': user_id,
            'question': question,
            'user_answer': user_answer,
            'feedback': feedback,
            'score': score
        }
        response = supabase.table('interview_results').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error saving interview result: {e}")
        return None

def get_resume(user_id, resume_id=None):
    """Get resume data for a user"""
    try:
        query = supabase.table('resumes').select('*').eq('user_id', user_id)
        if resume_id:
            query = query.eq('id', resume_id)
        response = query.execute()
        return response.data[0] if resume_id and response.data else response.data
    except Exception as e:
        print(f"Error getting resume: {e}")
        return None

def save_resume(user_id, filename, file_path, extracted_text):
    """Save resume data to database"""
    try:
        data = {
            'user_id': user_id,
            'filename': filename,
            'file_path': file_path,
            'extracted_text': extracted_text
        }
        response = supabase.table('resumes').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error saving resume: {e}")
        return None

def save_resume_analysis(resume_id, user_id, analysis_data):
    """Save resume analysis to database"""
    try:
        # Extract data from analysis_data object
        analysis = analysis_data.get('analysis', {})
        download_links = analysis_data.get('download_links', {})
        
        data = {
            'resume_id': resume_id,
            'user_id': user_id,
            'analysis_text': json.dumps(analysis) if analysis else '{}',
            'suggestions': json.dumps(analysis.get('improvements', [])),
            'pdf_download_link': download_links.get('pdf', ''),
            'docx_download_link': download_links.get('docx', ''),
            'ai_generated_resume': analysis_data.get('ai_generated_resume', ''),
            'score': analysis.get('score', 0),
            'created_at': analysis_data.get('analysis_date')
        }
        response = supabase.table('resume_analysis').insert(data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error saving resume analysis: {e}")
        return None