import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase/client";

export async function POST(request) {
  try {
    const { entryId } = await request.json();

    // Validate request data
    if (!entryId) {
      return NextResponse.json(
        { error: "Entry ID is required" },
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

    // Fetch the entry
    const { data: entry, error: entryError } = await supabase
      .from("entries")
      .select("*")
      .eq("id", entryId)
      .eq("user_id", user.id)
      .single();

    if (entryError || !entry) {
      return NextResponse.json(
        { error: "Entry not found" },
        { status: 404 }
      );
    }

    // Prepare request to OpenAI for vocabulary extraction
    const prompt = `
      You are a language tutor helping a student learn ${entry.language}. 
      Extract important vocabulary words from the following text that would be valuable for a language learner to remember.
      For each word, provide its base form, a brief definition, and an example sentence (different from the original text).
      Format your response as a JSON array with the following structure:
      [
        {
          "word": "extracted word",
          "definition": "brief definition",
          "example": "example sentence"
        }
      ]
      Limit your response to 10-15 most important words.
      
      Text: ${entry.content}
    `;

    // Call OpenAI API
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) {
      return NextResponse.json(
        { error: "API key not configured" },
        { status: 500 }
      );
    }

    const openaiResponse = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${apiKey}`
      },
      body: JSON.stringify({
        model: "gpt-4o",
        messages: [
          {
            role: "system",
            content: "You are a helpful language tutor extracting vocabulary."
          },
          {
            role: "user",
            content: prompt
          }
        ],
        temperature: 0.3,
      })
    });

    if (!openaiResponse.ok) {
      const errorData = await openaiResponse.json();
      console.error("OpenAI API error:", errorData);
      return NextResponse.json(
        { error: "Failed to extract vocabulary" },
        { status: 500 }
      );
    }

    const openaiData = await openaiResponse.json();
    const vocabulary = JSON.parse(openaiData.choices[0].message.content);

    // Store the extracted vocabulary in the database
    const vocabularyInserts = vocabulary.map((item) => ({
      user_id: user.id,
      entry_id: entryId,
      word: item.word,
      language: entry.language,
    }));

    const { error: insertError } = await supabase
      .from("vocabulary")
      .insert(vocabularyInserts);

    if (insertError) {
      console.error("Error inserting vocabulary:", insertError);
      return NextResponse.json(
        { error: "Failed to save vocabulary" },
        { status: 500 }
      );
    }

    // Update the entry to mark vocabulary as extracted
    await supabase
      .from("entries")
      .update({ vocab_extracted: true })
      .eq("id", entryId);

    return NextResponse.json({ vocabulary });
  } catch (error) {
    console.error("Vocabulary API error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

export async function GET(request) {
  try {
    const url = new URL(request.url);
    const language = url.searchParams.get("language");
    
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
      .from("vocabulary")
      .select("*")
      .eq("user_id", user.id);
    
    // Add language filter if provided
    if (language) {
      query = query.eq("language", language);
    }
    
    // Order by creation date
    query = query.order("created_at", { ascending: false });

    // Execute query
    const { data, error } = await query;

    if (error) {
      return NextResponse.json(
        { error: "Failed to fetch vocabulary" },
        { status: 500 }
      );
    }

    return NextResponse.json({ vocabulary: data });
  } catch (error) {
    console.error("Vocabulary API error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}