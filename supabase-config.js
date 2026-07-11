/**
 * AlphaMind OS — Supabase configuration
 *
 * Paste your Supabase Project URL and Publishable (Anon) Key below.
 * These are safe to use in the browser when Row Level Security is enabled.
 *
 * NEVER put these in this file:
 * - Database password
 * - Secret key
 * - Service role key
 * - Connection string
 */

const SUPABASE_URL = "https://skhvblmtfjuuoxwxjgrg.supabase.co";
const SUPABASE_PUBLISHABLE_KEY = "sb_publishable_f_AqZlSyecDZYPRny1r6Zg_O2YN_Z5N";

// Create one shared Supabase client for the whole dashboard
window.supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);
