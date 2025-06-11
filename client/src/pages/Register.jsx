import { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import '../styles/register.css';

const Register = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    api_key: '',
    index_id: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  const { register, isAuthenticated } = useAuth();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage('');
    setSuccessMessage('');

    try {
      const result = await register(formData);
      if (result.success) {
        if (result.needsConfirmation) {
          setSuccessMessage(result.message || 'Registration successful! Please check your email to confirm your account.');
        } else {
          setSuccessMessage('Registration successful! You can now login.');
        }
        setFormData({
          email: '',
          password: '',
          api_key: '',
          index_id: ''
        });
      } else {
        setErrorMessage(result.error || 'Registration failed. Please try again.');
      }
    } catch (error) {
      setErrorMessage('An unexpected error occurred. Please try again.');
      console.error('Registration error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="form-wrapper">
      <div className="form-card">
        <h2 className="form-title">Register for MockPrep AI</h2>

        {errorMessage && (
          <div className="form-alert error-alert">
            {errorMessage}
          </div>
        )}

        {successMessage && (
          <div className="form-alert success-alert">
            {successMessage}
          </div>
        )}

        <form onSubmit={handleSubmit} className="form">
          <div className="form-group">
            <label htmlFor="email" className="form-label">Email</label>
            <input
              id="email"
              name="email"
              type="email"
              value={formData.email}
              onChange={handleChange}
              className="form-input"
              required
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="password" className="form-label">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              value={formData.password}
              onChange={handleChange}
              className="form-input"
              required
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="api_key" className="form-label">TwelveLabs API Key</label>
            <input
              id="api_key"
              name="api_key"
              type="text"
              value={formData.api_key}
              onChange={handleChange}
              className="form-input"
              required
              disabled={isLoading}
            />
          </div>

          <div className="form-group">
            <label htmlFor="index_id" className="form-label">TwelveLabs Index ID</label>
            <input
              id="index_id"
              name="index_id"
              type="text"
              value={formData.index_id}
              onChange={handleChange}
              className="form-input"
              required
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            className={`form-button ${isLoading ? 'disabled-button' : ''}`}
            disabled={isLoading}
          >
            {isLoading ? 'Registering...' : 'Register'}
          </button>
        </form>

        <div className="form-footer">
          <p>
            Already have an account?{' '}
            <Link to="/login" className="link">
              Login here
            </Link>
          </p>
        </div>

        <div className="info-box">
          <h3 className="info-title">How to Obtain Your TwelveLabs API Key and Index ID</h3>
          <ol className="info-list">
            <li>Visit <a href="https://twelvelabs.io" target="_blank" rel="noopener noreferrer" className="link">https://twelvelabs.io</a></li>
            <li>Log in or register for a TwelveLabs account</li>
            <li>Go to the API Keys section in your settings or console</li>
            <li>Create a new API key and copy it</li>
            <li>Go to the Indexes section</li>
            <li>Create a new index and copy the Index ID</li>
          </ol>
        </div>
      </div>
    </div>
  );
};

export default Register;
