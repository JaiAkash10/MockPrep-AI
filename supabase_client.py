import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

import datetime # Added for timestamping

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

def get_interview_results_for_question(user_id: str, question_text: str) -> list:
    """Fetches all interview results for a specific question by a user, ordered by creation date."""
    try:
        admin_client = get_admin_client()
        response = admin_client.table('interview_results') \
                                     .select('*') \
                                     .eq('user_id', user_id) \
                                     .eq('question', question_text) \
                                     .order('created_at', desc=True) \
                                     .execute()

        if response.data:
            return response.data
        if hasattr(response, 'error') and response.error:
            print(f"Error fetching interview results for user {user_id}, question '{question_text}': {response.error}")
            return []
        return [] # No data and no specific error object (or caught by general exception)

    except Exception as e:
        print(f"Exception fetching interview results for user {user_id}, question '{question_text}': {e}")
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

def save_full_interview_analysis(user_id: str, video_id: str, question_text: str, twelvelabs_data: dict, gemini_analysis: str):
    """Saves the complete interview analysis to Supabase."""
    try:
        data_to_insert = {
            'user_id': user_id,
            'video_id': video_id,
            'question': question_text,
            'twelvelabs_analysis': twelvelabs_data, # Should be JSON serializable
            'gemini_analysis': gemini_analysis
            # 'created_at' will be handled by the database default (now())
        }

        admin_client = get_admin_client()
        # Supabase insert expects a list of dictionaries
        response = admin_client.table('interview_results').insert([data_to_insert]).execute()

        if response.data:
            return response.data[0]
        # Check for Supabase specific error object if data is empty
        if hasattr(response, 'error') and response.error:
            print(f"Error saving full interview analysis to Supabase: {response.error}")
            return None
        # If no data and no explicit error object, implies an issue or empty return not caught as error by client
        print(f"No data returned and no explicit error object for Supabase insert. User: {user_id}, Video: {video_id}")
        return None

    except Exception as e:
        print(f"Exception saving full interview analysis for user {user_id}, video {video_id}: {e}")
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

# --- New Resume Handling Functions ---

def save_resume_metadata(user_id: str, filename: str, file_path: str, job_description: str, client_resume_id: str) -> dict or None:
    """Saves resume metadata to Supabase `resumes` table."""
    try:
        admin_client = get_admin_client()
        data_to_insert = {
            'user_id': user_id,
            'client_resume_id': client_resume_id,
            'filename': filename,
            'file_path': file_path,
            'job_description': job_description,
            'upload_date': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'analyzed': False
        }
        response = admin_client.table('resumes').insert([data_to_insert]).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error saving resume metadata for user {user_id}: {e}")
        return None

def get_resume_metadata_by_id(resume_supa_id: str, user_id: str) -> dict or None:
    """Fetches resume metadata by its Supabase ID, ensuring user owns it."""
    try:
        admin_client = get_admin_client()
        response = admin_client.table('resumes').select('*').eq('id', resume_supa_id).eq('user_id', user_id).maybe_single().execute()
        return response.data if response.data else None
    except Exception as e:
        print(f"Error fetching resume metadata by id {resume_supa_id} for user {user_id}: {e}")
        return None

def get_resume_metadata_by_client_id(client_resume_id: str, user_id: str) -> dict or None:
    """Fetches resume metadata by its client-generated ID, ensuring user owns it."""
    try:
        admin_client = get_admin_client()
        response = admin_client.table('resumes').select('*').eq('client_resume_id', client_resume_id).eq('user_id', user_id).maybe_single().execute()
        return response.data if response.data else None
    except Exception as e:
        print(f"Error fetching resume metadata by client_id {client_resume_id} for user {user_id}: {e}")
        return None


