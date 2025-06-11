import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import Webcam from 'react-webcam';
import api from '../api';
import '../styles/interview.css'

const Interview = () => {
  const navigate = useNavigate();
  const webcamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const [recordedChunks, setRecordedChunks] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState('ready');
  const [prepTimeLeft, setPrepTimeLeft] = useState(20);
  const [recordingTimeLeft, setRecordingTimeLeft] = useState(60);
  const [timerInterval, setTimerInterval] = useState(null);
  const [showInstructions, setShowInstructions] = useState(false);
  const [askedQuestions, setAskedQuestions] = useState([]);
  const [sessionActive, setSessionActive] = useState(false);
  const [analysisComplete, setAnalysisComplete] = useState(false);
  const [allQuestions, setAllQuestions] = useState([]);
  const [sessionQuestions, setSessionQuestions] = useState([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [networkStatus, setNetworkStatus] = useState('good'); // good, fair, poor
  const [voiceLevel, setVoiceLevel] = useState(0); // 0-100
  const [audioContext, setAudioContext] = useState(null);
  const [analyser, setAnalyser] = useState(null);
  const [voiceMonitoringActive, setVoiceMonitoringActive] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [analysisSteps, setAnalysisSteps] = useState({
    uploading: false,
    nonContextual: false,
    contextual: false
  });

  useEffect(() => {
    const fetchAllQuestions = async () => {
      try {
        setIsLoading(true);
        const response = await api.get('/api/questions/all');
        const questions = response.data.questions || [];
        setAllQuestions(questions);
      } catch (err) {
        console.error('Error fetching questions:', err);
        setError('Failed to load interview questions. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchAllQuestions();

    // Network monitoring
    const monitorNetwork = () => {
      const connection = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
      if (connection) {
        const speed = connection.downlink;
        if (speed >= 10) setNetworkStatus('good');
        else if (speed >= 1) setNetworkStatus('fair');
        else setNetworkStatus('poor');
      }
    };

    const networkInterval = setInterval(monitorNetwork, 2000);
    monitorNetwork();

    return () => {
      if (timerInterval) clearInterval(timerInterval);
      clearInterval(networkInterval);
      stopCameraStream();
      if (audioContext) {
        audioContext.close();
      }
    };
  }, []);

  // Voice monitoring effect
  useEffect(() => {
    let animationFrame;
    
    const monitorLoop = () => {
      if (voiceMonitoringActive && window.voiceMonitor) {
        window.voiceMonitor();
        animationFrame = requestAnimationFrame(monitorLoop);
      }
    };
    
    if (voiceMonitoringActive) {
      monitorLoop();
    }
    
    return () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
    };
  }, [voiceMonitoringActive]);

  const startInterview = async () => {
    try {
      setError(null); // Clear any previous errors
      
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280, max: 1920 },
          height: { ideal: 720, max: 1080 },
          facingMode: "user"
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100
        }
      });

      // Set up audio analysis for voice level monitoring
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const analyserNode = audioCtx.createAnalyser();
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyserNode);
      
      analyserNode.fftSize = 256;
      const bufferLength = analyserNode.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);
      
      setAudioContext(audioCtx);
      setAnalyser(analyserNode);
      
      // Create voice monitoring function
      const monitorVoice = () => {
        analyserNode.getByteFrequencyData(dataArray);
        const average = dataArray.reduce((a, b) => a + b) / bufferLength;
        const voicePercentage = Math.min(100, (average / 128) * 100);
        setVoiceLevel(voicePercentage);
      };
      
      // Store monitoring function for later use
      window.voiceMonitor = monitorVoice;
      window.voiceDataArray = dataArray;
      window.voiceAnalyser = analyserNode;
      
      // Use better video codec if available
      let options = { mimeType: 'video/webm;codecs=vp9' };
      if (!MediaRecorder.isTypeSupported(options.mimeType)) {
        options = { mimeType: 'video/webm;codecs=vp8' };
        if (!MediaRecorder.isTypeSupported(options.mimeType)) {
          options = { mimeType: 'video/webm' };
        }
      }
      
      mediaRecorderRef.current = new MediaRecorder(stream, options);

      mediaRecorderRef.current.ondataavailable = handleDataAvailable;
      mediaRecorderRef.current.onstop = handleStop;

      setStatus('preparing');
      startTimer('prep');
      
    } catch (err) {
      console.error('Error accessing camera:', err);
      setError('Unable to access camera or microphone. Please ensure you have given permission and try again.');
      setStatus('error');
    }
  };

  const startTimer = (phase) => {
    const timeLeft = phase === 'prep' ? 20 : 60;
    const setTimeLeft = phase === 'prep' ? setPrepTimeLeft : setRecordingTimeLeft;

    setTimeLeft(timeLeft);

    const interval = setInterval(() => {
      setTimeLeft((prevTime) => {
        if (prevTime <= 1) {
          clearInterval(interval);
          if (phase === 'prep') {
            startRecording();
          } else {
            stopRecording();
          }
          return 0;
        }
        return prevTime - 1;
      });
    }, 1000);

    setTimerInterval(interval);
  };

  const startRecording = () => {
    setStatus('recording');
    setRecordedChunks([]);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'inactive') {
      mediaRecorderRef.current.start(1000); // Record in 1-second chunks
    }
    startTimer('recording');
    
    // Start voice level monitoring during recording
    setVoiceMonitoringActive(true);
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (timerInterval) {
      clearInterval(timerInterval);
      setTimerInterval(null);
    }
    // Stop voice monitoring
    setVoiceMonitoringActive(false);
    setVoiceLevel(0);
    setStatus('uploading');
    setAnalysisSteps({
      uploading: true,
      nonContextual: false,
      contextual: false
    });
  };

  const finishRecording = () => {
    stopRecording();
  };

  const handleDataAvailable = (event) => {
    if (event.data.size > 0) {
      setRecordedChunks((prev) => [...prev, event.data]);
    }
  };

  const handleStop = () => {
    // Wait a bit to ensure all chunks are collected
    setTimeout(() => {
      if (recordedChunks.length === 0) {
        setError('No video data recorded. Please try again.');
        setStatus('error');
        return;
      }
      
      const blob = new Blob(recordedChunks, { type: 'video/webm' });
      if (blob.size === 0) {
        setError('Recording failed - no data captured. Please try again.');
        setStatus('error');
        return;
      }
      
      uploadVideo(blob);
      stopCameraStream();
    }, 500);
  };

  const stopCameraStream = () => {
    if (webcamRef.current && webcamRef.current.stream) {
      const tracks = webcamRef.current.stream.getTracks();
      tracks.forEach(track => track.stop());
    }
  };

  const uploadVideo = async (blob) => {
    try {
      setUploadProgress(0);
      
      // Validate blob size
      const maxSize = 100 * 1024 * 1024; // 100MB limit for better reliability
      if (blob.size > maxSize) {
        throw new Error('Video file is too large. Please try recording a shorter response.');
      }
      
      if (blob.size < 1000) { // Less than 1KB is probably empty
        throw new Error('Recording appears to be empty. Please try again.');
      }

      const formData = new FormData();
      formData.append('video', blob, `interview_${Date.now()}.webm`);
      formData.append('question', currentQuestion);

      // Update progress steps
      setAnalysisSteps(prev => ({
        ...prev,
        uploading: true
      }));

      const response = await api.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 300000, // 5 minutes timeout
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
          
          if (percentCompleted === 100) {
            setAnalysisSteps(prev => ({
              ...prev,
              uploading: true,
              nonContextual: true
            }));
          }
        }
      });

      // Check if response contains error
      if (response.data.error) {
        throw new Error(response.data.error);
      }

      console.log('Video uploaded and analyzed successfully:', response.data);
      
      // Update final step
      setAnalysisSteps(prev => ({
        ...prev,
        uploading: true,
        nonContextual: true,
        contextual: true
      }));
      
      setAnalysisComplete(true);
      setStatus('completed');
      
    } catch (err) {
      console.error('Error uploading video:', err);
      
      let errorMessage = 'Failed to upload and analyze video. ';
      
      if (err.response) {
        // Server responded with error status
        if (err.response.status === 413) {
          errorMessage += 'File too large. Please try recording a shorter response.';
        } else if (err.response.status === 500) {
          errorMessage += 'Server error during analysis. Please try again.';
        } else if (err.response.data && err.response.data.error) {
          errorMessage += err.response.data.error;
        } else {
          errorMessage += `Server error (${err.response.status}). Please try again.`;
        }
      } else if (err.request) {
        // Network error
        errorMessage += 'Network error. Please check your connection and try again.';
      } else if (err.message) {
        errorMessage += err.message;
      } else {
        errorMessage += 'Please try again.';
      }
      
      setError(errorMessage);
      setStatus('error');
      setAnalysisSteps({
        uploading: false,
        nonContextual: false,
        contextual: false
      });
    }
  };

  const initializeSession = () => {
    if (allQuestions.length === 0) {
      setError('No questions available. Please try again later.');
      return;
    }
    
    // Shuffle questions for random order
    const shuffledQuestions = [...allQuestions].sort(() => Math.random() - 0.5);
    setSessionQuestions(shuffledQuestions);
    setCurrentQuestionIndex(0);
    setCurrentQuestion(shuffledQuestions[0]);
    setAskedQuestions([shuffledQuestions[0]]);
    setSessionActive(true);
    setAnalysisComplete(false);
    setStatus('ready');
    setError(null); // Clear any previous errors
  };

  const fetchNextQuestion = () => {
    const nextIndex = currentQuestionIndex + 1;
    
    if (nextIndex >= sessionQuestions.length) {
      // All questions completed
      setSessionActive(false);
      setStatus('interview_complete');
      return;
    }
    
    const nextQuestion = sessionQuestions[nextIndex];
    setCurrentQuestionIndex(nextIndex);
    setCurrentQuestion(nextQuestion);
    setAskedQuestions(prev => [...prev, nextQuestion]);
    setAnalysisComplete(false);
    setStatus('ready');
    setError(null); // Clear any previous errors
  };

  const endInterview = () => {
    setSessionActive(false);
    setStatus('interview_complete');
    if (timerInterval) {
      clearInterval(timerInterval);
      setTimerInterval(null);
    }
    stopCameraStream();
  };

  const viewAnalysis = () => {
    navigate('/analysis');
  };

  const retryUpload = () => {
    if (recordedChunks.length > 0) {
      const blob = new Blob(recordedChunks, { type: 'video/webm' });
      setStatus('uploading');
      setError(null);
      setAnalysisSteps({
        uploading: true,
        nonContextual: false,
        contextual: false
      });
      uploadVideo(blob);
    } else {
      setError('No recorded video to retry. Please record again.');
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="page-container">
      <div className="interview-container">
        <div className="interview-wrapper">
          <section className="interview-card">
            <div className="interview-header">
              <h2 className="interview-title">Mock Interview</h2>
              <button 
                onClick={() => setShowInstructions(true)} 
                className="instructions-btn"
              >
                Instructions
              </button>
            </div>

            {isLoading ? (
              <div className="loader-container">
                <div className="loader"></div>
              </div>
            ) : error ? (
              <div className="error-message">
                {error}
                <div className="error-actions">
                  <button onClick={() => window.location.reload()} className="btn-secondary">
                    Try Again
                  </button>
                  {status === 'error' && recordedChunks.length > 0 && (
                    <button onClick={retryUpload} className="btn-primary">
                      Retry Upload
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <div className="interview-content">
                {status === 'ready' && sessionActive && (
                  <div className="interview-section">
                    <div className="question-display-prep">
                      <div className="question-box">
                        <h3>Interview Question {currentQuestionIndex + 1} of {sessionQuestions.length}</h3>
                        <p className="question-text">{currentQuestion}</p>
                      </div>
                    </div>
                    <div className="start-section">
                      <p className="start-info">When you're ready, click the button below to begin answering this question.</p>
                      <button onClick={startInterview} className="btn-primary">
                        Start Recording
                      </button>
                    </div>
                  </div>
                )}

                {!sessionActive && status !== 'interview_complete' && (
                  <div className="start-section">
                    <h3>Welcome to Mock Interview</h3>
                    <p className="start-info">Click below to start a new interview session with randomly selected questions.</p>
                    <button onClick={initializeSession} className="btn-primary">
                      Start Interview Session
                    </button>
                  </div>
                )}

                {status === 'preparing' && (
                  <div className="interview-section">
                    <div className="question-display-prep">
                      <div className="question-box">
                        <h3>Interview Question</h3>
                        <p className="question-text">{currentQuestion}</p>
                      </div>
                    </div>
                    <div className="prep-timer">
                      <h3>Preparation Time</h3>
                      <div className="timer-display">{formatTime(prepTimeLeft)}</div>
                      <p>Review the question and prepare your answer</p>
                    </div>
                  </div>
                )}

                {status === 'recording' && (
                  <div className="interview-section">
                    <div className="question-display-recording">
                      <div className="question-box">
                        <h3>Interview Question</h3>
                        <p className="question-text">{currentQuestion}</p>
                      </div>
                    </div>
                    <div className="recording-area">
                      <div className="webcam-container">
                        <Webcam
                          audio={true}
                          ref={webcamRef}
                          videoConstraints={{
                            width: 1280,
                            height: 720,
                            facingMode: "user"
                          }}
                          className="webcam-video"
                        />
                      </div>
                      
                      <div className="recording-controls">
                        <div className="record-timer">
                          <h3>Recording Time</h3>
                          <div className="timer-display">{formatTime(recordingTimeLeft)}</div>
                        </div>
                        
                        <div className="status-indicators">
                          <div className={`network-status ${networkStatus}`}>
                            <span className="status-icon">📶</span>
                            <span style={{
                              color: networkStatus === 'good' ? '#10b981' : 
                                     networkStatus === 'fair' ? '#f59e0b' : '#ef4444'
                            }}>Network: {networkStatus}</span>
                          </div>
                          
                          <div className="voice-level-indicator">
                            <span className="status-icon">🎤</span>
                            <span>Voice: {Math.round(voiceLevel)}%</span>
                            <div className="voice-meter">
                              <div 
                                className="voice-fill" 
                                style={{ width: `${voiceLevel}%`, backgroundColor: voiceLevel > 60 ? '#10b981' : voiceLevel > 30 ? '#f59e0b' : '#ef4444' }}
                              ></div>
                            </div>
                          </div>
                        </div>
                        
                        <button 
                          className="finish-btn"
                          onClick={finishRecording}
                        >
                          Finish Recording
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {status === 'uploading' && (
                  <div className="uploading-section">
                    <div className="loader-container">
                      <div className="loader"></div>
                    </div>
                    <div className="upload-status">
                      <h3>Processing Your Interview</h3>
                      <p>Your video is being analyzed by our AI system. This may take a few minutes...</p>
                      
                      {uploadProgress > 0 && uploadProgress < 100 && (
                        <div className="upload-progress">
                          <div className="progress-bar">
                            <div 
                              className="progress-fill" 
                              style={{ width: `${uploadProgress}%` }}
                            ></div>
                          </div>
                          <p>Uploading: {uploadProgress}%</p>
                        </div>
                      )}
                      
                      <div className="upload-steps">
                        <div className={`step ${analysisSteps.uploading ? 'active' : ''}`}>
                          <span className="step-number">1</span>
                          <span className="step-text">Uploading video</span>
                          {analysisSteps.uploading && <span className="step-check">✓</span>}
                        </div>
                        <div className={`step ${analysisSteps.nonContextual ? 'active' : ''}`}>
                          <span className="step-number">2</span>
                          <span className="step-text">Non-Contextual Analysis</span>
                          {analysisSteps.nonContextual && <span className="step-check">✓</span>}
                        </div>
                        <div className={`step ${analysisSteps.contextual ? 'active' : ''}`}>
                          <span className="step-number">3</span>
                          <span className="step-text">Contextual Analysis and Feedback</span>
                          {analysisSteps.contextual && <span className="step-check">✓</span>}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {status === 'completed' && analysisComplete && sessionActive && (
                  <div className="completion-section">
                    <div className="completion-message">
                      <h3>✅ Analysis Complete!</h3>
                      <p>Your interview response has been successfully analyzed. What would you like to do next?</p>
                    </div>
                    <div className="action-buttons">
                      <button onClick={viewAnalysis} className="btn-secondary">
                        View Analysis
                      </button>
                      <button onClick={fetchNextQuestion} className="btn-primary">
                        Next Question
                      </button>
                      <button onClick={endInterview} className="btn-danger">
                        End Interview
                      </button>
                    </div>
                    <div className="session-info">
                      <p>Questions completed: {askedQuestions.length}/{sessionQuestions.length}</p>
                    </div>
                  </div>
                )}

                {status === 'interview_complete' && (
                  <div className="interview-complete-section">
                    <div className="completion-message">
                      <h2>🎉 Interview Complete!</h2>
                      <p>Congratulations! You have successfully completed your mock interview session.</p>
                      <p>You answered {askedQuestions.length} questions and gained valuable practice experience.</p>
                    </div>
                    <div className="final-actions">
                      <button onClick={viewAnalysis} className="btn-primary">
                        View All Analysis
                      </button>
                      <button onClick={() => navigate('/dashboard')} className="btn-secondary">
                        Back to Dashboard
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </section>
        </div>
      </div>

      {/* Instructions Modal */}
      {showInstructions && (
        <div className="modal-overlay" onClick={() => setShowInstructions(false)}>
          <div className="instructions-modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Interview Instructions</h3>
              <button 
                className="close-btn" 
                onClick={() => setShowInstructions(false)}
              >
                ×
              </button>
            </div>
            <div className="modal-content">
              <div className="instruction-section">
                <h4>📹 Virtual Interview Setup</h4>
                <ul>
                  <li><strong>Lighting:</strong> Ensure your face is well-lit with natural light or a lamp in front of you</li>
                  <li><strong>Camera Position:</strong> Place camera at eye level for professional appearance</li>
                  <li><strong>Background:</strong> Use a clean, neutral background or virtual background</li>
                  <li><strong>Internet:</strong> Test your connection beforehand to avoid interruptions</li>
                </ul>
              </div>
              
              <div className="instruction-section">
                <h4>👔 Professional Appearance</h4>
                <ul>
                  <li><strong>Attire:</strong> Dress professionally as you would for an in-person interview</li>
                  <li><strong>Grooming:</strong> Maintain neat appearance and good personal hygiene</li>
                  <li><strong>Posture:</strong> Sit up straight with shoulders back to project confidence</li>
                </ul>
              </div>
              
              <div className="instruction-section">
                <h4>🗣️ Communication Tips</h4>
                <ul>
                  <li><strong>Eye Contact:</strong> Look directly at the camera, not the screen</li>
                  <li><strong>Speech:</strong> Speak clearly and at a moderate pace</li>
                  <li><strong>Tone:</strong> Use a confident, enthusiastic, and professional tone</li>
                  <li><strong>Gestures:</strong> Use natural hand movements to emphasize points</li>
                </ul>
              </div>
              
              <div className="instruction-section">
                 <h4>⏰ During the Interview</h4>
                 <ul>
                   <li><strong>Preparation Time:</strong> Use the 20 seconds to organize your thoughts while viewing the question</li>
                   <li><strong>Recording Time:</strong> You have up to 60 seconds to record your answer</li>
                   <li><strong>Finish Early:</strong> Click "Finish Recording" button if you complete your answer before time runs out</li>
                   <li><strong>Structure:</strong> Follow STAR method (Situation, Task, Action, Result) for behavioral questions</li>
                   <li><strong>Confidence:</strong> Take a deep breath and speak with conviction</li>
                   <li><strong>Authenticity:</strong> Be genuine and let your personality shine through</li>
                 </ul>
               </div>
               
               <div className="instruction-section">
                 <h4>🤖 AI Analysis Process</h4>
                 <ul>
                  <li><strong>Non-contextual Analysis:</strong> Comprehensive evaluation of confidence, clarity, speech rate, eye contact, body language, voice tone, and key points from your recording</li>
                  <li><strong>Contextual Analysis:</strong> Detailed assessment of answer relevancy with improvement recommendations and sample answer templates for both fresher and experienced candidates</li>
                  <li><strong>Processing Time:</strong> Analysis typically takes 2-3 minutes after recording</li>
                 </ul>
               </div>
              
              <div className="motivation-section">
                <h4>💪 You've Got This!</h4>
                <p>
                  Remember, every expert was once a beginner. This practice session is your opportunity to 
                  shine and improve. Trust in your preparation, believe in your abilities, and approach 
                  this interview with confidence. You have unique experiences and perspectives that make 
                  you valuable. Take a deep breath, smile, and show them the amazing professional you are!
                </p>
              </div>
            </div>
            <div className="modal-footer">
              <button 
                className="btn-primary" 
                onClick={() => setShowInstructions(false)}
              >
                Got it, let's start!
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Interview;