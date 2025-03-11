import os
import json
import random
import requests
from urllib.parse import unquote
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv
from twelvelabs import TwelveLabs
from twelvelabs.models.task import Task
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_required, login_user, current_user, UserMixin, logout_user
from bson.objectid import ObjectId
import google.generativeai as genai 

# from flask import Flask, render_template, request, jsonify
# from twelvelabs import TwelveLabs
# from twelvelabs.models.task import Task
# import requests
# from dotenv import load_dotenv

load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') 

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
    # Example:
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
        print(f"Attempting to connect to API: {api_url}")
        print(f"API Key (first 4 chars): {api_key[:4]}...")
        
        response = requests.get(api_url, headers={
            "x-api-key": api_key,
            "Accept": "application/json"
        })
        if response.status_code not in [200, 401, 403]:
            return False, f"API key check failed with status code: {response.status_code}"
        return True, None
    except requests.RequestException as e:
        return False, f"API connection check failed. Detailed error: {str(e)}"
    
def get_transcript(video_file):
    # This is a placeholder. Replace with your actual speech-to-text logic.
    return "This is a simulated transcript of the candidate's response."

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

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_data = users_collection.find_one({"email": email})
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user)  # Log the user in
            session['email'] = email
            session['api_key'] = user_data['api_key']
            session['index_id'] = user_data['index_id']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Invalid email or password')
    return render_template('login.html')

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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        api_key = request.form['api_key']
        index_id = request.form['index_id']

        if users_collection.find_one({"email": email}):
            return render_template('register.html', error='Email already registered')

        api_result, api_error = check_api_connection(api_key)
        if not api_result:
            return render_template('register.html', error=api_error)

        index_result, index_error = check_index_id(api_key, index_id)
        if not index_result:
            return render_template('register.html', error=index_error)

        # if not check_api_connection(api_key): #Corrected line
        #     return render_template('register.html', error="Invalid TwelveLabs API key")

        hashed_password = generate_password_hash(password)
        users_collection.insert_one({
            "email": email,
            "password": hashed_password,
            "api_key": api_key,
            "index_id": index_id
        })
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/index')
@login_required
def index():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/get_question')
@login_required
def get_question():
    question = random.choice(INTERVIEW_QUESTIONS)
    session['current_question'] = question
    return jsonify({"question": question})

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'email' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    api_key = session['api_key']
    index_id = session['index_id']
    email = session['email']

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
        question = session.get('current_question') #Retrieve question from session.

        print(f"Processed data: {processed_data}")

        transcript = get_transcript(video_path)
        gemini_analysis = analyze_with_gemini(question, transcript)

        results_collection.insert_one({
            "email": email,
            "video_id": task.video_id,
            "question": question, #Use the question from the session.
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

def analyze_with_gemini(question, transcript):
    prompt = f"""
    Evaluate the following response to the question: "{question}".

    Response: "{transcript}"

    Provide a concise and respectful evaluation of the response. Focus on providing constructive criticism. Then, offer two good answer templates as suggestions, one for freshers and one for experienced candidates.

    The response should be:
    1. Short and to the point.
    3. The response must contai a maximum of 5 points.
    2. Respectful and encouraging.
    3. Focused on improvement.
    4. Provide a simple and easy to understand template for a good answer for both freshers and experienced candidates.
    5. Provide the response in a human written format.
    6. After each point leave a line break.
    """
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Error in Gemini analysis: {e}")
        return "Gemini analysis failed."

@app.route('/history')
@login_required
def history():
    if 'email' not in session:
        return redirect(url_for('login'))
    return render_template('history.html', questions=INTERVIEW_QUESTIONS)

@app.route('/history_question/<question>')
@login_required
def history_question(question):
    if 'email' not in session:
        return redirect(url_for('login'))
    email = session['email']
    question = unquote(question)

    document = results_collection.find_one({'email': email, 'question': question})

    if document:
        print(f"History question database: '{document['question']}'")
    else:
        print("No matching document found.")

    query = {"email": email, "question": question}
    results = list(results_collection.find(query).sort("_id", -1))
    print(f"Query results: {results}")
    return render_template('history_question.html', results=results, question=question)

@app.route('/logout')
def logout():
    session.pop('email', None)
    session.pop('api_key', None)
    session.pop('index_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    app.run(debug=True)