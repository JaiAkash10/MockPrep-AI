import { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import api from '../api';

const Results = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [results, setResults] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const interviewId = location.state?.interviewId || new URLSearchParams(location.search).get('id');

  useEffect(() => {
    if (!interviewId) {
      navigate('/dashboard');
      return;
    }

    const fetchResults = async () => {
      try {
        setIsLoading(true);
        const response = await api.get(`/results/${interviewId}`);
        setResults(response.data);
      } catch (err) {
        console.error('Error fetching results:', err);
        setError('Failed to load interview results. Please try again.');
      } finally {
        setIsLoading(false);
      }
    };

    fetchResults();
  }, [interviewId, navigate]);

  if (isLoading) {
    return (
      <div className="loading-container">
        <div className="spinner"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card">
        <div className="error-message">{error}</div>
        <button 
          onClick={() => navigate('/dashboard')} 
          className="btn-primary"
        >
          Return to Dashboard
        </button>
      </div>
    );
  }

  return (
    <div className="results-page">
      <section className="card">
        <h2 className="section-title">Interview Results</h2>
        
        {results && (
          <div className="results-section">
            <div className="result-block">
              <h3 className="block-title">Question</h3>
              <p className="block-content">{results.question}</p>
            </div>
            
            <div className="result-block">
              <h3 className="block-title">Overall Score</h3>
              <div className="score-display">
                <div className="score-value">{results.score.toFixed(1)}</div>
                <div className="score-out-of">/10</div>
              </div>
            </div>

            <div className="result-block">
              <h3 className="block-title">Feedback</h3>
              <div className="feedback-section">
                <div className="feedback-block">
                  <h4 className="feedback-title">Content</h4>
                  <p>{results.feedback.content}</p>
                </div>
                
                <div className="feedback-block">
                  <h4 className="feedback-title">Delivery</h4>
                  <p>{results.feedback.delivery}</p>
                </div>
                
                <div className="feedback-block">
                  <h4 className="feedback-title">Body Language</h4>
                  <p>{results.feedback.body_language}</p>
                </div>
              </div>
            </div>

            <div className="result-block">
              <h3 className="block-title">Improvement Tips</h3>
              <ul className="tips-list">
                {results.improvement_tips.map((tip, index) => (
                  <li key={index} className="tip-item">{tip}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
        
        <div className="button-group">
          <button 
            onClick={() => navigate('/interview')} 
            className="btn-primary"
          >
            New Interview
          </button>
          <button 
            onClick={() => navigate('/dashboard')} 
            className="btn-secondary"
          >
            Back to Dashboard
          </button>
        </div>
      </section>
    </div>
  );
};

export default Results;
