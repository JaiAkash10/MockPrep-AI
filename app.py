import os
import json
import random
import requests
import datetime
from urllib.parse import unquote
from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from dotenv import load_dotenv
from twelvelabs import TwelveLabs
from twelvelabs.models.task import Task
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
import google.generativeai as genai 
import speech_recognition as sr
from moviepy.editor import VideoFileClip
from datetime import timedelta
from flask_login import LoginManager, UserMixin

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

# MongoDB setup
mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client["ai-interview-analyzer"]
users_collection = db["users"]
results_collection = db["results"]

API_URL = os.getenv('API_URL')

# Gemini AI setup
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.0-flash')  # Initialize Gemini model

print("Environment Variables:")
print(f"API_URL exists: {'API_URL' in os.environ}")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 

@login_manager.user_loader
def load_user(user_id):
    # Load your user from the database based on user_id
    # Return None if the user doesn't exist
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if user:
        return User(user)
    return None

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.email = user_data['email']

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

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
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    user_data = users_collection.find_one({"email": email})
    if user_data and check_password_hash(user_data['password'], password):
        access_token = create_access_token(identity=str(user_data['_id']))
        return jsonify({
            'token': access_token,
            'user': {
                'email': email,
                'api_key': user_data['api_key'],
                'index_id': user_data['index_id'],
                'role': user_data.get('role', 'user')
            }
        })
    return jsonify({'error': 'Invalid email or password'}), 401

@app.route('/api/auth/validate', methods=['GET'])
@jwt_required()
def validate_token():
    current_user_id = get_jwt_identity()
    user_data = users_collection.find_one({"_id": ObjectId(current_user_id)})
    if user_data:
        return jsonify({
            'valid': True,
            'user': {
                'email': user_data['email'],
                'api_key': user_data['api_key'],
                'index_id': user_data['index_id'],
                'role': user_data.get('role', 'user')
            }
        })
    return jsonify({'valid': False}), 401

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
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400

        email = data.get('email')
        password = data.get('password')
        api_key = data.get('api_key')
        index_id = data.get('index_id')

        # Validate required fields
        if not all([email, password, api_key, index_id]):
            return jsonify({'error': 'All fields are required'}), 400

        # Check if email already exists
        if users_collection.find_one({"email": email}):
            return jsonify({'error': 'Email already registered'}), 400

        # Check API connection with timeout
        try:
            api_result, api_error = check_api_connection(api_key)
            if not api_result:
                return jsonify({'error': api_error}), 400
        except Exception as e:
            return jsonify({'error': f'API validation error: {str(e)}'}), 500

        # Check Index ID with timeout
        try:
            index_result, index_error = check_index_id(api_key, index_id)
            if not index_result:
                return jsonify({'error': index_error}), 400
        except Exception as e:
            return jsonify({'error': f'Index validation error: {str(e)}'}), 500

        # Create user in database
        try:
            hashed_password = generate_password_hash(password)
            users_collection.insert_one({
                "email": email,
                "password": hashed_password,
                "api_key": api_key,
                "index_id": index_id
            })
            return jsonify({'message': 'Registration successful'}), 201
        except Exception as e:
            return jsonify({'error': f'Database error: {str(e)}'}), 500

    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

@app.route('/api/questions/next', methods=['GET'])
@jwt_required()
def get_question():
    user_id = get_jwt_identity()
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Get user's asked questions from database
    asked_questions = user.get('asked_questions', [])
    available_questions = [q for q in INTERVIEW_QUESTIONS if q not in asked_questions]

    if not available_questions:
        return jsonify({"message": "All questions have been asked."})

    question = random.choice(available_questions)
    
    # Update user's asked questions in database
    users_collection.update_one(
        {'_id': ObjectId(user_id)},
        {
            '$push': {'asked_questions': question},
            '$set': {'current_question': question}
        }
    )
    
    return jsonify({"question": question})


@app.route('/api/upload', methods=['POST'])
@jwt_required()
def upload():
    user_id = get_jwt_identity()
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    api_key = user['api_key']
    index_id = user['index_id']
    email = user['email']

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

        # Store results in Database
        email = session['email']
        question = session.get('current_question')  # Retrieve question from session.

        print(f"Processed data: {processed_data}")

        transcript = get_transcript(video_path)
        gemini_analysis = analyze_with_gemini(question, transcript)

        results_collection.insert_one({
            "email": email,
            "video_id": task.video_id,
            "question": question,  # Use the question from the session.
            "results": processed_data,
            "gemini_analysis": gemini_analysis
        })

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
    user_id = get_jwt_identity()
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'questions': INTERVIEW_QUESTIONS})

@app.route('/api/history/<question>')
@jwt_required()
def history_question(question):
    user_id = get_jwt_identity()
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    email = user['email']
    question = unquote(question)

    query = {"email": email, "question": question}
    results = list(results_collection.find(query).sort("_id", -1))
    
    # Convert ObjectId to string for JSON serialization
    for result in results:
        result['_id'] = str(result['_id'])
    
    return jsonify({
        'question': question,
        'results': results
    })

@app.route('/api/user/profile')
@jwt_required()
def get_user_profile():
    user_id = get_jwt_identity()
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'email': user['email'],
        'api_key': user['api_key'],
        'index_id': user['index_id']
    })

