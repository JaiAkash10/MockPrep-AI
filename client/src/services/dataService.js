import { supabaseDB } from '../lib/supabase'

// Data service for handling database operations with Supabase
export const dataService = {
  // User-related operations (now refers to 'profiles' table)
  users: {
    // Get user profile by ID
    getById: async (userId) => {
      return await supabaseDB.select('profiles', '*', { id: userId });
    },

    // Get user profile by email (if email is a unique column in profiles)
    getByEmail: async (email) => {
      return await supabaseDB.select('profiles', '*', { email });
    },

    // Update user profile
    update: async (userId, userData) => {
      return await supabaseDB.update('profiles', userData, { id: userId });
    },

    // Delete user profile (use with caution, might need to handle auth user deletion separately)
    delete: async (userId) => {
      return await supabaseDB.delete('profiles', { id: userId });
    }
  },

  // Interview results operations
  results: {
    // Get all results for a user
    getByUser: async (userId) => {
      return await supabaseDB.select('interview_results', '*', { user_id: userId });
    },

    // Get results by email (for backward compatibility) - Commented out
    // getByEmail: async (email) => {
    //   return await supabaseDB.select('interview_results', '*', { email });
    // },

    // Get results by question
    // This client-side one might be redundant or for a different purpose than backend API.
    // Keeping as is for now. It uses the global supabase client.
    getByQuestion: async (userId, question) => {
      const { data, error } = await supabase // Note: uses global supabase, not supabaseDB helper
        .from('interview_results')
        .select('*')
        .eq('user_id', userId)
        .eq('question', question)
        .order('created_at', { ascending: false });
      
      return { data, error };
    },

    // Create new result - Commented out
    // create: async (resultData) => {
    //   return await supabaseDB.insert('interview_results', {
    //     ...resultData,
    //     created_at: new Date().toISOString(),
    //     updated_at: new Date().toISOString()
    //   });
    // },

    // Update result
    update: async (resultId, resultData) => {
      return await supabaseDB.update('interview_results', {
        ...resultData,
        updated_at: new Date().toISOString()
      }, { id: resultId })
    },

    // Delete result
    delete: async (resultId) => {
      return await supabaseDB.delete('interview_results', { id: resultId })
    }
  },

  // Resume operations
  resumes: {
    // Get all resumes for a user
    getByUser: async (userId) => {
      return await supabaseDB.select('resumes', '*', { user_id: userId })
    },

    // Get resume by ID (Supabase UUID)
    getById: async (resumeId) => {
      return await supabaseDB.select('resumes', '*', { id: resumeId });
    },

    // Get resume by client-generated ID
    getByClientId: async (clientResumeId) => {
      // Assumes supabaseDB.select returns an object like { data, error }
      // and data is an array.
      const { data, error } = await supabaseDB.select('resumes', '*', { client_resume_id: clientResumeId });
      if (error) {
        console.error('Error fetching resume by client_resume_id:', error.message);
        return { data: null, error };
      }
      // Return the single record or null if not found
      return { data: data?.[0] || null, error: null };
    },

    // Create new resume - Commented out
    // create: async (resumeData) => {
    //   return await supabaseDB.insert('resumes', {
    //     ...resumeData,
    //     created_at: new Date().toISOString(),
    //     updated_at: new Date().toISOString()
    //   });
    // },

    // Update resume
    update: async (resumeId, resumeData) => {
      return await supabaseDB.update('resumes', {
        ...resumeData,
        updated_at: new Date().toISOString()
      }, { id: resumeId })
    },

    // Delete resume
    delete: async (resumeId) => {
      return await supabaseDB.delete('resumes', { id: resumeId })
    }
  },

  // Resume analysis operations
  resumeAnalysis: {
    // Get analysis by resume ID
    getByResumeId: async (resumeId) => {
      return await supabaseDB.select('resume_analysis', '*', { resume_id: resumeId })
    },

    // Get analysis by user
    getByUser: async (userId) => {
      return await supabaseDB.select('resume_analysis', '*', { user_id: userId })
    },

    // Create new analysis
    create: async (analysisData) => {
      return await supabaseDB.insert('resume_analysis', {
        ...analysisData,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      })
    },

    // Update analysis
    update: async (analysisId, analysisData) => {
      return await supabaseDB.update('resume_analysis', {
        ...analysisData,
        updated_at: new Date().toISOString()
      }, { id: analysisId })
    },

    // Delete analysis
    delete: async (analysisId) => {
      return await supabaseDB.delete('resume_analysis', { id: analysisId })
    }
  },

  // Generic operations for any table
  generic: {
    // Get all records from a table
    getAll: async (table, filters = {}) => {
      return await supabaseDB.select(table, '*', filters)
    },

    // Get single record
    getOne: async (table, filters = {}) => {
      const { data, error } = await supabaseDB.select(table, '*', filters)
      return {
        data: data?.[0] || null,
        error
      }
    },

    // Create record
    create: async (table, data) => {
      return await supabaseDB.insert(table, {
        ...data,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      })
    },

    // Update record
    update: async (table, data, filters) => {
      return await supabaseDB.update(table, {
        ...data,
        updated_at: new Date().toISOString()
      }, filters)
    },

    // Delete record
    delete: async (table, filters) => {
      return await supabaseDB.delete(table, filters)
    }
  }
}

export default dataService