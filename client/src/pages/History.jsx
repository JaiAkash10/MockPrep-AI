import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import '../styles/history.css';

const History = () => {
  const [interviews, setInterviews] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    const fetchInterviewHistory = async () => {
      try {
        setIsLoading(true);

        const mockData = [
          {
            id: 1,
            question: 'Tell me about yourself',
            date: '2023-11-15',
            score: 7.5,
            feedback: {
              content: 'Good introduction but could be more concise',
              delivery: 'Confident speaking voice',
              body_language: 'Maintained good eye contact',
            },
          },
          {
            id: 2,
            question: 'What are your greatest strengths',
            date: '2023-11-14',
            score: 8.2,
            feedback: {
              content: 'Well articulated examples',
              delivery: 'Clear and engaging tone',
              body_language: 'Some nervous gestures noted',
            },
          },
          {
            id: 3,
            question: 'How do you handle conflict in the workplace',
            date: '2023-11-10',
            score: 6.8,
            feedback: {
              content: 'Good framework but lacked specific examples',
              delivery: 'Occasional filler words',
              body_language: 'Good posture throughout',
            },
          },
          {
            id: 4,
            question: 'Where do you see yourself in five years',
            date: '2023-11-05',
            score: 7.9,
            feedback: {
              content: 'Clear career goals',
              delivery: 'Enthusiastic tone',
              body_language: 'Positive facial expressions',
            },
          },
        ];

        if (filter === 'week') {
          const oneWeekAgo = new Date();
          oneWeekAgo.setDate(oneWeekAgo.getDate() - 7);
          setInterviews(mockData.filter((i) => new Date(i.date) >= oneWeekAgo));
        } else if (filter === 'month') {
          const oneMonthAgo = new Date();
          oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);
          setInterviews(mockData.filter((i) => new Date(i.date) >= oneMonthAgo));
        } else {
          setInterviews(mockData);
        }
      } catch (err) {
        console.error('Error fetching interview history:', err);
        setError('Failed to load your interview history');
      } finally {
        setIsLoading(false);
      }
    };

    fetchInterviewHistory();
  }, [filter]);

  const handleFilterChange = (newFilter) => {
    setFilter(newFilter);
  };

  const getScoreColor = (score) => {
    if (score >= 8) return 'text-green';
    if (score >= 6) return 'text-yellow';
    return 'text-red';
  };

  return (
      <div className="section">
        <div className="section-header">
          <h2 className="title">Interview History</h2>
          <div className="filter-group">
            <button
              onClick={() => handleFilterChange('all')}
              className={filter === 'all' ? 'btn-primary' : 'btn-secondary'}
            >
              All Time
            </button>
            <button
              onClick={() => handleFilterChange('month')}
              className={filter === 'month' ? 'btn-primary' : 'btn-secondary'}
            >
              Last Month
            </button>
            <button
              onClick={() => handleFilterChange('week')}
              className={filter === 'week' ? 'btn-primary' : 'btn-secondary'}
            >
              Last Week
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="loading">
            <div className="spinner"></div>
          </div>
        ) : error ? (
          <div className="error">{error}</div>
        ) : interviews.length === 0 ? (
          <div className="empty">
            <p>No interviews found for the selected time period.</p>
            <Link to="/interview" className="btn-primary">
              Start Your First Interview
            </Link>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Question</th>
                  <th>Score</th>
                  <th className="text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {interviews.map((interview) => (
                  <tr key={interview.id}>
                    <td>{interview.date}</td>
                    <td className="truncate">{interview.question}</td>
                    <td className={`score ${getScoreColor(interview.score)}`}>
                      {interview.score.toFixed(1)}
                    </td>
                    <td className="text-right">
                      <Link to={`/results?id=${interview.id}`} className="btn-secondary">
                        View Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
  );
};

export default History;
