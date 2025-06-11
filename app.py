import os
import json
import random
import requests
import datetime
from urllib.parse import unquote
from flask import Flask, request, jsonify, session # session might be removed later if not used elsewhere
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, get_current_user, verify_jwt_in_request
from dotenv import load_dotenv
from twelvelabs import TwelveLabs
from twelvelabs.models.task import Task
# from pymongo import MongoClient # Commented out for Supabase migration
# from werkzeug.security import generate_password_hash, check_password_hash # Removed, auth handled by Supabase
from bson.objectid import ObjectId # Kept for client_resume_id generation
import google.generativeai as genai
import speech_recognition as sr
from moviepy.editor import VideoFileClip
from datetime import timedelta
# from flask_login import LoginManager, UserMixin # Removed Flask-Login

# Import Supabase functions
from supabase_client import (
    get_admin_client,
    get_user_profile as supabase_get_user_profile,
    update_user_profile as supabase_update_user_profile,
    get_user_interview_progress,
    update_user_interview_progress,
    reset_user_interview_progress,
    save_full_interview_analysis,
    get_interview_results_for_question,
    # Resume handling functions
    save_resume_metadata,
    get_resume_metadata_by_client_id,
    save_resume_analysis_data,
    update_resume_with_analysis_info,
    get_resume_analysis_by_resume_id,
    add_resume_chat_message
)
from datetime import timezone # Added for datetime.now(timezone.utc)


load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
# Configure CORS to allow requests from React frontend
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:5173", "http://127.0.0.1:5173"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)
jwt = JWTManager(app)

# MongoDB setup - Commented out as major parts are migrated to Supabase
# mongo_uri = os.getenv("MONGO_URI")
# client = MongoClient(mongo_uri)
# db = client["ai-interview-analyzer"]
# # users_collection = db["users"] # Removed MongoDB users collection
# # results_collection = db["results"] # Removed, migrated to Supabase interview_results table

API_URL = os.getenv('API_URL')

# Gemini AI setup
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.0-flash')  # Initialize Gemini model

print("Environment Variables:")
print(f"API_URL exists: {'API_URL' in os.environ}")

# Removed Flask-Login setup
# login_manager = LoginManager()
# login_manager.init_app(app)
# login_manager.login_view = 'login'

# @login_manager.user_loader
# def load_user(user_id):
#     # Load your user from the database based on user_id
#     # Return None if the user doesn't exist
#     user = users_collection.find_one({'_id': ObjectId(user_id)})
#     if user:
#         return User(user)
#     return None

# class User(UserMixin):
#     def __init__(self, user_data):
#         self.id = str(user_data['_id'])
#         self.email = user_data['email']

#     def is_authenticated(self):
#         return True

#     def is_active(self):
#         return True

#     def is_anonymous(self):
#         return False

#     def get_id(self):
#         return self.id

# Supabase JWT Configuration with flask_jwt_extended
@jwt.user_identity_loader
def user_identity_lookup(decoded_jwt):
    # The 'sub' claim in a Supabase JWT is the user's ID
    return decoded_jwt["sub"]

@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]
    # This callback needs to return the "user object" that get_current_user() will return.
    # We'll validate the token with Supabase and return the Supabase user object.

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        # This case should ideally be caught by verify_jwt_in_request() or @jwt_required
        return None
    token = auth_header.split(' ')[1]

    try:
        admin_client = get_admin_client()
        # This validates the token with Supabase and returns the user object
        user = admin_client.auth.get_user(token).user
        if user:
            return user # flask_jwt_extended will pass this to get_current_user()
    except Exception as e:
        print(f"Error during token validation in user_lookup_callback: {e}")
        return None
    return None


INTERVIEW_QUESTIONS = [
    "Tell me about yourself.",
    "What are your greatest strengths",
    "What do you consider to be your weaknesses",
    "Where do you see yourself in five years",
    "Why should we hire you",
    "What motivates you",
    "What are your career goals",
    "How do you work in a team",
    "What's your leadership style"
]

def check_api_connection(api_key):
    try:
        api_url = "https://api.twelvelabs.io/v1.3/tasks"
        response = requests.get(
            api_url,
            headers={
                "x-api-key": api_key,
                "Accept": "application/json"
            },
            timeout=10  # Set timeout to 10 seconds
        )
        
        if response.status_code == 200:
            return True, None
        elif response.status_code in [401, 403]:
            return False, "Invalid API key"
        else:
            return False, f"API key check failed with status code: {response.status_code}"
            
    except requests.Timeout:
        return False, "API connection timed out. Please try again."
    except requests.ConnectionError:
        return False, "Could not connect to API. Please check your internet connection."
    except requests.RequestException as e:
        return False, f"API connection check failed: {str(e)}"


