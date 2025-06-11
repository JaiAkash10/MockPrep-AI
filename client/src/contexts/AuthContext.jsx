import React, { createContext, useState, useContext, useEffect, useCallback } from 'react';
import authService from '../services/authService';
import { supabaseAuth } from '../lib/supabase';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isInitialized, setIsInitialized] = useState(false);
  
  // Helper function to clear auth data
  const clearAuthData = useCallback(() => {
    // Clear any legacy localStorage data
    localStorage.removeItem('token');
    localStorage.removeItem('tokenExpiry');
    localStorage.removeItem('userData');
    setCurrentUser(null);
    setError(null);
  }, []);

  // Function to handle successful authentication
  const handleAuthSuccess = useCallback(async (session) => {
    try {
      if (!session?.user) {
        clearAuthData();
        return;
      }

      // Get user data from your auth service
      const { success, user } = await authService.getCurrentUser();
      
      if (success && user) {
        setCurrentUser(user);
      } else {
        console.warn('Failed to get user data despite valid session');
        clearAuthData();
      }
    } catch (err) {
      console.error('Error handling auth success:', err);
      clearAuthData();
    }
  }, [clearAuthData]);

  // Check if user is already logged in on mount
  useEffect(() => {
    let isMounted = true;

    const initializeAuth = async () => {
      try {
        setLoading(true);
        
        // Get current session - Fix: use getCurrentSession() instead of getSession()
        const { data: sessionData, error: sessionError } = await supabaseAuth.getCurrentSession();
        
        if (sessionError) {
          console.error('Session error:', sessionError);
          if (isMounted) {
            clearAuthData();
            setIsInitialized(true);
            setLoading(false);
          }
          return;
        }

        if (!sessionData?.session) {
          // No active session
          if (isMounted) {
            clearAuthData();
            setIsInitialized(true);
            setLoading(false);
          }
          return;
        }

        // Handle existing session
        await handleAuthSuccess(sessionData.session);
        
      } catch (err) {
        console.error('Auth initialization error:', err);
        if (isMounted) {
          clearAuthData();
        }
      } finally {
        if (isMounted) {
          setIsInitialized(true);
          setLoading(false);
        }
      }
    };

    initializeAuth();

    return () => {
      isMounted = false;
    };
  }, [handleAuthSuccess, clearAuthData]);

  // Set up auth state listener after initialization
  useEffect(() => {
    if (!isInitialized) return;

    console.log('Setting up auth state listener');

    const { data: { subscription } } = supabaseAuth.onAuthStateChange(async (event, session) => {
      console.log('Auth state changed:', event, session ? 'Session exists' : 'No session');
      
      try {
        if (event === 'SIGNED_IN' && session) {
          setLoading(true);
          await handleAuthSuccess(session);
        } else if (event === 'SIGNED_OUT' || event === 'TOKEN_REFRESHED' && !session) {
          clearAuthData();
        } else if (event === 'TOKEN_REFRESHED' && session) {
          // Token refreshed successfully, update user data if needed
          await handleAuthSuccess(session);
        }
      } catch (err) {
        console.error('Auth state change error:', err);
        clearAuthData();
      } finally {
        setLoading(false);
      }
    });

    return () => {
      console.log('Cleaning up auth state listener');
      subscription?.unsubscribe();
    };
  }, [isInitialized, handleAuthSuccess, clearAuthData]);

  // Login function
  const login = async (email, password) => {
    let loginResult = null; // Fix: Define result variable outside try block
    try {
      setError(null);
      setLoading(true);
      
      console.log('Attempting login for:', email);
      loginResult = await authService.signIn(email, password);
      
      if (loginResult.success) {
        // Don't set user here - let the auth state change handler do it
        // This prevents race conditions
        return { success: true };
      } else {
        setError(loginResult.error);
        return { success: false, error: loginResult.error };
      }
    } catch (err) {
      const errorMessage = err.message || 'Login failed';
      console.error('Login error:', err);
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      // Don't set loading to false here if login was successful
      // Let the auth state change handler manage loading state
      if (!loginResult?.success) {
        setLoading(false);
      }
    }
  };
  
  // Register function
  const register = async (userData) => {
    try {
      setError(null);
      setLoading(true);
      
      console.log('Attempting registration for:', userData.email);
      const result = await authService.signUp(userData);
      
      if (result.success) {
        // For Supabase, user might need email confirmation
        if (result.data.user && !result.data.user.email_confirmed_at) {
          return { 
            success: true, 
            needsConfirmation: true,
            message: 'Please check your email to confirm your account'
          };
        }
        
        // Don't set user here - let the auth state change handler do it
        return { success: true };
      } else {
        setError(result.error);
        return { success: false, error: result.error };
      }
    } catch (err) {
      const errorMessage = err.message || 'Registration failed';
      console.error('Registration error:', err);
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      if (!result?.success) {
        setLoading(false);
      }
    }
  };

  // Logout function
  const logout = async () => {
    try {
      setLoading(true);
      console.log('Attempting logout');
      
      await authService.signOut();
      // Don't call clearAuthData here - let the auth state change handler do it
      
    } catch (err) {
      console.error('Logout error:', err);
      // Still clear local data even if Supabase logout fails
      clearAuthData();
    } finally {
      setLoading(false);
    }
  };
  
  // Update profile function
  const updateProfile = async (profileData) => {
    try {
      setError(null);
      setLoading(true);
      
      const result = await authService.updateProfile(profileData);
      
      if (result.success) {
        const updatedUser = {
          ...currentUser,
          ...result.data.user,
          profile: result.data.profile
        };
        setCurrentUser(updatedUser);
        return { success: true, user: updatedUser };
      } else {
        setError(result.error);
        return { success: false, error: result.error };
      }
    } catch (err) {
      const errorMessage = err.message || 'Profile update failed';
      console.error('Profile update error:', err);
      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  // Function to manually refresh auth state
  const refreshAuth = async () => {
    try {
      setLoading(true);
      const { data: sessionData } = await supabaseAuth.getSession();
      
      if (sessionData?.session) {
        await handleAuthSuccess(sessionData.session);
      } else {
        clearAuthData();
      }
    } catch (err) {
      console.error('Auth refresh error:', err);
      clearAuthData();
    } finally {
      setLoading(false);
    }
  };
  
  // Check if user is authenticated
  const isAuthenticated = !!currentUser;
  
  // Check if user is admin
  const isAdmin = currentUser?.role === 'admin';
  
  const value = {
    currentUser,
    loading,
    error,
    isInitialized,
    login,
    register,
    logout,
    updateProfile,
    refreshAuth,
    isAuthenticated,
    isAdmin,
    clearError: () => setError(null)
  };
  
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};