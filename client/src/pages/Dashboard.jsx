import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import api from '../api';
import '../styles/dashboard.css';

const Dashboard = () => {
  const { currentUser } = useAuth();
  const [recentInterviews, setRecentInterviews] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchRecentInterviews = async () => {
      try {
        setIsLoading(true);
        // const response = await api.get('/history');
        // setRecentInterviews(response.data.interviews);
        setRecentInterviews([
          { id: 1, question: 'Tell me about yourself', date: '2023-11-15', score: 7.5 },
          { id: 2, question: 'What are your greatest strengths', date: '2023-11-14', score: 8.2 },
        ]);
      } catch (err) {
        console.error('Error fetching recent interviews:', err);
        setError('Failed to load your recent interviews');
      } finally {
        setIsLoading(false);
      }
    };

    fetchRecentInterviews();
  }, []);

  return (
      <div className="dashboard-container">
        <section className="dashboard-section">
          <h2 className="section-title">Welcome, {currentUser?.email || 'User'}!</h2>
          <p className="section-description">Ready to improve your interview skills? Start a mock interview or explore your past performance.</p>
          
          <div className="action-buttons">
            <Link to="/interview" className="btn primary-btn">
              Start New Interview
            </Link>
            <Link to="/resume-analysis" className="btn secondary-btn">
              Analyze Resume
            </Link>
            <Link to="/history" className="btn secondary-btn">
              View All History
            </Link>
          </div>
        </section>

        <section className="dashboard-section">
          <h2 className="section-title">Recent Interviews</h2>
          
          {isLoading ? (
            <div className="loader-wrapper">
              <div className="loader"></div>
            </div>
          ) : error ? (
            <div className="error-box">
              {error}
            </div>
          ) : recentInterviews.length > 0 ? (
            <div className="table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Question</th>
                    <th>Date</th>
                    <th>Score</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {recentInterviews.map((interview) => (
                    <tr key={interview.id}>
                      <td>{interview.question}</td>
                      <td>{new Date(interview.date).toLocaleDateString()}</td>
                      <td>
                        <span className={`score-badge ${interview.score >= 7 ? 'score-high' : 'score-medium'}`}>
                          {interview.score}/10
                        </span>
                      </td>
                      <td>
                        <Link to={`/history/${interview.id}`} className="link">
                          View Details
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="no-data-msg">No interview history yet. Start your first interview!</p>
          )}
        </section>

        <section className="dashboard-section">
          <h2 className="section-title">Subscription Status</h2>
          <div className="info-box">
            <p className="info-title">You are currently on the Free Plan</p>
            <p className="info-subtext">Upgrade to unlock unlimited interviews and advanced features</p>
          </div>
          <Link to="/pricing" className="btn primary-btn">
            View Pricing Plans
          </Link>
        </section>
      </div>
  );
};

export default Dashboard;
