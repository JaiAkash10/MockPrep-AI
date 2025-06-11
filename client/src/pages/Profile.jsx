import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import api from '../api';
import '../styles/profile.css';

const Profile = () => {
  const { currentUser, updateUserProfile } = useAuth();
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    jobTitle: '',
    industry: '',
    experience: '',
    password: '',
    confirmPassword: ''
  });
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    if (currentUser) {
      setFormData({
        name: currentUser.name || '',
        email: currentUser.email || '',
        jobTitle: currentUser.jobTitle || '',
        industry: currentUser.industry || '',
        experience: currentUser.experience || '',
        password: '',
        confirmPassword: ''
      });
    }
  }, [currentUser]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (formData.password && formData.password !== formData.confirmPassword) {
      setMessage({ type: 'error', text: 'Passwords do not match' });
      return;
    }

    try {
      setIsLoading(true);
      setMessage({ type: '', text: '' });

      const dataToUpdate = { ...formData };
      if (!dataToUpdate.password) delete dataToUpdate.password;
      delete dataToUpdate.confirmPassword;

      await api.put('/profile', dataToUpdate);

      if (updateUserProfile) {
        updateUserProfile({
          name: formData.name,
          email: formData.email,
          jobTitle: formData.jobTitle,
          industry: formData.industry,
          experience: formData.experience
        });
      }

      setMessage({ type: 'success', text: 'Profile updated successfully' });
      setIsEditing(false);
    } catch (err) {
      console.error('Error updating profile:', err);
      setMessage({
        type: 'error',
        text: err.response?.data?.message || 'Failed to update profile'
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="page-container">
      <section className="box">
        <h2 className="title">Your Profile</h2>

        {message.text && (
          <div className={`alert ${message.type === 'error' ? 'alert-error' : 'alert-success'}`}>
            {message.text}
          </div>
        )}

        <form onSubmit={handleSubmit} className="form">
          <div className="form-grid">
            <div>
              <label htmlFor="name" className="label">Full Name</label>
              <input
                type="text"
                id="name"
                name="name"
                value={formData.name}
                onChange={handleChange}
                disabled={!isEditing}
                className="input"
              />
            </div>

            <div>
              <label htmlFor="email" className="label">Email Address</label>
              <input
                type="email"
                id="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                disabled={!isEditing}
                className="input"
              />
            </div>

            <div>
              <label htmlFor="jobTitle" className="label">Job Title</label>
              <input
                type="text"
                id="jobTitle"
                name="jobTitle"
                value={formData.jobTitle}
                onChange={handleChange}
                disabled={!isEditing}
                className="input"
                placeholder="e.g. Software Engineer"
              />
            </div>

            <div>
              <label htmlFor="industry" className="label">Industry</label>
              <input
                type="text"
                id="industry"
                name="industry"
                value={formData.industry}
                onChange={handleChange}
                disabled={!isEditing}
                className="input"
                placeholder="e.g. Technology"
              />
            </div>

            <div>
              <label htmlFor="experience" className="label">Years of Experience</label>
              <input
                type="text"
                id="experience"
                name="experience"
                value={formData.experience}
                onChange={handleChange}
                disabled={!isEditing}
                className="input"
                placeholder="e.g. 5"
              />
            </div>
          </div>

          {isEditing && (
            <div className="password-section">
              <h3 className="subtitle">Change Password</h3>
              <p className="note">Leave blank to keep your current password</p>

              <div className="form-grid">
                <div>
                  <label htmlFor="password" className="label">New Password</label>
                  <input
                    type="password"
                    id="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    className="input"
                  />
                </div>

                <div>
                  <label htmlFor="confirmPassword" className="label">Confirm New Password</label>
                  <input
                    type="password"
                    id="confirmPassword"
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    className="input"
                  />
                </div>
              </div>
            </div>
          )}

          <div className="action-row">
            {isEditing ? (
              <>
                <button
                  type="button"
                  onClick={() => setIsEditing(false)}
                  className="btn btn-secondary"
                  disabled={isLoading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <span className="loading-text">
                      <svg className="spinner" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="circle" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="path" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.37 0 0 5.37 0 12h4zm2 5.29A7.96 7.96 0 014 12H0c0 3.04 1.13 5.82 3 7.94l3-2.65z"></path>
                      </svg>
                      Saving...
                    </span>
                  ) : 'Save Changes'}
                </button>
              </>
            ) : (
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="btn btn-primary"
              >
                Edit Profile
              </button>
            )}
          </div>
        </form>
      </section>

      <section className="box">
        <h2 className="title">Subscription</h2>

        <div className="info-box">
          <p className="label">Current Plan: <span className="highlight">Free Trial</span></p>
          <p className="small-text">Upgrade to unlock unlimited interviews and advanced features</p>
        </div>

        <button className="btn btn-primary">
          Upgrade Subscription
        </button>
      </section>
    </div>
  );
};

export default Profile;
