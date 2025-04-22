import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase/client";

export async function POST(request) {
  try {
    const { content, language } = await request.json();

    // Validate request data
    if (!content || !language) {
      return NextResponse.json(
        { error: "Content and language are required" },
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

    // Prepare request to OpenAI
    const prompt = `
      You are a language tutor helping a student practice ${language}. 
      Review the following text written by the student and provide grammar corrections.
      Format your response as JSON with the following structure:
      {
        "corrected_content": "The corrected version of the text",
        "corrections": [
          {
            "original": "original text with error",
            "corrected": "corrected text",
            "explanation": "brief explanation of the correction"
          }
        ]
      }
      
      Student text: ${content}
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
            content: "You are a helpful language tutor providing grammar corrections."
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
        { error: "Failed to get grammar feedback" },
        { status: 500 }
      );
    }

    const openaiData = await openaiResponse.json();
    const aiResponse = JSON.parse(openaiData.choices[0].message.content);

    return NextResponse.json(aiResponse);
  } catch (error) {
    console.error("Grammar API error:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}