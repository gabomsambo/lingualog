"""
Quiz Generation Agent using Atomic Agents framework.

This agent provides quiz generation, ELI5 explanations, and additional examples
for vocabulary learning.
"""

import os
import logging
from typing import Optional
import instructor
from openai import OpenAI, AsyncOpenAI
from atomic_agents import AtomicAgent, AgentConfig, BaseIOSchema
from atomic_agents.context import SystemPromptGenerator, ChatHistory

from ..schemas import (
    QuizGenerationInputSchema, QuizGenerationOutputSchema,
    ELI5InputSchema, ELI5OutputSchema,
    MoreExamplesInputSchema, MoreExamplesOutputSchema
)
from ..context_providers import UserPreferencesProvider

logger = logging.getLogger(__name__)


class QuizGenerationAgent:
    """
    Atomic Agent for vocabulary quiz generation and educational content creation.
    
    This agent generates interactive quizzes, simple explanations (ELI5),
    and additional example sentences for vocabulary learning.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", provider: str = "openai", use_async: bool = False):
        
        # Initialize the appropriate client
        if provider == "openai":
            # Handle both naming conventions for API key
            api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY or OPEN_AI_API_KEY in environment.")
            
            if use_async:
                client = instructor.from_openai(AsyncOpenAI(api_key=api_key))
            else:
                client = instructor.from_openai(OpenAI(api_key=api_key))
        else:
            raise ValueError(f"Provider {provider} not yet supported")
        
        # Store client for creating different agents for different tasks
        self.client = client
        self.model = model
        
        # Create quiz generation agent
        quiz_system_prompt = SystemPromptGenerator(
            background=[
                "You are an expert language educator specializing in interactive quiz creation.",
                "You design engaging, pedagogically sound multiple-choice questions for vocabulary learning.",
                "Your quizzes test comprehension, usage, and contextual understanding.",
            ],
            steps=[
                "Analyze the target vocabulary word and its difficulty level",
                "Create diverse question types (definition, usage, context, synonyms)",
                "Generate plausible distractors that test real understanding",
                "Ensure questions are clear, unambiguous, and fair",
                "Provide educational explanations for correct answers",
                "Adapt difficulty to the specified level",
            ],
            output_instructions=[
                "Create exactly the requested number of questions",
                "Each question should have 3-4 answer options",
                "Include one clearly correct answer and plausible distractors",
                "Provide brief, helpful explanations for correct answers",
                "Vary question types to test different aspects of knowledge",
                "Use clear, learner-appropriate language",
                "Ensure questions test genuine understanding, not just memorization",
            ]
        )
        
        self.quiz_agent = AtomicAgent[QuizGenerationInputSchema, QuizGenerationOutputSchema](
            config=AgentConfig(
                client=client,
                model=model,
                system_prompt_generator=quiz_system_prompt,
                history=ChatHistory(),
            )
        )
        
        # Create ELI5 agent
        eli5_system_prompt = SystemPromptGenerator(
            background=[
                "You are a gifted educator who excels at explaining complex concepts in simple, relatable terms.",
                "You use analogies, metaphors, and everyday examples to make learning accessible and fun.",
                "Your explanations are accurate while being engaging and memorable.",
            ],
            steps=[
                "Break down the concept into its most essential components",
                "Find relatable analogies or real-world comparisons",
                "Use simple vocabulary and short sentences",
                "Include vivid imagery or examples where helpful",
                "Make the explanation memorable and engaging",
                "Ensure accuracy while maintaining simplicity",
            ],
            output_instructions=[
                "Explain as if speaking to a curious 5-year-old",
                "Use simple words and short sentences",
                "Include analogies or examples from everyday life",
                "Make it engaging and fun to learn",
                "Keep it brief but complete",
                "Use positive, encouraging tone",
                "Avoid technical jargon or complex grammar",
            ]
        )
        
        self.eli5_agent = AtomicAgent[ELI5InputSchema, ELI5OutputSchema](
            config=AgentConfig(
                client=client,
                model=model,
                system_prompt_generator=eli5_system_prompt,
                history=ChatHistory(),
            )
        )
        
        # Create examples generation agent
        examples_system_prompt = SystemPromptGenerator(
            background=[
                "You are a skilled language teacher who creates natural, diverse example sentences.",
                "Your examples demonstrate authentic usage in various contexts and registers.",
                "You adapt examples to different proficiency levels and avoid repetitive patterns.",
            ],
            steps=[
                "Consider the word's meaning, register, and typical usage contexts",
                "Generate sentences that show different aspects of the word's usage",
                "Vary sentence structure, length, and complexity appropriately",
                "Ensure examples are natural and contextually appropriate",
                "Avoid redundancy with existing examples",
                "Adapt to the learner's proficiency level",
            ],
            output_instructions=[
                "Create the exact number of examples requested",
                "Ensure each example is distinct and shows different usage",
                "Use natural, contemporary language",
                "Vary contexts (formal, informal, everyday situations)",
                "Make examples memorable and relatable",
                "Appropriate for the target proficiency level",
                "Show the word in realistic, useful contexts",
            ]
        )
        
        self.examples_agent = AtomicAgent[MoreExamplesInputSchema, MoreExamplesOutputSchema](
            config=AgentConfig(
                client=client,
                model=model,
                system_prompt_generator=examples_system_prompt,
                history=ChatHistory(),
            )
        )
        
        logger.info(f"QuizGenerationAgent initialized with {provider} {model}")
    
    def generate_quiz(self, 
                     word: str, 
                     language: str, 
                     num_questions: int = 3, 
                     difficulty: str = "medium") -> QuizGenerationOutputSchema:
        """
        Generate a mini-quiz for a vocabulary word.
        
        Args:
            word: The vocabulary word to quiz about
            language: The language of the word
            num_questions: Number of questions to generate (1-10)
            difficulty: Quiz difficulty level (easy, medium, hard)
            
        Returns:
            QuizGenerationOutputSchema with quiz data
        """
        logger.info(f"Generating quiz for word: '{word}' in {language}, {num_questions} questions, {difficulty} difficulty")
        
        input_data = QuizGenerationInputSchema(
            word=word,
            language=language,
            num_questions=num_questions,
            difficulty=difficulty
        )
        
        try:
            result = self.quiz_agent.run(input_data)
            logger.info(f"Successfully generated quiz for '{word}' with {len(result.questions)} questions")
            return result
            
        except Exception as e:
            logger.error(f"Error generating quiz for word '{word}': {e}", exc_info=True)
            # Return minimal valid structure on error
            return QuizGenerationOutputSchema(
                quiz_title=f"Quiz for '{word}'",
                questions=[]
            )
    
    async def generate_quiz_async(self, 
                                 word: str, 
                                 language: str, 
                                 num_questions: int = 3, 
                                 difficulty: str = "medium") -> QuizGenerationOutputSchema:
        """
        Async version of generate_quiz method.
        """
        logger.info(f"Async generating quiz for word: '{word}' in {language}")
        
        input_data = QuizGenerationInputSchema(
            word=word,
            language=language,
            num_questions=num_questions,
            difficulty=difficulty
        )
        
        try:
            result = self.quiz_agent.run(input_data)
            logger.info(f"Successfully generated quiz for '{word}' with {len(result.questions)} questions")
            return result
            
        except Exception as e:
            logger.error(f"Error generating quiz for word '{word}': {e}", exc_info=True)
            return QuizGenerationOutputSchema(
                quiz_title=f"Quiz for '{word}'",
                questions=[]
            )
    
    def explain_eli5(self, 
                    term: str, 
                    language: str, 
                    context: Optional[str] = None) -> ELI5OutputSchema:
        """
        Generate an "Explain Like I'm 5" explanation for a term.
        
        Args:
            term: The term to explain
            language: The language of the term
            context: Optional context where the term was encountered
            
        Returns:
            ELI5OutputSchema with simple explanation
        """
        logger.info(f"Generating ELI5 explanation for term: '{term}' in {language}")
        
        input_data = ELI5InputSchema(
            term=term,
            language=language,
            context=context
        )
        
        try:
            result = self.eli5_agent.run(input_data)
            logger.info(f"Successfully generated ELI5 explanation for '{term}'")
            return result
            
        except Exception as e:
            logger.error(f"Error generating ELI5 explanation for term '{term}': {e}", exc_info=True)
            return ELI5OutputSchema(
                explanation=f"Sorry, I couldn't explain '{term}' right now. Try again later!"
            )
    
    async def explain_eli5_async(self, 
                               term: str, 
                               language: str, 
                               context: Optional[str] = None) -> ELI5OutputSchema:
        """
        Async version of explain_eli5 method.
        """
        logger.info(f"Async generating ELI5 explanation for term: '{term}' in {language}")
        
        input_data = ELI5InputSchema(
            term=term,
            language=language,
            context=context
        )
        
        try:
            result = self.eli5_agent.run(input_data)
            logger.info(f"Successfully generated ELI5 explanation for '{term}'")
            return result
            
        except Exception as e:
            logger.error(f"Error generating ELI5 explanation for term '{term}': {e}", exc_info=True)
            return ELI5OutputSchema(
                explanation=f"Sorry, I couldn't explain '{term}' right now. Try again later!"
            )
    
    def generate_more_examples(self, 
                              word: str, 
                              language: str, 
                              existing_examples: Optional[list] = None,
                              target_audience_level: str = "intermediate",
                              num_examples: int = 3) -> MoreExamplesOutputSchema:
        """
        Generate additional example sentences for a word.
        
        Args:
            word: The word to generate examples for
            language: The language of the word
            existing_examples: List of existing examples to avoid duplicating
            target_audience_level: Proficiency level for examples
            num_examples: Number of examples to generate
            
        Returns:
            MoreExamplesOutputSchema with new example sentences
        """
        logger.info(f"Generating {num_examples} more examples for word: '{word}' in {language}")
        
        input_data = MoreExamplesInputSchema(
            word=word,
            language=language,
            existing_examples=existing_examples or [],
            target_audience_level=target_audience_level,
            num_examples=num_examples
        )
        
        try:
            result = self.examples_agent.run(input_data)
            logger.info(f"Successfully generated {len(result.new_example_sentences)} examples for '{word}'")
            return result
            
        except Exception as e:
            logger.error(f"Error generating examples for word '{word}': {e}", exc_info=True)
            return MoreExamplesOutputSchema(
                new_example_sentences=[]
            )
    
    async def generate_more_examples_async(self, 
                                         word: str, 
                                         language: str, 
                                         existing_examples: Optional[list] = None,
                                         target_audience_level: str = "intermediate",
                                         num_examples: int = 3) -> MoreExamplesOutputSchema:
        """
        Async version of generate_more_examples method.
        """
        logger.info(f"Async generating {num_examples} more examples for word: '{word}' in {language}")
        
        input_data = MoreExamplesInputSchema(
            word=word,
            language=language,
            existing_examples=existing_examples or [],
            target_audience_level=target_audience_level,
            num_examples=num_examples
        )
        
        try:
            result = self.examples_agent.run(input_data)
            logger.info(f"Successfully generated {len(result.new_example_sentences)} examples for '{word}'")
            return result
            
        except Exception as e:
            logger.error(f"Error generating examples for word '{word}': {e}", exc_info=True)
            return MoreExamplesOutputSchema(
                new_example_sentences=[]
            )