def get_transcript(video_file_path):
    recognizer = sr.Recognizer()
    audio_path = "temp_audio.wav"
    
    try:
        # Use 'with' to ensure the video file is closed after use
        with VideoFileClip(video_file_path) as video:
            video.audio.write_audiofile(audio_path, codec='pcm_s16le')

        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)

        transcript = recognizer.recognize_google(audio)
        return transcript

    except Exception as e:
        print(f"Error extracting transcript: {e}")
        return ""

    finally:
        # Clean up the audio file regardless of success or failure
        if os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except Exception as cleanup_error:
                print(f"Error cleaning up audio file: {cleanup_error}")

def process_api_response(data):
    processed_data = {
        "confidence": 0,
        "clarity": 0,
        "speech_rate": 0,
        "eye_contact": 0,
        "body_language": 0,
        "voice_tone": 0,
        "imp_points": []
    }
    
    try:
        if isinstance(data, str):

            try:
                import re
                json_match = re.search(r'\{[\s\S]*\}', data)
                if json_match:
                    data = json.loads(json_match.group())
                else:
                    data = json.loads(data)
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                print(f"Raw data: {data}")
                return processed_data
        
        if isinstance(data, dict):
            for key in processed_data.keys():
                if key in data:
                    if isinstance(data[key], (int, float)):
                        processed_data[key] = data[key]
                    elif isinstance(data[key], str) and data[key].replace('.', '').isdigit():
                        processed_data[key] = float(data[key])
                    elif key == 'imp_points' and isinstance(data[key], list):
                        processed_data[key] = data[key]
                        
    except Exception as e:
        print(f"Error processing response: {e}")
        print(f"Raw data: {data}")
    
    return processed_data

@app.route('/api/auth/login', methods=['POST'])
def login():
    # Client should have already logged in with Supabase and obtained a JWT.
    # This endpoint validates that JWT. @jwt_required() could also be used if preferred.
    # For now, it attempts to verify and returns user info.
    try:
        # verify_jwt_in_request() will raise an error if token is invalid/missing
        # This is useful if the route isn't protected by @jwt_required but needs a token.
        # However, for a login route, the client sends its token for the *first time* to this backend
        # for this backend to "acknowledge" it.
        # The user_lookup_loader will be triggered if a token is present.

        # A more explicit way for a login endpoint:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header missing or invalid'}), 401
        token = auth_header.split(' ')[1]

        admin_client = get_admin_client()
        current_user_supabase = admin_client.auth.get_user(token).user

        if not current_user_supabase:
            return jsonify({'error': 'User not found or token invalid via Supabase'}), 401

        # Optionally, fetch profile details from 'profiles' table if needed immediately at login
        user_profile_details = supabase_get_user_profile(current_user_supabase.id)

        user_response = {
            'id': current_user_supabase.id,
            'email': current_user_supabase.email,
            'aud': current_user_supabase.aud,
        }
        if user_profile_details:
            user_response['role'] = user_profile_details.get('role', 'user')
            user_response['api_key'] = user_profile_details.get('api_key')
            user_response['index_id'] = user_profile_details.get('index_id')
            # Add any other fields from your 'profiles' table that the client needs at login

        # We don't issue a new token here. Client already has the Supabase token.
        return jsonify({
            'message': 'User authenticated successfully via Supabase JWT.',
            'user': user_response
        })
    except Exception as e:
        # Log the exception e for debugging
        print(f"Login endpoint error: {e}")
        # Check if it's a Supabase specific auth error if possible, otherwise generic
        if "Invalid JWT" in str(e) or "User not found" in str(e): # Basic check
             return jsonify({'error': 'Invalid or expired Supabase token'}), 401
        return jsonify({'error': 'Server error during login validation'}), 500

