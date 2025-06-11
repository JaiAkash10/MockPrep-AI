import { Outlet } from 'react-router-dom';
import Nav from './Nav';
import '../../styles/index.css'

const Layout = () => {
  return (
    <div className="layout-wrapper">
      <div className="layout-container">
        <Nav />

        <main className="main-content">
          <Outlet />
        </main>

        <footer className="footer">
          <p>© {new Date().getFullYear()} MockPrep AI. All rights reserved.</p>
        </footer>
      </div>
    </div>
  );
};

export default Layout;
