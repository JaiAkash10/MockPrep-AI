import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { useAuth } from '../hooks/useAuth';
import api from '../api';
import '../styles/resumeAnalysis.css';

const ResumeAnalysis = () => {
  const navigate = useNavigate();
  const { currentUser, loading } = useAuth();
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [jobDescription, setJobDescription] = useState('');
  const [aiGeneratedResume, setAiGeneratedResume] = useState(null);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [showAnalysisDetails, setShowAnalysisDetails] = useState(false);
  const chatContainerRef = useRef(null);

  // Check authentication on component mount
  useEffect(() => {
    // If not loading and no user, we'll be redirected by ProtectedRoute
    if (!loading && !currentUser) {
      console.log('No authenticated user, will be redirected by ProtectedRoute');
    }
  }, [loading, currentUser]);

  const validateFile = (file) => {
    const allowedTypes = [
      'application/pdf',
      'application/msword',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ];
    
    const allowedExtensions = ['.pdf', '.doc', '.docx'];
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    
    // Check file type and extension
    if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(fileExtension)) {
      return {
        isValid: false,
        error: 'Please upload a PDF, DOC, or DOCX file only.'
      };
    }
    
    // Check file size (limit to 10MB)
    if (file.size > 10 * 1024 * 1024) {
      return {
        isValid: false,
        error: 'File size must be less than 10MB.'
      };
    }
    
    // Check if file is not empty
    if (file.size === 0) {
      return {
        isValid: false,
        error: 'Please upload a non-empty file.'
      };
    }
    
    return { isValid: true };
  };

  // Updated dropzone with validation
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxFiles: 1,
    onDrop: acceptedFiles => {
      if (acceptedFiles.length > 0) {
        const selectedFile = acceptedFiles[0];
        
        // Validate the file
        const validation = validateFile(selectedFile);
        
        if (!validation.isValid) {
          setError(validation.error);
          return;
        }
        
        setFile(selectedFile);
        setError(null);
        console.log('File accepted:', selectedFile.name, 'Type:', selectedFile.type);
      }
    },
    onDropRejected: (rejectedFiles) => {
      if (rejectedFiles.length > 0) {
        const rejection = rejectedFiles[0];
        if (rejection.errors.some(error => error.code === 'file-invalid-type')) {
          setError('Invalid file format. Please upload a PDF, DOC, or DOCX file.');
        } else if (rejection.errors.some(error => error.code === 'file-too-large')) {
          setError('File is too large. Please upload a file smaller than 10MB.');
        } else {
          setError('File upload failed. Please try again.');
        }
      }
    }
  });

  const handleJobDescriptionChange = (e) => {
    setJobDescription(e.target.value);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!file) {
      setError('Please upload a resume file');
      return;
    }

    // Double-check file validation before upload
    const validation = validateFile(file);
    if (!validation.isValid) {
      setError(validation.error);
      return;
    }

    try {
      setIsUploading(true);
      setError(null);

      const formData = new FormData();
      formData.append('resume', file);
      if (jobDescription.trim()) {
        formData.append('job_description', jobDescription.trim());
      }

      console.log('Uploading file:', file.name, 'Size:', file.size, 'Type:', file.type);

      // Upload the resume file and job description
      const uploadResponse = await api.post('/api/resume/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        timeout: 30000 // 30 seconds timeout
      });

      console.log('Upload successful, resumeId:', uploadResponse.data.resumeId);
      
      setIsUploading(false);
      setIsAnalyzing(true);
      
      try {
        // Get the analysis from the backend
        const analysisResponse = await api.get(`/api/resume/analyze/${uploadResponse.data.resumeId}`, {
          timeout: 60000 // 60 seconds timeout for analysis
        });
        
        console.log('Analysis completed:', analysisResponse.data.analysis?.score);
        
        setAnalysis(analysisResponse.data.analysis);
        setAiGeneratedResume(analysisResponse.data.aiGeneratedResume);
        setIsAnalyzing(false);
        
        // Add initial chatbot message
        setChatMessages([
          {
            sender: 'ai',
            text: `I've analyzed your resume and given it a score of ${analysisResponse.data.analysis?.score || 'N/A'}/100. Ask me anything about improving it or making specific changes.`
          }
        ]);
        
      } catch (analysisErr) {
        console.error('Error analyzing resume:', analysisErr);
        // Check if this is an authentication error
        if (analysisErr.response?.status === 401) {
          setError('Your session has expired. Please log in again.');
        } else {
          const errorMessage = analysisErr.response?.data?.error || 
                              analysisErr.message || 
                              'Failed to analyze resume. Please try again.';
          setError(errorMessage);
        }
        setIsAnalyzing(false);
      }
      
    } catch (uploadErr) {
      console.error('Error uploading resume:', uploadErr);
      // Check if this is an authentication error
      if (uploadErr.response?.status === 401) {
        setError('Your session has expired. Please log in again.');
      } else {
        const errorMessage = uploadErr.response?.data?.error || 
                            uploadErr.message || 
                            'Failed to upload resume. Please try again.';
        setError(errorMessage);
      }
      setIsUploading(false);
      setIsAnalyzing(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    setJobDescription('');
    setAnalysis(null);
    setAiGeneratedResume(null);
    setChatMessages([]);
    setError(null);
  };

  const handleChatSubmit = async (e) => {
    e.preventDefault();
    if (!chatInput.trim()) return;

    // Add user message to chat
    const userMessage = { sender: 'user', text: chatInput };
    setChatMessages(prev => [...prev, userMessage]);
    setChatInput('');
    setIsChatLoading(true);

    // Scroll to bottom of chat
    setTimeout(() => {
      if (chatContainerRef.current) {
        chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
      }
    }, 100);

    try {
      // Call the backend API to get AI response using Gemini
      const response = await api.post('/api/resume/chat', {
        resumeId: analysis.resumeId,
        message: chatInput
      });

      setChatMessages(prev => [...prev, { sender: 'ai', text: response.data.reply }]);
      setIsChatLoading(false);
      
      // Scroll to bottom again after response
      setTimeout(() => {
        if (chatContainerRef.current) {
          chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
        }
      }, 100);
    } catch (err) {
      console.error('Error getting AI response:', err);
      setChatMessages(prev => [...prev, { 
        sender: 'ai', 
        text: 'Sorry, I encountered an error processing your request. Please try again.'
      }]);
      setIsChatLoading(false);
    }
  };

  const generateAIResponse = (userInput) => {
    const input = userInput.toLowerCase();
    
    if (input.includes('improve') && input.includes('summary')) {
      return 'To improve your professional summary, try highlighting your most impressive achievements and the unique value you bring. For example: "Innovative Senior Software Engineer with 6+ years of experience delivering high-impact web applications that drive business growth. Reduced system downtime by 40% and increased user engagement by 45% through architectural improvements and user-centered design."';
    } else if (input.includes('keywords') || input.includes('ats')) {
      return 'To improve keyword optimization for ATS systems, analyze the job descriptions you are targeting and incorporate relevant technical skills, methodologies, and industry terms. Place these keywords naturally throughout your resume, especially in your skills section and job descriptions. For your resume, consider adding more emphasis on: CI/CD, Cloud platforms (AWS/Azure), Performance optimization, and Microservices architecture.';
    } else if (input.includes('format') || input.includes('layout')) {
      return 'For optimal resume formatting: 1) Use a clean, professional template with consistent spacing, 2) Ensure section headers stand out with bold formatting, 3) Use bullet points for achievements rather than paragraphs, 4) Keep to 1-2 pages maximum, 5) Use a professional font like Arial, Calibri or Garamond at 10-12pt size, and 6) Save as a PDF to maintain formatting across devices.';
    } else if (input.includes('achievements') || input.includes('results')) {
      return 'To strengthen your achievements, use the PAR formula: Problem, Action, Result. For example, instead of "Developed a customer portal," write "Developed a customer-facing portal that resolved user navigation issues, resulting in 45% increased engagement and 30% fewer support tickets." Always quantify results with percentages, numbers, or time frames when possible.';
    } else {
      return 'I can help you improve your resume by suggesting changes to your professional summary, skills section, work achievements, formatting, or keyword optimization. What specific aspect would you like me to help with?';
    }
  };

  const downloadAIResume = () => {
    const element = document.createElement('a');
    const file = new Blob([aiGeneratedResume], {type: 'text/plain'});
    element.href = URL.createObjectURL(file);
    element.download = 'AI_Generated_Resume.txt';
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="resume-analysis-container">
      <section className="upload-section">
        <h2 className="upload-title">Resume Analysis</h2>
        <p className="section-description">Upload your resume to get AI-powered feedback, suggestions, and an optimized version.</p>

        {!analysis ? (
          <form onSubmit={handleSubmit} className="form">

            <div className="form-group">
              <label className="label">Upload Resume</label>
              <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
                <input {...getInputProps()} />
                {file ? (
                  <div className="file-info">
                    <p className="file-name">{file.name}</p>
                    <p className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                    <button type="button" onClick={(e) => { e.stopPropagation(); setFile(null); }} className="remove-btn">
                      Remove
                    </button>
                  </div>
                ) : isDragActive ? (
                  <p>Drop your resume file here...</p>
                ) : (
                  <p>Drag & drop your resume here, or click to select a file</p>
                )}
              </div>
              <p className="hint">Supported formats: PDF, DOC, DOCX (All formats are fully supported and optimized)</p>
            </div>

            <div className="form-group">
              <label htmlFor="jobDescription" className="label">Job Description (Optional)</label>
              <textarea
                id="jobDescription"
                value={jobDescription}
                onChange={handleJobDescriptionChange}
                rows="4"
                className="job-description-input"
                placeholder="Paste the job description here for a tailored analysis..."
              ></textarea>
              <p className="hint">Adding a job description will help us analyze how well your resume matches the position</p>
            </div>

            {error && <div className="error-box">{error}</div>}

            <div className="form-actions">
              <button type="submit" className="analyze-button" disabled={isUploading || isAnalyzing}>
                {isUploading ? 'Uploading...' : isAnalyzing ? 'Analyzing...' : 'Analyze Resume'}
              </button>
            </div>
          </form>
        ) : (
          <div className="results-container">
            <div className="success-box">Analysis complete! Review the feedback below.</div>

            <div className="results-grid">
              <div className="results-column">
                <div className="result-item score-section">
                  <h3 className="result-title">Resume Score</h3>
                  <div className="score-display">
                    <div className="score-circle">
                      <span className="score-value">{analysis.score}</span>
                      <span className="score-max">/100</span>
                    </div>
                    <div className="score-label">
                      {analysis.score >= 80 ? 'Excellent' : 
                       analysis.score >= 70 ? 'Good' : 
                       analysis.score >= 60 ? 'Average' : 'Needs Improvement'}
                    </div>
                  </div>
                  <p className="score-summary">{analysis.summary}</p>
                  
                  <button 
                    onClick={() => setShowAnalysisDetails(!showAnalysisDetails)}
                    className="view-analysis-button"
                  >
                    {showAnalysisDetails ? 'Hide Analysis' : 'View Analysis'}
                  </button>
                </div>

                {showAnalysisDetails && (
                  <div className="analysis-details-card">
                    <div className="result-item">
                      <h3 className="result-title">Strengths</h3>
                      <ul className="result-list strengths-list">
                        {analysis.strengths.map((strength, i) => (
                          <li key={i} className="strength-item">{strength}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="result-item">
                      <h3 className="result-title">Areas for Improvement</h3>
                      <ul className="result-list improvements-list">
                        {analysis.improvements.map((improvement, i) => (
                          <li key={i} className="improvement-item">{improvement}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="result-item">
                      <h3 className="result-title">Keyword Analysis</h3>
                      <div className="keywords-container">
                        {analysis.keywords.map((keyword, i) => (
                          <span key={i} className="keyword-tag">{keyword}</span>
                        ))}
                      </div>
                    </div>

                    {analysis.job_match && (
                      <div className="result-item job-match-section">
                        <h3 className="result-title">Job Match Analysis</h3>
                        <div className="job-match-score">
                          <div className="match-percentage">{analysis.job_match.score}%</div>
                          <div className="match-label">Match Rate</div>
                        </div>
                        <p className="job-match-summary">{analysis.job_match.summary}</p>

                        <div className="missing-keywords">
                          <h4 className="subsection-title">Missing Keywords</h4>
                          <div className="keywords-container">
                            {analysis.job_match.missing_keywords.map((keyword, i) => (
                              <span key={i} className="keyword-tag missing">{keyword}</span>
                            ))}
                          </div>
                        </div>

                        <div className="job-recommendations">
                          <h4 className="subsection-title">Recommendations</h4>
                          <ul className="result-list recommendation-list">
                            {analysis.job_match.recommendations.map((rec, i) => (
                              <li key={i} className="recommendation-item">{rec}</li>
                            ))}
                          </ul>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="results-column">
                <div className="result-item ai-resume-section">
                  <h3 className="result-title">AI-Generated Resume</h3>
                  <p className="ai-resume-description">
                    Based on your current resume, we've generated an optimized version that highlights your strengths and addresses the improvement areas.
                  </p>
                  <div className="ai-resume-preview">
                    <pre>{aiGeneratedResume}</pre>
                  </div>
                  <button onClick={downloadAIResume} className="download-button">
                    Download AI Resume
                  </button>
                </div>

                <div className="result-item chat-section">
                  <h3 className="result-title">Resume Assistant</h3>
                  <p className="chat-description">
                    Ask questions about improving your resume or request specific changes.
                  </p>
                  <div className="chat-container" ref={chatContainerRef}>
                    {chatMessages.map((msg, i) => (
                      <div key={i} className={`chat-message ${msg.sender}`}>
                        <div className="message-content">{msg.text}</div>
                      </div>
                    ))}
                    {isChatLoading && (
                      <div className="chat-message ai loading">
                        <div className="typing-indicator">
                          <span></span><span></span><span></span>
                        </div>
                      </div>
                    )}
                  </div>
                  <form onSubmit={handleChatSubmit} className="chat-input-form">
                    <input
                      type="text"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      placeholder="Ask about improving your resume..."
                      className="chat-input"
                      disabled={isChatLoading}
                    />
                    <button 
                      type="submit" 
                      className="chat-submit-button"
                      disabled={isChatLoading || !chatInput.trim()}
                    >
                      Send
                    </button>
                  </form>
                </div>
              </div>
            </div>

            <div className="form-actions">
              <button onClick={resetForm} className="secondary-button">Analyze Another Resume</button>
              <button onClick={() => navigate('/dashboard')} className="primary-button">Back to Dashboard</button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
};

export default ResumeAnalysis;