@app.route('/api/auth/validate', methods=['GET'])
@jwt_required() # This decorator now uses our Supabase configured loaders
def validate_token():
    # get_current_user() returns the Supabase user object from user_lookup_callback
    current_user_supabase = get_current_user()
    if not current_user_supabase:
        # This case should ideally not be reached if @jwt_required and user_lookup_callback work correctly
        return jsonify({'valid': False, 'error': 'User not found from token'}), 401

    # Fetch additional profile details from 'profiles' table in Supabase.
    user_profile_details = supabase_get_user_profile(current_user_supabase.id)

    user_response = {
        'id': current_user_supabase.id,
        'email': current_user_supabase.email,
        'aud': current_user_supabase.aud, # Audience from token
    }

    if user_profile_details:
        user_response['role'] = user_profile_details.get('role', 'user')
        user_response['api_key'] = user_profile_details.get('api_key')
        user_response['index_id'] = user_profile_details.get('index_id')
        # Add other fields from Supabase user object or profile table as needed
        return jsonify({'valid': True, 'user': user_response})
    else:
        # This case means the user exists in Supabase auth but not in our 'profiles' table,
        # or supabase_get_user_profile returned None.
        # The token is valid, but full application profile might be missing.
        return jsonify({
            'valid': True,
            'user': user_response, # Return basic info from token
            'message': 'User authenticated, but app-specific profile details could not be fetched.'
        }), 200 # Or 404 if profile is strictly required for the app to function


def check_index_id(api_key, index_id):
    try:
        api_url = f"https://api.twelvelabs.io/v1.3/indexes/{index_id}"
        response = requests.get(api_url, headers={
            "x-api-key": api_key,
            "Accept": "application/json"
        })
        if response.status_code != 200:
            return False, f"Index ID check failed with status code: {response.status_code}"
        return True, None
    except requests.RequestException as e:
        return False, f"Index ID connection check failed. Detailed error: {str(e)}"

@app.route('/api/auth/register', methods=['POST'])
def register():
    # Registration is handled by the client-side application using Supabase.
    # This endpoint no longer handles user creation or password hashing.
    # Optionally, you could take the Supabase user ID and API key/Index ID here
    # to create a profile in your 'profiles' table if it's not done by a trigger in Supabase.
    # For now, just a message.
    return jsonify({'message': 'Registration is handled by the client application using Supabase.'}), 200


@app.route('/api/questions/next', methods=['GET'])
@jwt_required()
def get_question():
    user_id = get_jwt_identity()
    progress = get_user_interview_progress(user_id) # Fetches from Supabase

    # Ensure progress is a dict, even if get_user_interview_progress has fallbacks, good practice here.
    if not isinstance(progress, dict):
        # Log this unexpected situation
        print(f"Error: get_user_interview_progress for user {user_id} did not return a dict: {progress}")
        return jsonify({"error": "Failed to retrieve interview progress."}), 500

    asked_questions = progress.get('asked_questions', [])

    available_questions = [q for q in INTERVIEW_QUESTIONS if q not in asked_questions]

    if not available_questions:
        # Check if all questions from the master list have been asked
        if len(asked_questions) >= len(INTERVIEW_QUESTIONS):
            return jsonify({"message": "All questions have been asked. You can reset if you wish to start over."}), 200
        else:
            # This might happen if INTERVIEW_QUESTIONS is empty or some other edge case
            return jsonify({"message": "No new questions available at the moment."}), 200

    question = random.choice(available_questions)
    
    new_asked_list = list(asked_questions) # Make a copy
    new_asked_list.append(question)

    # Update Supabase with new list of asked questions and the current selected question
    update_result = update_user_interview_progress(user_id, new_asked_list, question)
    if not update_result:
        # Log this error
        print(f"Error: update_user_interview_progress failed for user {user_id}")
        return jsonify({"error": "Failed to update interview progress."}), 500
    
    return jsonify({"question": question})