def save_resume_analysis_data(resume_supa_id: str, user_id: str, analysis_json: dict, ai_generated_resume_text: str) -> dict or None:
    """Saves resume analysis data to `resume_analysis` table."""
    try:
        admin_client = get_admin_client()
        data_to_insert = {
            'resume_id': resume_supa_id, # This is the Supabase PK of the resume record
            'user_id': user_id,
            'analysis_data': analysis_json,
            'ai_generated_resume': ai_generated_resume_text,
            'analysis_date': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        response = admin_client.table('resume_analysis').insert([data_to_insert]).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error saving resume analysis data for resume_id {resume_supa_id}, user {user_id}: {e}")
        return None

def update_resume_with_analysis_info(resume_supa_id: str, analysis_supa_id: str, user_id: str):
    """Updates the resume record to mark as analyzed and link to analysis entry."""
    try:
        admin_client = get_admin_client()
        update_data = {'analyzed': True, 'analysis_id': analysis_supa_id} # analysis_id is FK to resume_analysis table
        response = admin_client.table('resumes').update(update_data).eq('id', resume_supa_id).eq('user_id', user_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error updating resume with analysis info for resume {resume_supa_id}, user {user_id}: {e}")
        return None

def get_resume_analysis_by_resume_id(resume_supa_id: str, user_id: str) -> dict or None:
    """Fetches resume analysis data by resume_id (Supabase PK of the resume), ensuring user owns it."""
    try:
        admin_client = get_admin_client()
        # Assuming resume_analysis table has a 'resume_id' column that is a FK to resumes.id
        response = admin_client.table('resume_analysis').select('*').eq('resume_id', resume_supa_id).eq('user_id', user_id).maybe_single().execute()
        return response.data if response.data else None
    except Exception as e:
        print(f"Error fetching resume analysis by resume_id {resume_supa_id} for user {user_id}: {e}")
        return None

def add_resume_chat_message(resume_supa_id: str, user_id: str, user_message: str, ai_response: str) -> dict or None:
    """Adds a chat message to the resume's chat_history."""
    try:
        admin_client = get_admin_client()
        # Fetch current chat history
        resume_record_response = admin_client.table('resumes').select('chat_history').eq('id', resume_supa_id).eq('user_id', user_id).maybe_single().execute()

        if not resume_record_response.data:
            print(f"Resume not found for chat: resume_id {resume_supa_id}, user_id {user_id}")
            return None

        chat_history = resume_record_response.data.get('chat_history') # Returns None if not present
        if chat_history is None: # Handle case where chat_history might be null in DB
            chat_history = []

        chat_history.append({
            'user': user_message,
            'ai': ai_response,
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
        })

        update_response = admin_client.table('resumes').update({'chat_history': chat_history}).eq('id', resume_supa_id).eq('user_id', user_id).execute()
        return update_response.data[0] if update_response.data else None
    except Exception as e:
        print(f"Error adding resume chat message for resume {resume_supa_id}, user {user_id}: {e}")
        return None

# Functions for user interview progress

def get_user_interview_progress(user_id: str) -> dict:
    """Fetches user's interview progress (asked questions, current question)."""
    try:
        admin_client = get_admin_client()
        response = admin_client.table('user_interview_progress').select('asked_questions, current_question').eq('user_id', user_id).maybe_single().execute()
        if response.data:
            return response.data
        return {'asked_questions': [], 'current_question': None} # Default if no record
    except Exception as e:
        print(f"Error getting user interview progress for {user_id}: {e}")
        return {'asked_questions': [], 'current_question': None} # Fallback

def update_user_interview_progress(user_id: str, asked_questions: list, current_question: str):
    """Updates or creates user's interview progress."""
    try:
        admin_client = get_admin_client()
        data_to_upsert = {
            'user_id': user_id,
            'asked_questions': asked_questions,
            'current_question': current_question,
            'updated_at': 'now()' # Let Supabase handle the timestamp
        }
        # Ensure data is a list of dicts for upsert
        response = admin_client.table('user_interview_progress').upsert([data_to_upsert], on_conflict='user_id').execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error updating user interview progress for {user_id}: {e}")
        return None

def reset_user_interview_progress(user_id: str):
    """Resets user's interview progress to initial state."""
    try:
        admin_client = get_admin_client()
        data_to_upsert = {
            'user_id': user_id,
            'asked_questions': [],
            'current_question': None,
            'updated_at': 'now()'
        }
        # Ensure data is a list of dicts for upsert
        response = admin_client.table('user_interview_progress').upsert([data_to_upsert], on_conflict='user_id').execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error resetting user interview progress for {user_id}: {e}")
        return None