@app.route('/api/user/update', methods=['PUT'])
@jwt_required()
def update_user_profile():
    user_id = get_jwt_identity()
    user = users_collection.find_one({'_id': ObjectId(user_id)})
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    update_fields = {}
    
    if 'api_key' in data:
        api_result, api_error = check_api_connection(data['api_key'])
        if not api_result:
            return jsonify({'error': api_error}), 400
        update_fields['api_key'] = data['api_key']
    
    if 'index_id' in data:
        if 'api_key' in update_fields:
            api_key = update_fields['api_key']
        else:
            api_key = user['api_key']
        index_result, index_error = check_index_id(api_key, data['index_id'])
        if not index_result:
            return jsonify({'error': index_error}), 400
        update_fields['index_id'] = data['index_id']
    
    if update_fields:
        users_collection.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': update_fields}
        )
    
    return jsonify({'message': 'Profile updated successfully'})

@app.route('/api/user/reset-questions', methods=['POST'])
@jwt_required()
def reset_questions():
    user_id = get_jwt_identity()
    users_collection.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'asked_questions': [], 'current_question': None}}
    )
    return jsonify({'message': 'Questions reset successfully'})

@app.route('/resume/upload', methods=['POST'])
@jwt_required()
def upload_resume():
    try:
        user_id = get_jwt_identity()
        user = users_collection.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'error': 'User not found'}), 404
            
        if 'resume' not in request.files:
            return jsonify({"error": "No resume file provided"}), 400
            
        resume_file = request.files['resume']
        if resume_file.filename == '':
            return jsonify({"error": "No resume file selected"}), 400
            
        # Create uploads directory if it doesn't exist
        resume_dir = os.path.join('uploads', 'resumes')
        os.makedirs(resume_dir, exist_ok=True)
        
        # Generate a unique ID for this resume
        resume_id = str(ObjectId())
        
        # Save the resume file
        file_ext = os.path.splitext(resume_file.filename)[1]
        resume_path = os.path.join(resume_dir, f"{resume_id}{file_ext}")
        resume_file.save(resume_path)
        
        # Store job description if provided
        job_description = request.form.get('job_description', '')
        
        # Store resume info in database
        resume_data = {
            "user_id": user_id,
            "resume_id": resume_id,
            "filename": resume_file.filename,
            "file_path": resume_path,
            "job_description": job_description,
            "upload_date": datetime.datetime.now(),
            "analyzed": False
        }
        
        db.resumes.insert_one(resume_data)
        
        return jsonify({"resumeId": resume_id}), 200
        
    except Exception as e:
        print(f"Error uploading resume: {str(e)}")
        return jsonify({"error": f"Error uploading resume: {str(e)}"}), 500

@app.route('/resume/analyze/<resume_id>', methods=['GET'])
@jwt_required()
def analyze_resume(resume_id):
    try:
        user_id = get_jwt_identity()
        
        # Find the resume in the database
        resume_data = db.resumes.find_one({"resume_id": resume_id, "user_id": user_id})
        if not resume_data:
            return jsonify({"error": "Resume not found"}), 404
            
        # Check if resume has already been analyzed
        if resume_data.get("analysis"):
            return jsonify({
                "analysis": resume_data["analysis"],
                "aiGeneratedResume": resume_data.get("ai_generated_resume", "")
            }), 200
            
        # Extract text from resume file
        # For simplicity, we'll assume it's a text file for now
        # In a real app, you'd use libraries like PyPDF2 for PDFs or python-docx for Word docs
        resume_text = ""
        with open(resume_data["file_path"], "r", encoding="utf-8", errors="ignore") as f:
            resume_text = f.read()
            
        # Get job description if available
        job_description = resume_data.get("job_description", "")
        
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
        
        # Add resumeId to the analysis
        analysis_json["resumeId"] = resume_id
        
        # Update the database with the analysis results
        db.resumes.update_one(
            {"resume_id": resume_id},
            {"$set": {
                "analysis": analysis_json,
                "ai_generated_resume": ai_generated_resume,
                "analyzed": True,
                "analysis_date": datetime.datetime.now()
            }}
        )
        
        return jsonify({
            "analysis": analysis_json,
            "aiGeneratedResume": ai_generated_resume
        }), 200
        
    except Exception as e:
        print(f"Error analyzing resume: {str(e)}")
        return jsonify({"error": f"Error analyzing resume: {str(e)}"}), 500

@app.route('/resume/chat', methods=['POST'])
@jwt_required()
def resume_chat():
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        resume_id = data.get('resumeId')
        message = data.get('message')
        
        if not resume_id or not message:
            return jsonify({"error": "Resume ID and message are required"}), 400
            
        # Find the resume in the database
        resume_data = db.resumes.find_one({"resume_id": resume_id, "user_id": user_id})
        if not resume_data:
            return jsonify({"error": "Resume not found"}), 404
            
        # Get the analysis and resume text
        analysis = resume_data.get("analysis", {})
        ai_resume = resume_data.get("ai_generated_resume", "")
        
        # Create a prompt for Gemini
        prompt = f"""
        You are a helpful resume assistant. You have analyzed a user's resume and provided the following analysis:
        
        {json.dumps(analysis)}
        
        You have also generated an improved version of their resume:
        
        {ai_resume}
        
        The user is asking the following question about their resume:
        
        {message}
        
        Please provide a helpful, specific response to their question. Focus on practical advice that they can implement.
        """
        
        # Call Gemini API
        response = gemini_model.generate_content(prompt)
        
        # Store the chat in the database
        if not resume_data.get("chat_history"):
            db.resumes.update_one(
                {"resume_id": resume_id},
                {"$set": {"chat_history": []}}
            )
            
        db.resumes.update_one(
            {"resume_id": resume_id},
            {"$push": {"chat_history": {
                "user": message,
                "ai": response.text,
                "timestamp": datetime.datetime.now()
            }}}
        )
        
        return jsonify({"reply": response.text}), 200
        
    except Exception as e:
        print(f"Error in resume chat: {str(e)}")
        return jsonify({"error": f"Error processing chat: {str(e)}"}), 500

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True)