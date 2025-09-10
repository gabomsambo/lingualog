"""
User Preferences Context Provider for Atomic Agents.

This provider injects user-specific preferences and learning context
into the agent's system prompt for personalized feedback.
"""

from typing import Dict, Any, Optional
from atomic_agents.context import BaseDynamicContextProvider


class UserPreferencesProvider(BaseDynamicContextProvider):
    """
    Provides user-specific context for personalized AI feedback.
    
    This context provider injects information about the user's:
    - Learning level and goals
    - Native language
    - Preferred feedback style
    - Learning focus areas
    """
    
    def __init__(self, 
                 user_level: str = "intermediate",
                 native_language: str = "English", 
                 feedback_style: str = "encouraging",
                 focus_areas: Optional[list] = None):
        """
        Initialize the user preferences provider.
        
        Args:
            user_level: User's proficiency level (beginner, intermediate, advanced)
            native_language: User's native language for better explanations
            feedback_style: Preferred feedback style (encouraging, direct, detailed)
            focus_areas: Specific areas to focus on (grammar, vocabulary, fluency)
        """
        super().__init__(title="User Learning Preferences")
        self.user_level = user_level
        self.native_language = native_language
        self.feedback_style = feedback_style
        self.focus_areas = focus_areas or ["grammar", "vocabulary", "fluency"]
    
    def get_info(self) -> str:
        """
        Generate the context string for user preferences.
        
        Returns:
            Formatted context string with user preferences
        """
        context_parts = [
            f"User Profile:",
            f"- Proficiency Level: {self.user_level}",
            f"- Native Language: {self.native_language}",
            f"- Preferred Feedback Style: {self.feedback_style}",
            f"- Focus Areas: {', '.join(self.focus_areas)}"
        ]
        
        # Add level-specific guidance
        if self.user_level == "beginner":
            context_parts.append("- Provide simple, clear explanations with basic vocabulary")
            context_parts.append("- Focus on fundamental grammar and common mistakes")
        elif self.user_level == "intermediate":
            context_parts.append("- Provide moderate complexity explanations")
            context_parts.append("- Include cultural context and idiomatic usage")
        elif self.user_level == "advanced":
            context_parts.append("- Provide sophisticated feedback with nuanced explanations")
            context_parts.append("- Focus on style, register, and advanced vocabulary")
        
        # Add feedback style guidance
        if self.feedback_style == "encouraging":
            context_parts.append("- Always start with positive observations before corrections")
            context_parts.append("- Frame mistakes as learning opportunities")
        elif self.feedback_style == "direct":
            context_parts.append("- Be concise and direct in corrections")
            context_parts.append("- Focus on actionable improvements")
        elif self.feedback_style == "detailed":
            context_parts.append("- Provide comprehensive explanations for all suggestions")
            context_parts.append("- Include grammar rules and linguistic reasoning")
        
        return "\n".join(context_parts)


class LanguageContextProvider(BaseDynamicContextProvider):
    """
    Provides language-specific context for better AI analysis.
    
    This context provider injects information about:
    - Language-specific grammar rules
    - Common mistakes for learners
    - Cultural and regional variations
    - Formal vs informal register
    """
    
    def __init__(self, target_language: str, language_variant: Optional[str] = None):
        """
        Initialize the language context provider.
        
        Args:
            target_language: The language being learned
            language_variant: Specific variant (e.g., "Mexican Spanish", "British English")
        """
        super().__init__(title=f"{target_language} Language Context")
        self.target_language = target_language.lower()
        self.language_variant = language_variant
    
    def get_info(self) -> str:
        """
        Generate language-specific context.
        
        Returns:
            Formatted context string with language-specific guidance
        """
        context_parts = [f"Language-Specific Context for {self.target_language.title()}:"]
        
        # Add language-specific guidance
        if self.target_language == "english":
            context_parts.extend([
                "- Focus on article usage (a, an, the)",
                "- Pay attention to verb tenses and irregular verbs", 
                "- Watch for subject-verb agreement",
                "- Consider formal vs informal register"
            ])
        elif self.target_language == "spanish":
            context_parts.extend([
                "- Focus on gender agreement (masculine/feminine)",
                "- Pay attention to ser vs estar usage",
                "- Watch for subjunctive mood usage",
                "- Consider formal (usted) vs informal (tú) address"
            ])
        elif self.target_language == "french":
            context_parts.extend([
                "- Focus on gender agreement and liaison",
                "- Pay attention to subjunctive and conditional moods",
                "- Watch for proper use of pronouns",
                "- Consider formal vs informal register (vous vs tu)"
            ])
        elif self.target_language == "german":
            context_parts.extend([
                "- Focus on case system (nominative, accusative, dative, genitive)",
                "- Pay attention to verb position in sentences",
                "- Watch for separable verbs",
                "- Consider formal (Sie) vs informal (du) address"
            ])
        elif self.target_language == "japanese":
            context_parts.extend([
                "- Focus on politeness levels (keigo)",
                "- Pay attention to particle usage (wa, ga, wo, ni, etc.)",
                "- Watch for proper verb conjugations",
                "- Consider context and social hierarchy"
            ])
        else:
            context_parts.extend([
                "- Focus on common grammar patterns for this language",
                "- Pay attention to cultural context and usage",
                "- Watch for register and formality levels"
            ])
        
        if self.language_variant:
            context_parts.append(f"- Specific variant: {self.language_variant}")
        
        return "\n".join(context_parts)


class LearningHistoryProvider(BaseDynamicContextProvider):
    """
    Provides context based on user's learning history and progress.
    
    This context provider can inject information about:
    - Previously corrected mistakes
    - Vocabulary words the user has learned
    - Areas where the user has shown improvement
    - Recurring issues to focus on
    """
    
    def __init__(self, 
                 recent_mistakes: Optional[list] = None,
                 learned_vocabulary: Optional[list] = None,
                 improvement_areas: Optional[list] = None):
        """
        Initialize the learning history provider.
        
        Args:
            recent_mistakes: List of recent grammar mistakes to watch for
            learned_vocabulary: List of vocabulary words user has learned
            improvement_areas: Areas where user has shown improvement
        """
        super().__init__(title="Learning History Context")
        self.recent_mistakes = recent_mistakes or []
        self.learned_vocabulary = learned_vocabulary or []
        self.improvement_areas = improvement_areas or []
    
    def get_info(self) -> str:
        """
        Generate learning history context.
        
        Returns:
            Formatted context string with learning history
        """
        if not any([self.recent_mistakes, self.learned_vocabulary, self.improvement_areas]):
            return "Learning History: No previous learning data available."
        
        context_parts = ["Learning History Context:"]
        
        if self.recent_mistakes:
            context_parts.append("Recent Mistakes to Watch For:")
            for mistake in self.recent_mistakes[:5]:  # Limit to 5 most recent
                context_parts.append(f"  - {mistake}")
        
        if self.learned_vocabulary:
            context_parts.append("Recently Learned Vocabulary:")
            for word in self.learned_vocabulary[:10]:  # Limit to 10 most recent
                context_parts.append(f"  - {word}")
        
        if self.improvement_areas:
            context_parts.append("Areas of Improvement:")
            for area in self.improvement_areas:
                context_parts.append(f"  - {area}")
        
        return "\n".join(context_parts)
