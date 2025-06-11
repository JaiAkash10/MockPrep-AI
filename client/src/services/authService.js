import { supabase, supabaseAuth, supabaseDB } from '../lib/supabase'

// Authentication service using Supabase
export const authService = {
  // Sign up a new user
  signUp: async (userData) => {
    try {
      const { email, password, ...additionalData } = userData;
      
      // Sign up with Supabase Auth
      const { data: authData, error: authError } = await supabaseAuth.signUp(
        email, 
        password, 
        additionalData
      )

      if (authError) {
        throw new Error(authError.message)
      }

      // If user is created, add additional profile data to profiles table
      if (authData.user && !authError) {
        const { error: profileError } = await supabaseDB.insert('profiles', { // Changed 'users' to 'profiles'
          id: authData.user.id, // This is the user's UUID from Supabase auth
          // email is typically in auth.users table and linked via id.
          api_key: additionalData.api_key || null,
          index_id: additionalData.index_id || null,
          // created_at and updated_at are generally handled by Supabase table defaults.
        });

        if (profileError) {
          console.error('Error creating user profile:', profileError)
        }
      }

      return {
        success: true,
        data: authData,
        message: 'Registration successful. Please check your email for verification.'
      }
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Registration failed'
      }
    }
  },

  // Sign in user
  signIn: async (email, password) => {
    try {
      const { data, error } = await supabaseAuth.signIn(email, password)

      if (error) {
        throw new Error(error.message)
      }

      // Get user profile data - Use profiles table instead of users
      const { data: userProfile, error: profileError } = await supabaseDB.select(
        'profiles',  // Changed from 'users' to 'profiles'
        '*',
        { id: data.user.id }
      )

      if (profileError) {
        console.error('Error fetching user profile:', profileError)
        // Continue even if profile fetch fails
      }

      return {
        success: true,
        data: {
          user: data.user,
          session: data.session,
          profile: userProfile?.[0] || null
        }
      }
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Login failed'
      }
    }
  },

  // Sign out user
  signOut: async () => {
    try {
      const { error } = await supabaseAuth.signOut()
      
      if (error) {
        throw new Error(error.message)
      }

      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Logout failed'
      }
    }
  },

  // Get current user
  getCurrentUser: async () => {
    try {
      const { data: { user }, error } = await supabaseAuth.getCurrentUser()
      
      if (error) {
        throw new Error(error.message)
      }

      if (!user) {
        return { success: false, user: null }
      }

      // Get user profile - Use profiles table instead of users
      const { data: userProfile, error: profileError } = await supabaseDB.select(
        'profiles',  // Changed from 'users' to 'profiles'
        '*',
        { id: user.id }
      )

      if (profileError) {
        console.error('Error fetching user profile:', profileError)
        // Continue even if profile fetch fails
      }

      return {
        success: true,
        user: {
          ...user,
          profile: userProfile?.[0] || null
        }
      }
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to get current user'
      }
    }
  },

  // Update user profile
  updateProfile: async (userId, profileData) => {
    try {
      const { data, error } = await supabaseDB.update(
        'profiles',  // Changed from 'users' to 'profiles'
        {
          ...profileData,
          updated_at: new Date().toISOString()
        },
        { id: userId }
      )

      if (error) {
        throw new Error(error.message)
      }

      return {
        success: true,
        data: data?.[0] || null
      }
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Profile update failed'
      }
    }
  },

  // Get current session
  getCurrentSession: async () => {
    try {
      const { data: { session }, error } = await supabaseAuth.getCurrentSession()
      
      if (error) {
        throw new Error(error.message)
      }

      return {
        success: true,
        session
      }
    } catch (error) {
      return {
        success: false,
        error: error.message || 'Failed to get session'
      }
    }
  },

  // Listen to auth state changes
  onAuthStateChange: (callback) => {
    return supabaseAuth.onAuthStateChange((event, session) => {
      callback(event, session)
    })
  }
}

export default authService