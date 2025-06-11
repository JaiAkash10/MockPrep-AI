import { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import api from '../../api';

const AdminDashboard = () => {
  const { currentUser } = useAuth();
  const [stats, setStats] = useState({
    totalUsers: 0,
    activeSubscriptions: 0,
    totalInterviews: 0,
    revenueThisMonth: 0
  });
  const [recentUsers, setRecentUsers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setIsLoading(true);
        // const response = await api.get('/admin/dashboard');
        // setStats(response.data.stats);
        // setRecentUsers(response.data.recentUsers);
        
        setStats({
          totalUsers: 150,
          activeSubscriptions: 45,
          totalInterviews: 328,
          revenueThisMonth: 899.99
        });

        setRecentUsers([
          { id: 1, name: 'John Doe', email: 'john@example.com', plan: 'Premium', joinDate: '2023-11-15' },
          { id: 2, name: 'Jane Smith', email: 'jane@example.com', plan: 'Free', joinDate: '2023-11-14' },
        ]);
      } catch (err) {
        console.error('Error fetching dashboard data:', err);
        setError('Failed to load dashboard data');
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  return (
    <div className="dashboard-container">
      <section className="dashboard-header">
        <h2 className="dashboard-title">Admin Dashboard</h2>
        <p className="dashboard-welcome">Welcome back, {currentUser?.name || 'Admin'}!</p>

        {isLoading ? (
          <div className="loader-container">
            <div className="loader-spinner"></div>
          </div>
        ) : error ? (
          <div className="error-message">
            {error}
          </div>
        ) : (
          <div className="stats-grid">
            <div className="stat-card stat-users">
              <h3 className="stat-label">Total Users</h3>
              <p className="stat-value">{stats.totalUsers}</p>
            </div>
            <div className="stat-card stat-subscriptions">
              <h3 className="stat-label">Active Subscriptions</h3>
              <p className="stat-value">{stats.activeSubscriptions}</p>
            </div>
            <div className="stat-card stat-interviews">
              <h3 className="stat-label">Total Interviews</h3>
              <p className="stat-value">{stats.totalInterviews}</p>
            </div>
            <div className="stat-card stat-revenue">
              <h3 className="stat-label">Revenue This Month</h3>
              <p className="stat-value">${stats.revenueThisMonth}</p>
            </div>
          </div>
        )}
      </section>

      <section className="recent-users-card">
        <h2 className="section-title">Recent Users</h2>
        
        {isLoading ? (
          <div className="loader-container">
            <div className="loader-spinner"></div>
          </div>
        ) : error ? (
          <div className="error-message">
            {error}
          </div>
        ) : recentUsers.length > 0 ? (
          <div className="table-container">
            <table className="users-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Plan</th>
                  <th>Join Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {recentUsers.map((user) => (
                  <tr key={user.id}>
                    <td>{user.name}</td>
                    <td>{user.email}</td>
                    <td>
                      <span className={`plan-badge ${user.plan === 'Premium' ? 'badge-premium' : 'badge-free'}`}>
                        {user.plan}
                      </span>
                    </td>
                    <td>{new Date(user.joinDate).toLocaleDateString()}</td>
                    <td>
                      <button className="btn-link">View Details</button>
                      <button className="btn-danger">Suspend</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="no-data-message">No users found.</p>
        )}
      </section>

      <section className="quick-actions-card">
        <h2 className="section-title">Quick Actions</h2>
        <div className="actions-container">
          <button className="btn-primary">Manage Users</button>
          <button className="btn-secondary">View Reports</button>
          <button className="btn-secondary">System Settings</button>
        </div>
      </section>
    </div>
  );
};

export default AdminDashboard;