@app.route('/api/upload', methods=['POST'])
@jwt_required()
def upload():
    user_id = get_jwt_identity() # Supabase user ID
    current_user_supa = get_current_user() # Supabase user object

    user_profile = supabase_get_user_profile(user_id)
    if not user_profile:
        return jsonify({'error': 'User profile not found in Supabase'}), 404

    api_key = user_profile.get('api_key')
    index_id = user_profile.get('index_id')
    current_user_email = current_user_supa.email # Email from Supabase token/user object

    if not api_key or not index_id:
        return jsonify({'error': 'API key or Index ID not configured in user profile'}), 400

    if not current_user_email: # Should not happen if user is authenticated
        return jsonify({'error': 'User email not found.'}), 401

    if not check_api_connection(api_key):
        return jsonify({"error": "Failed to connect to the Twelve Labs API."}), 500
    if 'video' not in request.files:
        return jsonify({"error": "No video file provided"}), 400
    video = request.files['video']
    if video.filename == '':
        return jsonify({"error": "No video file selected"}), 400

    video_path = os.path.join('uploads', 'interview.mp4')
    video.save(video_path)

    file_size = os.path.getsize(video_path)
    if file_size > 2 * 1024 * 1024 * 1024:
        return jsonify({"error": "Video file size exceeds 2GB limit"}), 400

    try:
        client = TwelveLabs(api_key=api_key)
        task = client.task.create(
            index_id=index_id,
            file=video_path
        )

        def on_task_update(task: Task):
            print(f"Task Status={task.status}")

        task.wait_for_done(sleep_interval=5, callback=on_task_update)

        if task.status != "ready":
            raise RuntimeError(f"Indexing failed with status {task.status}")

        print("Task completed successfully. Video ID:", task.video_id)

        prompt = """You're an Interviewer, Analyze the video clip of the interview answer.
        Rules for scoring:
        - If **no face is detected**, give **less than 5** for all categories.
        - If **no voice is detected**, set `"clarity"`, `"speech_rate"`, `"voice_tone"` to **1** and add `"No speech detected"` to `"imp_points"`.
        - If **both face and voice are missing**, return the following JSON:
        ```json
        {
            "error": "No valid face or speech detected in the video."
        }

        Otherwise provide the response in the following JSON format with numerical values from 1-10:
        {
            "confidence": <number>,
            "clarity": <number>,
            "speech_rate": <number>,
            "eye_contact": <number>,
            "body_language": <number>,
            "voice_tone": <number>,
            "imp_points": [<list of important points as strings>]
        }"""

        result = client.generate.text(
            video_id=task.video_id,
            prompt=prompt
        )

        print("Raw API Response:", result.data)
        processed_data = process_api_response(result.data)

        # Fetch current_question from Supabase user_interview_progress table
        progress = get_user_interview_progress(user_id)
        question_text = progress.get('current_question')

        if not question_text:
            return jsonify({"error": "Could not determine the current question for this interview. Please ensure a question is selected first via /api/questions/next."}), 400

        print(f"Processed data: {processed_data}")

        transcript = get_transcript(video_path)
        gemini_analysis = analyze_with_gemini(question_text, transcript) # Use question_text

        # Storing results in Supabase
        supabase_save_result = save_full_interview_analysis(
            user_id=user_id,
            video_id=task.video_id, # Assuming 'task' is from TwelveLabs
            question_text=question_text, # Question from Supabase progress
            twelvelabs_data=processed_data,
            gemini_analysis=gemini_analysis
        )

        if not supabase_save_result:
            # Log error or return a specific message if saving to Supabase failed
            print(f"Warning: Failed to save interview analysis to Supabase for user {user_id}, video {task.video_id}")
            # Optionally, you could return an error to the client:
            # return jsonify({"error": "Failed to save analysis results"}), 500

        return jsonify({
            "twelvelabs_data": processed_data,
            "gemini_analysis": gemini_analysis
        }), 200

    except Exception as e:
        print(f"Error processing video: {str(e)}")
        return jsonify({"error": f"Error processing video: {str(e)}"}), 500

    finally:
        if os.path.exists(video_path):
            os.remove(video_path)

