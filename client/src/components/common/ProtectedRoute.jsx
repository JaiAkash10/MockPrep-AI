import { Navigate, Outlet } from 'react-router-dom';
import PropTypes from 'prop-types';
import Loader from './Loader';
import { useAuth } from '../../hooks/useAuth';

const ProtectedRoute = ({ children, isAuthenticated }) => {
  const { loading } = useAuth();

  if (loading) {
    return <Loader />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children || <Outlet />;
};

ProtectedRoute.propTypes = {
  children: PropTypes.node,
  isAuthenticated: PropTypes.bool.isRequired
};

export default ProtectedRoute;