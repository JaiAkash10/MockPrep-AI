import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import '../../styles/nav.css';

const Nav = () => {
  const { logout } = useAuth();

  return (
    <nav className="nav-wrapper">
      <div className="nav-container">
        <div className="nav-branding">
          <h1 className="nav-title">MockPrep AI</h1>
          <p className="nav-subtitle">Enhance Your Interview Skills with AI Powered Feedback</p>
        </div>
        <div className="nav-links">
          <Link to="/dashboard" className="nav-link">
            Dashboard
          </Link>
          <Link to="/profile" className="nav-link">
            Profile
          </Link>
          <Link to="/history" className="nav-link">
            History
          </Link>
          <Link to="/pricing" className="nav-link">
            Pricing
          </Link>
          <button onClick={logout} className="nav-link logout-link">
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Nav;