def analyze_with_gemini(question, transcript):
    
    prompt = f"""
    You are a professional career coach providing constructive feedback on interview performance.

    Your task is to analyze the following response to an interview question. 
    Provide the analysis in markdown format, adhering strictly to the following structure:

    Analysis:\n

    Evaluation: [A brief, human-written evaluation of the response, highlighting strengths and areas for improvement. Use a positive and encouraging tone.]\n

    Constructive Criticism:
    * [Point 1: Specific, actionable criticism in bullet-point format. Use a positive and encouraging tone. Add a line break after the point.]\n
    * [Point 2: Specific, actionable criticism in bullet-point format. Use a positive and encouraging tone. Add a line break after the point.]\n
    * [Point 3: Specific, actionable criticism in bullet-point format. Use a positive and encouraging tone. Add a line break after the point.]\n
    * [Point 4: Specific, actionable criticism in bullet-point format. Use a positive and encouraging tone. Add a line break after the point.]\n
    * [Point 5: Specific, actionable criticism in bullet-point format. Use a positive and encouraging tone. Add a line break after the point.]\n

    Answer Templates:\n
    * Fresher: [Example answer template for a fresher, providing a clear structure for an effective answer. Use a positive and encouraging tone. Add a line break after the point.]\n

    * Experienced: [Example answer template for an experienced candidate, providing a clear structure for an effective answer. Use a positive and encouraging tone. Add a line break after the point.]\n

    ---

    **Special Instruction: If no speech is detected in the transcript, respond with the following, but still generate the answer templates based on the question:**

    **Analysis:**

    Evaluation: No speech was detected in the provided transcript.\n

    Answer Templates:
    *Fresher: [Example answer template for a fresher, providing a clear structure for an effective answer. Use a positive and encouraging tone. Add a line break after the point.]\n

    *Experienced: [Example answer template for an experienced candidate, providing a clear structure for an effective answer. Use a positive and encouraging tone. Add a line break after the point.]\n

    ---

    Here are a few examples of the desired output format:

    **Example 1:**
    Question: "Tell me about your greatest weakness."
    Response: "I sometimes work too hard."
    Analysis:
    Evaluation: The candidate's response is a common attempt to frame a positive trait as a weakness. While well-intentioned, it lacks genuine self-awareness.
    Constructive Criticism:
    * The response is cliche and lacks authenticity.
    * It doesn't demonstrate self-awareness or a willingness to improve.
    * It fails to address a genuine weakness.
    Answer Templates:
    Fresher: "While I'm generally organized, I sometimes struggle with time management when handling multiple tasks. I'm actively working on improving this by using time-blocking techniques."
    Experienced: "In the past, I've sometimes hesitated to delegate tasks. I've learned that empowering my team leads to better outcomes and have been working to improve my delegation skills."

    **Example 2:**
    Question: "Why should we hire you?"
    Response: "I'm a hard worker."
    Analysis:
    Evaluation: This response is too vague and doesn't effectively highlight the candidate's specific skills or qualifications for the role.
    Constructive Criticism:
    * It lacks specific examples of achievements.
    * It doesn't connect the candidate's skills to the company's needs.
    * It's not memorable or impactful.
    Answer Templates:
    Fresher: "I'm eager to learn and contribute. My coursework has provided me with a strong foundation in [relevant skill], and I'm confident I can quickly become a valuable asset to your team."
    Experienced: "My experience in [relevant field] aligns perfectly with the requirements of this role. I have a proven track record of [specific achievement] and I'm excited about the opportunity to contribute to your company's success."

    ---

    Now, evaluate the following response:

    Question: "{question}".
    Response: "{transcript}".
    Analysis:
    """
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error in Gemini analysis: {e}")
        return "Gemini analysis failed."

@app.route('/api/history')
@jwt_required()
def history():
    user_id = get_jwt_identity() # Supabase user ID
    # TODO: This route might need further review if INTERVIEW_QUESTIONS should be dynamic
    # or if user-specific history (beyond asked questions) is needed from Supabase.
    # For now, it only returns the static list of questions.
    # The previous MongoDB user lookup here was already non-functional after users_collection removal.
    # No direct Supabase user data is strictly needed to just return INTERVIEW_QUESTIONS.
    # However, if this route was intended to show user-specific history summary, it needs full rework.
    # For now, keeping it simple:
    # supabase_user = get_current_user()
    # if not supabase_user:
    #     return jsonify({'error': 'User not found or token invalid'}), 401
    
    return jsonify({'questions': INTERVIEW_QUESTIONS})

@app.route('/api/history/<question>')
@jwt_required()
def history_question(question):
    user_id = get_jwt_identity() # Supabase user ID
    question_text_param = unquote(question) # Decode URL-encoded question string

    # Fetch results from Supabase
    # This function should return a list of dictionaries.
    # Supabase primary key 'id' is a UUID string, so no special conversion like ObjectId is needed.
    results_data = get_interview_results_for_question(user_id, question_text_param)
    
    return jsonify({
        'question': question_text_param,
        'results': results_data
    })

# Renamed to avoid conflict with imported supabase_get_user_profile
@app.route('/api/user/me', methods=['GET'])
@jwt_required()
def get_user_me(): # Renamed function
    user_id = get_jwt_identity() # Supabase user ID
    current_sb_user = get_current_user() # Supabase User Auth object

    if not current_sb_user:
         return jsonify({'error': 'User not found from token'}), 401

    # Fetch profile data from Supabase 'profiles' table
    user_profile_details = supabase_get_user_profile(user_id)
    
    if not user_profile_details:
        # User exists in auth.users but not in profiles table
        return jsonify({
            'email': current_sb_user.email,
            'id': current_sb_user.id,
            'message': 'User profile not found in application database. Basic auth details provided.'
        }), 200 # Or 404 if profile is essential

    return jsonify({
        'id': current_sb_user.id,
        'email': current_sb_user.email, # Or user_profile_details.get('email')
        'api_key': user_profile_details.get('api_key'),
        'index_id': user_profile_details.get('index_id'),
        'role': user_profile_details.get('role', 'user')
        # Add any other fields from 'profiles' table
    })

