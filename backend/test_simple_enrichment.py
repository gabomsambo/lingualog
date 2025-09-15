#!/usr/bin/env python3
"""
Simple test to manually enrich a vocabulary word by directly updating user_vocabulary table.
"""

import sys
import os
sys.path.insert(0, '/Users/gabrielsambo/Desktop/udh lock in/lingualog/backend')

from database import create_supabase_client
import uuid

def test_direct_enrichment():
    """Test direct enrichment by updating user_vocabulary table."""
    print("🧪 Testing direct enrichment for 'correcto'")
    
    try:
        supabase = create_supabase_client()
        
        # Sample enrichment data
        enrichment_data = {
            "ai_example_sentences": [
                "Esa respuesta es correcta.",
                "El procedimiento correcto es importante.",
                "¿Es correcto este camino?"
            ],
            "ai_synonyms": ["exacto", "acertado", "preciso", "adecuado"],
            "ai_antonyms": ["incorrecto", "erróneo", "equivocado"],
            "ai_cultural_note": "En español, 'correcto' se usa tanto en contextos formales como informales para indicar que algo está bien hecho o es apropiado.",
            "emotion_tone": "neutral, educativo",
            "emoji": "✅",
            "source_model": "manual_test"
        }
        
        # Update correcto word
        result = supabase.table("user_vocabulary").update(enrichment_data).eq("id", "ca8a998a-8eef-4bc3-accd-1aa3f4b392fa").execute()
        
        if result.data:
            print("✅ Successfully enriched 'correcto'!")
            print(f"📊 Updated fields: {list(enrichment_data.keys())}")
            return True
        else:
            print("❌ Failed to update 'correcto'")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_direct_enrichment()
    if success:
        print("\n🎉 Direct enrichment test successful!")
        print("📝 Now test the frontend to see if Cultural & Usage Insights appear.")
    else:
        print("\n⚠️ Direct enrichment test failed.")
