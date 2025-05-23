#!/usr/bin/env python
"""
Example Script for Mistral-7B-Instruct-v0.3 Usage in LinguaLog.

This script demonstrates how to use the Mistral model for:
1. Text generation (completion)
2. Translation
3. Language feedback (complete analysis)

It provides practical examples of working with the Mistral integration
in the LinguaLog application.
"""
import logging
import sys
from pathlib import Path
import time

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Import Mistral engine
import mistral_engine
from feedback_engine import generate_feedback


def text_generation_example():
    """Example of using Mistral for text generation."""
    print("\n=== Text Generation Example ===")
    
    # Define a prompt for text generation
    prompt = "Write a short paragraph about the benefits of learning a new language:"
    
    print(f"Prompt: {prompt}")
    print("Generating response...")
    
    # Generate text using Mistral
    start_time = time.time()
    response = mistral_engine.generate_text(prompt)
    elapsed_time = time.time() - start_time
    
    print(f"\nResponse (generated in {elapsed_time:.2f} seconds):")
    print(response)
    print("\n")


def translation_example():
    """Example of using Mistral for translation."""
    print("\n=== Translation Example ===")
    
    # Example texts in different languages
    examples = [
        {"text": "Bonjour, comment allez-vous aujourd'hui?", "language": "French"},
        {"text": "Ich lerne jeden Tag Englisch und es macht mir Spaß.", "language": "German"},
        {"text": "Me gusta mucho viajar y conocer nuevas culturas.", "language": "Spanish"}
    ]
    
    # Load model and tokenizer once to reuse
    print("Loading Mistral model (this may take a moment)...")
    model, tokenizer = mistral_engine.load_model()
    
    for example in examples:
        text = example["text"]
        language = example["language"]
        
        print(f"\n{language} text: {text}")
        
        # Construct translation prompt
        prompt = f"Translate this {language} text to English: \"{text}\""
        
        # Generate translation
        start_time = time.time()
        translation = mistral_engine.generate_text(prompt, model, tokenizer)
        elapsed_time = time.time() - start_time
        
        print(f"Translation (generated in {elapsed_time:.2f} seconds):")
        print(translation)


def language_feedback_example():
    """Example of using the complete feedback engine with Mistral."""
    print("\n=== Complete Language Feedback Example ===")
    
    # Example journal entry with intentional mistakes
    journal_entry = """
    Yesterday I goed to the store for buying some foods. 
    The weather was very nice and I see many peoples outside. 
    I thinked about my plans for the weekend and I am excited.
    """
    
    print(f"Journal entry:\n{journal_entry}")
    print("\nGenerating comprehensive language feedback...")
    
    # Generate feedback
    start_time = time.time()
    feedback = generate_feedback(journal_entry)
    elapsed_time = time.time() - start_time
    
    print(f"\nFeedback (generated in {elapsed_time:.2f} seconds):")
    print(f"Corrected version:\n{feedback['corrected']}")
    print(f"\nNative-like rewrite:\n{feedback['rewritten']}")
    print(f"\nFluency score: {feedback['score']}/100")
    print(f"Detected tone: {feedback['tone']}")
    print(f"\nTranslation:\n{feedback['translation']}")
    print(f"\nExplanation of mistakes:\n{feedback['explanation']}")


if __name__ == "__main__":
    # First, ensure model is downloaded
    print("Checking if Mistral model is downloaded...")
    model_path = mistral_engine.download_model()
    print(f"Model path: {model_path}")
    
    # Run examples
    try:
        # Example 1: Simple text generation
        text_generation_example()
        
        # Example 2: Translation examples
        translation_example()
        
        # Example 3: Complete language feedback
        language_feedback_example()
        
    except KeyboardInterrupt:
        print("\nExecution interrupted by user. Exiting...")
    except Exception as e:
        print(f"\nError during execution: {str(e)}")
        logging.error(f"Execution error: {str(e)}", exc_info=True) 