@app.route('/api/user/update', methods=['PUT'])
@jwt_required()
def update_user_profile_route():
    user_id = get_jwt_identity() # Supabase user ID
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request data'}), 400

    update_payload = {}

    if 'api_key' in data and data['api_key'] is not None:
        api_key_to_check = data['api_key']
        api_result, api_error = check_api_connection(api_key_to_check)
        if not api_result:
            return jsonify({'error': f"Invalid API Key: {api_error}"}), 400
        update_payload['api_key'] = api_key_to_check
    
    if 'index_id' in data and data['index_id'] is not None:
        index_id_to_check = data['index_id']
        # Determine which API key to use for index_id validation
        # Prioritize the API key being updated in this request, otherwise use existing one.
        key_for_index_check = update_payload.get('api_key')
        if not key_for_index_check:
            profile = supabase_get_user_profile(user_id)
            if not profile or not profile.get('api_key'):
                return jsonify({'error': 'API key not found in profile, cannot validate index_id without it.'}), 400
            key_for_index_check = profile.get('api_key')

        index_result, index_error = check_index_id(key_for_index_check, index_id_to_check)
        if not index_result:
            return jsonify({'error': f"Invalid Index ID: {index_error}"}), 400
        update_payload['index_id'] = index_id_to_check

    if update_payload:
        updated_profile = supabase_update_user_profile(user_id, update_payload)
        if not updated_profile:
           return jsonify({'error': 'Failed to update profile in Supabase'}), 500

        # Construct a response that includes the updated fields
        response_user_data = {}
        if 'api_key' in updated_profile: # Supabase update usually returns the updated record
            response_user_data['api_key'] = updated_profile['api_key']
        if 'index_id' in updated_profile:
            response_user_data['index_id'] = updated_profile['index_id']

        return jsonify({
            'message': 'Profile updated successfully',
            'updated_fields': response_user_data
        }), 200
    
    return jsonify({'message': 'No fields to update or invalid data provided.'}), 400

@app.route('/api/user/reset-questions', methods=['POST'])
@jwt_required()
def reset_questions():
    user_id = get_jwt_identity() # Supabase user ID
    reset_result = reset_user_interview_progress(user_id) # Resets in Supabase
    if not reset_result:
        # Log this error
        print(f"Error: reset_user_interview_progress failed for user {user_id}")
        return jsonify({'error': 'Failed to reset interview progress.'}), 500
    return jsonify({'message': 'Questions reset successfully'})

@app.route('/resume/upload', methods=['POST'])
@jwt_required()
def upload_resume():
    try:
        user_id = get_jwt_identity() # Supabase user ID
            
        if 'resume' not in request.files:
            return jsonify({"error": "No resume file provided"}), 400
            
        resume_file = request.files['resume']
        if resume_file.filename == '':
            return jsonify({"error": "No resume file selected"}), 400
            
        # Create uploads directory if it doesn't exist
        resume_dir = os.path.join('uploads', 'resumes')
        os.makedirs(resume_dir, exist_ok=True)
        
        # Generate a client-side unique ID for this resume (e.g., for immediate client reference)
        client_resume_id_str = str(ObjectId())
        
        # Save the resume file
        file_ext = os.path.splitext(resume_file.filename)[1]
        # It's better to use a Supabase generated ID or client_resume_id_str for the filename to ensure uniqueness if needed
        # For now, keeping client_resume_id_str as part of the path for traceability.
        resume_filename_on_server = f"{client_resume_id_str}{file_ext}"
        resume_path = os.path.join(resume_dir, resume_filename_on_server)
        resume_file.save(resume_path)
        
        # Store job description if provided
        job_description = request.form.get('job_description', '')
        
        # Save resume metadata to Supabase
        saved_supa_resume = save_resume_metadata(
            user_id=user_id,
            filename=resume_file.filename, # Original filename
            file_path=resume_path, # Path on server (consider moving to Supabase storage later)
            job_description=job_description,
            client_resume_id=client_resume_id_str
        )
        
        if not saved_supa_resume:
            # Cleanup saved file if DB entry failed
            if os.path.exists(resume_path):
                try:
                    os.remove(resume_path)
                except Exception as e_clean:
                    print(f"Error cleaning up file {resume_path} after DB save failure: {e_clean}")
            return jsonify({"error": "Failed to save resume metadata to Supabase"}), 500
        
        # Return the client_resume_id_str, client uses this to refer to the uploaded resume
        return jsonify({"resumeId": client_resume_id_str}), 200
        
    except Exception as e:
        print(f"Error uploading resume: {str(e)}")
        return jsonify({"error": f"Error uploading resume: {str(e)}"}), 500

