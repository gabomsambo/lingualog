import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase/client";

export async function GET(request) {
  try {
    const url = new URL(request.url);
    const language = url.searchParams.get("language");
    const limit = parseInt(url.searchParams.get("limit") || "10");
    const offset = parseInt(url.searchParams.get("offset") || "0");
    
    // Authenticate the user
    const supabase = createSupabaseServerClient();
    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    // Build query
    let query = supabase
      .from("entries")
      .select("*")
      .eq("user_id", user.id);
    
    // Add language filter if provided
    if (language) {
      query = query.eq("language", language);
    }
    
    // Add pagination
    query = query
      .order("created_at", { ascending: false })
      .range(offset, offset + limit - 1);

    // Execute query
    const { data, error, count } = await query;

    if (error) {
      return NextResponse.json(
        { error: "Failed to fetch entries" },
        { status: 500 }
      );
    }

    return NextResponse.json({ 
      entries: data,
      pagination: {
        limit,
        offset,
        total: count
      }
    });
  } catch (error) {
    console.error("Entries API error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

export async function POST(request) {
  try {
    const { title, content, language } = await request.json();

    // Validate request data
    if (!title || !content || !language) {
      return NextResponse.json(
        { error: "Title, content, and language are required" },
        { status: 400 }
      );
    }

    // Authenticate the user
    const supabase = createSupabaseServerClient();
    const { data: { user }, error: authError } = await supabase.auth.getUser();

    if (authError || !user) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    // Insert the entry
    const { data, error } = await supabase
      .from("entries")
      .insert({
        title,
        content,
        language,
        user_id: user.id
      })
      .select()
      .single();

    if (error) {
      return NextResponse.json(
        { error: "Failed to create entry" },
        { status: 500 }
      );
    }

    return NextResponse.json({ entry: data });
  } catch (error) {
    console.error("Entries API error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}