<br />
<div align="center">
  <a href="https://github.com/JaiAkash10/AI-Interview-Analyzer">
    <img src="https://github.com/JaiAkash10/TwelveLabs-Interview-App/blob/main/src/logo-interview.jpg" alt="Logo" width="80" height="80">
  </a>
  <h3 align="center">AI Interview Analyzer</h3>
  <p align="center">
    Empowering Interview Preparation with Twelve Labs and Gemini
    <br />
    <br />
  </p>
</div>

<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#About">About</a></li>
    <li><a href="#Features">Features</a></li>
    <li><a href="#Tech-Stack">Tech Stack</a></li>
    <li><a href="#Instructions-on-running-project-locally">Instructions on running project locally</a></li>
    <li><a href="#Usecases">Usecase</a></li>
  </ol>
</details>

------

## About

The AI Interview Analyzer is a powerful tool designed to revolutionize the interview preparation process. By leveraging Twelve Labs, this application provides valuable feedback and insights based on various factors such as body language, voice pitch, confidence, and other critical aspects of an interview performance.

If you are a job seeker looking to improve your interview skills, the AI Interview Analyzer is an indispensable tool that empowers users to make informed decisions and achieve success in their interview endeavors.

## Features

📊 **Comprehensive Analysis**: The power of Pegasus 1.1 from TwelveLabs to gain deep insights into interview performance.

🎯 **Key Points Identification**: Automatically identify and highlight important points discussed during the interview for quick reference.

🕴️**Body Language Analysis**: Receive feedback on body language, including posture, gestures, and facial expressions, to enhance nonverbal communication skills.

💪**Confidence Assessment**: Measure and provide feedback on the interviewe's confidence level throughout the interview. 

📝 **Interview Transcription**:  Automatically transcribe the interview for easy review and analysis.

📈 **Performance Metrics**: Generate performance metrics and scores based on various aspects of the interview.


## Tech Stack

**Frontend** - JavaScript, HTML, CSS

**Backend** -  Flask, Twelve Labs, Gemini

**AI Technologies** - Marengo 2.6 (Video Embedding), Pegasus 1.1 (Generative Model), Gemini 2.0 
 
 
## Instructions on running project locally:

Clone the project

```bash
  git clone https://github.com/JaiAkash10/TwelveLabs-Interview-App.git
```

Install dependencies:

```bash
 cd TwelveLabs-Interview-App
 
 pip install -r requirements.txt
```

Do prepare the .env file and put the following content in the .env file

```
API_KEY = "<Your API Key>"

# Carefully add the Index ID which is created from the Twelvelabs playground

API_URL = "https://api.twelvelabs.io/v1.2/indexes/<Your Index ID>"
index_id = "<Your Index ID>"

```

Start the server

```bash
  http://localhost:8501/
```

## Usecases

📚️ **Interview Preparation:** Job seekers can leverage the AI Interview Analyzer to practice and refine their interview skills in a realistic setting.

🎓 **Training and Development** Organizations can incorporate the AI Interview Analyzer into their training and development programs to enhance the interview skills of their employees.

😊️ **Identifying Suspected Users** The AI Interview Analyzer contributes to a positive candidate experience by providing valuable insights and feedback to job seekers.