@app.route('/resume/analyze/<client_resume_id_param>', methods=['GET']) # Parameter name changed for clarity
@jwt_required()
def analyze_resume(client_resume_id_param): # Parameter name changed for clarity
    try:
        user_id = get_jwt_identity()
        
        # Fetch resume metadata from Supabase using client_resume_id
        resume_meta = get_resume_metadata_by_client_id(client_resume_id_param, user_id)
        if not resume_meta:
            return jsonify({"error": "Resume not found"}), 404

        resume_supa_id = resume_meta['id'] # Supabase generated UUID for the resume

        # Check if already analyzed by looking at 'analyzed' flag and 'analysis_id'
        if resume_meta.get("analyzed") and resume_meta.get("analysis_id"):
            # Fetch existing analysis from Supabase resume_analysis table
            existing_analysis_record = get_resume_analysis_by_resume_id(resume_supa_id, user_id)
            if existing_analysis_record:
                return jsonify({
                    "analysis": existing_analysis_record.get('analysis_data'),
                    "aiGeneratedResume": existing_analysis_record.get('ai_generated_resume'),
                    "resumeId": client_resume_id_param # Return the client_id for consistency
                }), 200
            else:
                # This case might indicate an issue, e.g., analysis_id present but record deleted
                print(f"Warning: Resume {client_resume_id_param} (Supa ID: {resume_supa_id}) marked analyzed but no analysis data found.")
                # Proceed to re-analyze as a fallback

        # Extract text from resume file (path stored in resume_meta)
        resume_file_path = resume_meta.get('file_path')
        if not resume_file_path or not os.path.exists(resume_file_path):
            return jsonify({"error": "Resume file not found on server."}), 500
            
        resume_text = ""
        try:
            with open(resume_file_path, "r", encoding="utf-8", errors="ignore") as f:
                resume_text = f.read()
        except Exception as e_read:
            print(f"Error reading resume file {resume_file_path}: {e_read}")
            return jsonify({"error": "Could not read resume file."}), 500
            
        # Get job description if available
        job_description = resume_meta.get("job_description", "")
        
        # Analyze resume with Gemini AI
        prompt = f"""
        You are a professional resume analyst. Please analyze the following resume:
        
        {resume_text}
        
        {"Job Description: " + job_description if job_description else ""}
        
        Provide a detailed analysis in the following JSON format:
        {{"score": <number between 0-100>,
         "summary": "<brief summary of the resume>",
         "strengths": ["<strength 1>", "<strength 2>", ...],
         "improvements": ["<improvement 1>", "<improvement 2>", ...],
         "keywords": ["<keyword 1>", "<keyword 2>", ...]
        }}
        
        {"Also include a job match analysis in the following format:\n" +
        "\"job_match\": {{\n" +
        "  \"score\": <match percentage>,\n" +
        "  \"summary\": \"<summary of how well the resume matches the job>\",\n" +
        "  \"missing_keywords\": [\"<missing keyword 1>\", \"<missing keyword 2>\", ...],\n" +
        "  \"recommendations\": [\"<recommendation 1>\", \"<recommendation 2>\", ...]\n" +
        "}}" if job_description else ""}
        
        Also generate an improved version of the resume that addresses the weaknesses and better highlights the strengths.
        """
        
        # Call Gemini API
        response = gemini_model.generate_content(prompt)
        
        # Parse the response
        response_text = response.text
        
        # Extract JSON part for analysis
        import re
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        analysis_json = {}
        ai_generated_resume = ""
        
        if json_match:
            try:
                analysis_json = json.loads(json_match.group())
                # Extract the AI-generated resume from the remaining text
                ai_generated_resume = response_text.replace(json_match.group(), "").strip()
            except json.JSONDecodeError:
                # If JSON parsing fails, use a default structure
                analysis_json = {
                    "score": 70,
                    "summary": "Analysis could not be properly formatted.",
                    "strengths": ["Resume has been received"],
                    "improvements": ["Try uploading a different format"],
                    "keywords": []
                }
        else:
            # If no JSON found, use the whole response as the resume
            ai_generated_resume = response_text
            analysis_json = {
                "score": 70,
                "summary": "Basic resume analysis completed.",
                "strengths": ["Resume has been processed"],
                "improvements": ["Consider adding more details"],
                "keywords": []
            }
        
        # Add client_resume_id_param to the analysis JSON for client reference
        analysis_json["resumeId"] = client_resume_id_param

        # Save new analysis to Supabase 'resume_analysis' table
        new_analysis_record = save_resume_analysis_data(
            resume_supa_id=resume_supa_id,
            user_id=user_id,
            analysis_json=analysis_json,
            ai_generated_resume_text=ai_generated_resume
        )
        
        if not new_analysis_record or not new_analysis_record.get('id'):
            return jsonify({"error": "Failed to save new resume analysis to Supabase"}), 500

        # Update the original resume metadata in 'resumes' table to link the analysis
        analysis_supa_id = new_analysis_record['id']
        update_meta_success = update_resume_with_analysis_info(resume_supa_id, analysis_supa_id, user_id)
        if not update_meta_success:
            # Log this, as analysis is saved but linking failed. Might need manual fix or retry.
            print(f"Error: Failed to link analysis {analysis_supa_id} to resume {resume_supa_id} in resumes table.")
            # Decide if to return error or proceed. For now, proceed.

        return jsonify({
            "analysis": analysis_json, # The new analysis
            "aiGeneratedResume": ai_generated_resume,
            "resumeId": client_resume_id_param
        }), 200
        
    except Exception as e:
        print(f"Error analyzing resume {client_resume_id_param}: {str(e)}")
        return jsonify({"error": f"Error analyzing resume: {str(e)}"}), 500

