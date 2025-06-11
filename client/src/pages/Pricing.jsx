import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import '../styles/pricing.css';

const Pricing = () => {
  const { isAuthenticated } = useAuth();
  const [selectedPlan, setSelectedPlan] = useState('monthly');

  const plans = {
    free: {
      name: 'Free',
      price: '0',
      features: [
        '3 Mock Interviews per month',
        'Basic AI feedback',
        'Interview history',
        'Limited question bank'
      ]
    },
    premium: {
      name: 'Premium',
      monthlyPrice: '19.99',
      yearlyPrice: '199.99',
      features: [
        'Unlimited Mock Interviews',
        'Advanced AI feedback',
        'Detailed performance analytics',
        'Full question bank access',
        'Resume analysis',
        'Custom interview scenarios',
        'Priority support'
      ]
    }
  };

  return (
    <div className="page-container">
      <div className="pricing-container">
        <div className="pricing-header">
          <h1 className="pricing-title">Choose Your Plan</h1>
          <p className="pricing-subtitle">Get the perfect plan for your interview preparation needs</p>
        </div>

        <div className="plan-toggle">
          <button
            className={`toggle-button ${selectedPlan === 'monthly' ? 'active' : ''}`}
            onClick={() => setSelectedPlan('monthly')}
          >
            Monthly
          </button>
          <button
            className={`toggle-button ${selectedPlan === 'yearly' ? 'active' : ''}`}
            onClick={() => setSelectedPlan('yearly')}
          >
            Yearly (Save 17%)
          </button>
        </div>

        <div className="plan-grid">
          {/* Free Plan */}
          <div className="plan-card">
            <h3 className="plan-name">{plans.free.name}</h3>
            <div className="plan-price">
              <span className="price">${plans.free.price}</span>
              <span className="price-period">/month</span>
            </div>
            <ul className="plan-features">
              {plans.free.features.map((feature, index) => (
                <li key={index} className="feature-item">
                  <span className="feature-icon">✔</span>
                  {feature}
                </li>
              ))}
            </ul>
            <Link
              to={isAuthenticated ? '/dashboard' : '/register'}
              className="btn-secondary"
            >
              {isAuthenticated ? 'Continue with Free' : 'Get Started'}
            </Link>
          </div>

          {/* Premium Plan */}
          <div className="plan-card premium-card">
            <div className="plan-badge">Most Popular</div>
            <h3 className="plan-name">{plans.premium.name}</h3>
            <div className="plan-price">
              <span className="price">
                ${selectedPlan === 'monthly' ? plans.premium.monthlyPrice : plans.premium.yearlyPrice}
              </span>
              <span className="price-period">/{selectedPlan === 'monthly' ? 'month' : 'year'}</span>
            </div>
            <ul className="plan-features">
              {plans.premium.features.map((feature, index) => (
                <li key={index} className="feature-item">
                  <span className="feature-icon">✔</span>
                  {feature}
                </li>
              ))}
            </ul>
            <Link
              to={isAuthenticated ? '/dashboard' : '/register'}
              className="btn-primary"
            >
              {isAuthenticated ? 'Upgrade Now' : 'Get Premium'}
            </Link>
          </div>
        </div>

        <div className="pricing-footer">
          <p>
            Questions about our plans?{' '}
            <a href="#" className="contact-link">Contact our support team</a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Pricing;
