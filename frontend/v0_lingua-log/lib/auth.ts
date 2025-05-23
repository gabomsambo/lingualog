import { supabase } from './supabase';

// Session storage key
const SESSION_KEY = "supabase_session";

/**
 * Sign up with email and password
 */
export async function signUp({ email, password, username }: { email: string; password: string; username?: string }) {
  try {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: {
          username
        }
      }
    });

    if (error) throw error;

    // The server-side trigger (handle_new_user) will now create the user record in public.users.
    // So, the client-side insertion block below is no longer needed and has been removed.

    // if (data.user) {
    //   const { error: userError } = await supabase
    //     .from('users')
    //     .insert({
    //       id: data.user.id,
    //       email: data.user.email,
    //       username: username || null
    //     });

    //   if (userError) {
    //     console.error("Error creating user record:", userError);
    //     // Don't throw here to allow sign up to succeed even if
    //     // the user record creation fails - it can be fixed later
    //   }
    // }

    return { success: true, user: data.user };
  } catch (error) {
    console.error("Signup error:", error);
    throw error;
  }
}

/**
 * Sign in with email and password
 */
export async function signIn({ email, password }: { email: string; password: string }) {
  try {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    });

    if (error) throw error;
    return { success: true, user: data.user, session: data.session };
  } catch (error) {
    console.error("Login error:", error);
    throw error;
  }
}

/**
 * Sign in with magic link
 */
export async function signInWithEmail(email: string) {
  try {
    const { data, error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/callback`,
      },
    });

    if (error) throw error;
    return { success: true, message: "Check your email for the login link!" };
  } catch (error) {
    console.error("Login error:", error);
    throw error;
  }
}

/**
 * Sign out the current user
 */
export async function signOut() {
  try {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    return { success: true };
  } catch (error) {
    console.error("Logout error:", error);
    throw error;
  }
}

/**
 * Get the current user session
 */
export async function getSession() {
  try {
    const { data, error } = await supabase.auth.getSession();
    if (error) throw error;
    return data.session;
  } catch (error) {
    console.error("Get session error:", error);
    return null;
  }
}

/**
 * Get the current user
 */
export async function getUser() {
  try {
    const { data, error } = await supabase.auth.getUser();
    if (error) throw error;
    return data.user;
  } catch (error) {
    console.error("Get user error:", error);
    return null;
  }
}

/**
 * Check if a user is logged in
 */
export async function isLoggedIn() {
  const session = await getSession();
  return !!session;
}

/**
 * Get auth headers for API requests
 * This will include the Supabase JWT token
 */
export async function getAuthHeaders() {
  const session = await getSession();
  return session ? { Authorization: `Bearer ${session.access_token}` } : {};
} 