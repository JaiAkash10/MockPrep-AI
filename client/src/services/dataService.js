import { supabaseDB } from '../lib/supabase'

// Data service for handling database operations with Supabase
export const dataService = {
  // User-related operations
  users: {
    // Get user by ID
    getById: async (userId) => {
      return await supabaseDB.select('users', '*', { id: userId })
    },

    // Get user by email
    getByEmail: async (email) => {
      return await supabaseDB.select('users', '*', { email })
    },

    // Update user
    update: async (userId, userData) => {
      return await supabaseDB.update('users', userData, { id: userId })
    },

    // Delete user
    delete: async (userId) => {
      return await supabaseDB.delete('users', { id: userId })
    }
  },

  // Interview results operations
  results: {
    // Get all results for a user
    getByUser: async (userId) => {
      return await supabaseDB.select('interview_results', '*', { user_id: userId })
    },

    // Get results by email (for backward compatibility)
    getByEmail: async (email) => {
      return await supabaseDB.select('interview_results', '*', { email })
    },

    // Get results by question
    getByQuestion: async (userId, question) => {
      const { data, error } = await supabase
        .from('interview_results')
        .select('*')
        .eq('user_id', userId)
        .eq('question', question)
        .order('created_at', { ascending: false })
      
      return { data, error }
    },

    // Create new result
    create: async (resultData) => {
      return await supabaseDB.insert('interview_results', {
        ...resultData,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      })
    },

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

    // Get resume by ID
    getById: async (resumeId) => {
      return await supabaseDB.select('resumes', '*', { id: resumeId })
    },

    // Create new resume
    create: async (resumeData) => {
      return await supabaseDB.insert('resumes', {
        ...resumeData,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      })
    },

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