@app.route('/resume/chat', methods=['POST'])
@jwt_required()
def resume_chat():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        client_resume_id_req = data.get('resumeId')
        user_message = data.get('message') # Renamed for clarity
        
        if not client_resume_id_req or not user_message:
            return jsonify({"error": "Resume ID and message are required"}), 400
            
        # Fetch resume metadata from Supabase using client_resume_id
        resume_meta = get_resume_metadata_by_client_id(client_resume_id_req, user_id)
        if not resume_meta:
            return jsonify({"error": "Resume not found"}), 404

        resume_supa_id = resume_meta['id']
            
        # Get the analysis and AI-generated resume text for context
        analysis_data_for_prompt = {}
        ai_resume_text = ""
        if resume_meta.get('analyzed'):
            analysis_record = get_resume_analysis_by_resume_id(resume_supa_id, user_id)
            if analysis_record:
                analysis_data_for_prompt = analysis_record.get('analysis_data', {})
                ai_resume_text = analysis_record.get('ai_generated_resume', "")
            else:
                print(f"Warning: Resume {client_resume_id_req} (Supa ID: {resume_supa_id}) is marked analyzed, but no analysis record found for chat context.")
        
        # Create a prompt for Gemini
        prompt = f"""
        You are a helpful resume assistant. You have analyzed a user's resume and provided the following analysis:
        
        {json.dumps(analysis)}
        
        You have also generated an improved version of their resume:
        
        {ai_resume}
        
        The user is asking the following question about their resume:
        
        {user_message}
        
        Please provide a helpful, specific response to their question. Focus on practical advice that they can implement.
        """
        
        # Call Gemini API
        gemini_response = gemini_model.generate_content(prompt) # Renamed to avoid conflict
        ai_chat_response_text = gemini_response.text

        # Add chat message to Supabase resume record's chat_history
        add_chat_result = add_resume_chat_message(
            resume_supa_id=resume_supa_id,
            user_id=user_id,
            user_message=user_message,
            ai_response=ai_chat_response_text
        )
        
        if not add_chat_result:
            # Log this error, but still return AI response to user if Gemini call was successful
            print(f"Warning: Failed to save chat message to Supabase for resume {client_resume_id_req} (Supa ID: {resume_supa_id}).")
            # Consider if an error should be returned if DB save fails:
            # return jsonify({"error": "Failed to save chat message"}), 500

        return jsonify({"reply": ai_chat_response_text}), 200
        
    except Exception as e:
        print(f"Error in resume chat for resumeId {data.get('resumeId')}: {str(e)}")
        return jsonify({"error": f"Error processing chat: {str(e)}"}), 500

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True)