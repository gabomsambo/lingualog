// src/app/api/entries/[id]/route.js
import { NextResponse } from 'next/server';
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers'; // Import cookies function from next/headers

// Helper function to create Supabase client for Route Handlers
function createSupabaseRouteHandlerClient() {
  const cookieStore = cookies(); // Get the cookie store
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL, // Ensure these are loaded server-side
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    {
      cookies: {
        get(name) {
          return cookieStore.get(name)?.value;
        },
        // We might not need set/remove in GET, but include for completeness if needed elsewhere
        set(name, value, options) {
           cookieStore.set({ name, value, ...options }); // Use cookieStore methods
        },
        remove(name, options) {
          cookieStore.set({ name, value: '', ...options });
        },
      },
    }
  );
}

// --- GET Handler ---
export async function GET(request, { params }) { // Note: request object might not be needed if only using params
  const { id } = params; // Extract entry ID from route parameters

  if (!id) {
    return NextResponse.json({ error: 'Entry ID is required' }, { status: 400 });
  }

  try {
    const supabase = createSupabaseRouteHandlerClient();

    // 1. Verify user session using the server client
    const { data: { session }, error: sessionError } = await supabase.auth.getSession();

    if (sessionError || !session?.user) {
      console.error("API GET /entries/[id]: Auth Error:", sessionError?.message);
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    const userId = session.user.id;

    // 2. Fetch the specific entry for the authenticated user
    const { data: entry, error: fetchError } = await supabase
      .from("entries") // Ensure table name is correct
      .select("*") // Select desired columns
      .eq("id", id) // Match the entry ID from the URL
      .eq("user_id", userId) // IMPORTANT: Ensure entry belongs to the user
      .single(); // Expect only one result

    // Handle fetch errors (e.g., entry not found)
    if (fetchError) {
        console.error(`API GET /entries/[id]: Fetch Error for ID ${id}, User ${userId}:`, fetchError.message);
        // Differentiate between "not found" and other errors if needed
        if (fetchError.code === 'PGRST116') { // Code for "Row not found"
             return NextResponse.json({ error: "Entry not found" }, { status: 404 });
        }
       return NextResponse.json({ error: "Failed to fetch entry" }, { status: 500 });
    }

    // Handle case where entry is null even without error (shouldn't happen with .single() if found)
     if (!entry) {
        return NextResponse.json({ error: "Entry not found" }, { status: 404 });
     }

    // 3. Return the entry data
    return NextResponse.json({ entry });

  } catch (error) {
    console.error(`API GET /entries/[id]: Internal Server Error for ID ${id}:`, error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}

// --- PUT Handler ---
export async function PUT(request, { params }) {
    const { id } = params;
     if (!id) {
       return NextResponse.json({ error: 'Entry ID is required' }, { status: 400 });
     }

    let updateData;
    try {
        updateData = await request.json(); // Get data from request body
    } catch (e) {
        return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
    }

    // Basic validation on update data
    const { title, content, language, corrected_content, vocab_extracted } = updateData;
     if (title === undefined && content === undefined && language === undefined && corrected_content === undefined && vocab_extracted === undefined) {
       return NextResponse.json({ error: "No valid fields provided for update" }, { status: 400 });
     }

    try {
       const supabase = createSupabaseRouteHandlerClient();

       // 1. Verify user session
       const { data: { session }, error: sessionError } = await supabase.auth.getSession();
       if (sessionError || !session?.user) {
         return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
       }
       const userId = session.user.id;

       // 2. Construct the update object safely
       const dataToUpdate = {};
       if (title !== undefined) dataToUpdate.title = title;
       if (content !== undefined) dataToUpdate.content = content;
       if (language !== undefined) dataToUpdate.language = language;
       if (corrected_content !== undefined) dataToUpdate.corrected_content = corrected_content;
       if (vocab_extracted !== undefined) dataToUpdate.vocab_extracted = vocab_extracted;

       // 3. Update the entry in the database
       const { data: updatedEntry, error: updateError } = await supabase
         .from("entries")
         .update(dataToUpdate)
         .eq("id", id)
         .eq("user_id", userId) // Ensure user owns the entry
         .select() // Select the updated row
         .single(); // Expect one row back

       if (updateError) {
           console.error(`API PUT /entries/[id]: Update Error for ID ${id}, User ${userId}:`, updateError.message);
           // Check if the error is due to the row not existing
            if (updateError.code === 'PGRST116') {
                return NextResponse.json({ error: "Entry not found or you don't have permission to update it" }, { status: 404 });
            }
           return NextResponse.json({ error: "Failed to update entry" }, { status: 500 });
       }

        if (!updatedEntry) {
             return NextResponse.json({ error: "Entry not found after update" }, { status: 404 });
        }

       // 4. Return the updated entry
       return NextResponse.json({ entry: updatedEntry });

    } catch (error) {
       console.error(`API PUT /entries/[id]: Internal Server Error for ID ${id}:`, error);
       return NextResponse.json({ error: "Internal server error" }, { status: 500 });
    }
}


// --- DELETE Handler ---
export async function DELETE(request, { params }) { // Note: request object might not be needed
    const { id } = params;
    if (!id) {
      return NextResponse.json({ error: 'Entry ID is required' }, { status: 400 });
    }

    try {
      const supabase = createSupabaseRouteHandlerClient();

      // 1. Verify user session
      const { data: { session }, error: sessionError } = await supabase.auth.getSession();
      if (sessionError || !session?.user) {
        return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
      }
      const userId = session.user.id;

      // 2. Delete the entry
      const { error: deleteError } = await supabase
        .from("entries")
        .delete()
        .eq("id", id)
        .eq("user_id", userId); // Ensure user owns the entry

      // Handle deletion errors
      if (deleteError) {
           console.error(`API DELETE /entries/[id]: Delete Error for ID ${id}, User ${userId}:`, deleteError.message);
           // Consider checking error code if you need to differentiate "not found" vs other errors
           return NextResponse.json({ error: "Failed to delete entry" }, { status: 500 });
       }

      // 3. Return success response (No Content)
      // return new Response(null, { status: 204 }); // Standard for successful DELETE
      // Or return JSON success message
      return NextResponse.json({ success: true, message: "Entry deleted successfully." });

    } catch (error) {
      console.error(`API DELETE /entries/[id]: Internal Server Error for ID ${id}:`, error);
      return NextResponse.json({ error: "Internal server error" }, { status: 500 });
    }
}