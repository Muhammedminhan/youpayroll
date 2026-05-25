import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { GoogleLogin } from '@react-oauth/google';
import { jwtDecode } from "jwt-decode";
import logoImg from '../assets/logo.jpg';
import { ROUTES } from '../constants/routes';
import { MEDIA_BASE_URL } from '../api';

const Login = () => {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [loginError, setLoginError] = useState(location.state?.error || '');

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    if (location.state?.error) {
      setLoginError(location.state.error);
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location.pathname, location.state?.error, navigate]);

  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      const decoded = jwtDecode(credentialResponse.credential);
      const result = await login(decoded.email, credentialResponse.credential);
      if (result.success) {
        navigate(ROUTES.DASHBOARD);
      } else {
        navigate(ROUTES.LOGIN, { state: { error: result.error || 'Your account is not registered or authentication failed.' } });
      }
    } catch (error) {
      console.error('Login error:', error);
      navigate(ROUTES.LOGIN, { state: { error: 'An error occurred during sign-in. Please try again.' } });
    }
  };

  const handleGoogleError = () => {
    console.error('Google Login Metadata Error: Check authorized origins in GCP Console.');
    navigate(ROUTES.LOGIN, { state: { error: 'Sign-in failed. Please ensure your account is authorized.' } });
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="brand-header">
          <img 
            src={logoImg} 
            alt="YOUPayroll Logo" 
            className="logo" 
            onError={(e) => {
              // Fallback to backend media if asset fails
              e.target.src = `${MEDIA_BASE_URL}/media/branding/logo.jpg`;
            }}
          />
          <p className="welcome-text">Welcome to YOUPayroll</p>
          <p className="subtitle">Please sign in with your Google account to continue</p>
        </div>

        {loginError && (
          <div className="error-message-box" style={{ color: '#ef4444', backgroundColor: '#fee2e2', padding: '1rem', borderRadius: '12px', marginBottom: '1.5rem', fontSize: '0.9rem', fontWeight: '600' }}>
            {loginError}
          </div>
        )}

        <div className="social-login-section">
          <div className="google-login-wrapper" style={{ display: 'flex', justifyContent: 'center' }}>
            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={handleGoogleError}
              useOneTap
              theme="outline"
              size="large"
              width="320"
              shape="pill"
            />
          </div>
        </div>

        <div className="login-footer">
          <p>By signing in, you agree to our Terms of Service</p>
          <div className="help-center-link">
            <span>Need Help? </span>
            <a href="https://yougotagift.atlassian.net/servicedesk/customer/portal/14" target="_blank" rel="noopener noreferrer">Visit our Support Center</a>
          </div>
        </div>
      </div>

      <style>{`
        .login-container {
          height: 100vh;
          width: 100vw;
          display: flex;
          align-items: center;
          justify-content: center;
          background: var(--bg-color);
        }

        .login-card {
          background: var(--card-bg);
          padding: 3.5rem 2.5rem;
          border-radius: 2rem;
          box-shadow: 0 20px 25px -5px var(--shadow-color), 0 10px 10px -5px var(--shadow-color);
          width: 100%;
          max-width: 420px;
          text-align: center;
          border: 1px solid var(--border-color);
          backdrop-filter: blur(10px);
          transition: background-color 0.3s ease;
        }

        .brand-header {
          margin-bottom: 2.5rem;
        }

        .logo {
          width: 120px;
          height: auto;
          margin-bottom: 2rem;
          transition: filter 0.3s ease;
        }

        body.dark-mode .logo {
          filter: invert(1) hue-rotate(180deg) contrast(1.4) saturate(1.2) brightness(1.1);
          mix-blend-mode: screen;
        }

        .welcome-text {
          font-size: 1.5rem;
          font-weight: 800;
          color: var(--text-primary);
          margin-bottom: 0.5rem;
        }

        .subtitle {
          font-size: 0.95rem;
          color: var(--text-secondary);
          line-height: 1.5;
        }

        .social-login-section {
            margin: 2rem 0;
        }
        
        .login-footer {
            margin-top: 2rem;
            font-size: 0.8rem;
            color: var(--text-secondary);
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .help-center-link span {
            color: var(--text-secondary);
        }

        .help-center-link a {
            color: #B800C4;
            font-weight: 700;
            text-decoration: none;
            transition: all 0.2s;
        }

        .help-center-link a:hover {
            text-decoration: underline;
            opacity: 0.8;
        }
      `}</style>
    </div>
  );
};

export default Login;
