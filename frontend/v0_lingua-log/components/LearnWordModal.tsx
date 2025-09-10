import React from 'react';
import { Badge } from "@/components/ui/badge";

// Define the structure for the vocabulary word data
export interface VocabWordData {
  id: string;
  word?: string; // Word in any language
  term?: string; // Alternative field name for word
  romaji?: string; // Romaji (for Japanese) or equivalent
  definition: string;
  exampleSentence?: string;
  example_sentence?: string; // Alternative field name
  isGlobal?: boolean;
  partOfSpeech?: string;
  part_of_speech?: string; // Alternative field name
  jlptLevel?: string;
  frequency?: 'Common' | 'Uncommon' | 'Rare';
  audioUrl?: string;
  secondaryDefinitions?: string[];
  language?: string; // Language of the word
  
  // AI Enrichment fields (from user_vocabulary table)
  ai_example_sentences?: string[];
  ai_definitions?: string[];
  ai_synonyms?: string[];
  ai_antonyms?: string[];
  ai_related_phrases?: string[];
  ai_conjugation_info?: { [key: string]: any };
  ai_cultural_note?: string;
  ai_pronunciation_guide?: string;
  ai_alternative_forms?: string[];
  ai_common_mistakes?: Array<{ mistake: string; correction: string; explanation?: string }>;
  ai_eli5_explanation?: string;
  emotion_tone?: string;
  mnemonic?: string;
  emoji?: string;
  source_model?: string;
  notes_user?: string; // User notes field
  tags?: string[];
  
  // Computed/transformed fields for UI display
  synonyms?: Array<{ word: string; romaji?: string }>;
  antonyms?: Array<{ word: string; romaji?: string }>;
  relatedPhrases?: Array<{ phrase: string; meaning: string }>;
  conjugations?: { [key: string]: string };
  culturalNote?: string;
  aiCulturalExplanation?: string;
  emotionTone?: string;
  userNote?: string;
  
  // Enhanced AI data
  aiExampleSentences?: Array<{
    sentence: string;
    translation: string;
    complexity?: 'Beginner' | 'Intermediate' | 'Advanced';
  }>;
  eli5Explanation?: string;
  flashcardPreview?: {
    type: 'definition-match' | 'fill-in-blank';
    question: string;
    prompt?: string;
    options?: string[];
    answer: string;
  };
}

interface LearnWordModalProps {
  vocabEntry: VocabWordData;
  isOpen: boolean;
  onClose: () => void;
}

const LearnWordModal: React.FC<LearnWordModalProps> = ({ vocabEntry, isOpen, onClose }) => {
  if (!isOpen) return null;
  
  // Convert vocabulary entry to the expected format with AI enrichment data
  const currentWord: VocabWordData = {
    id: vocabEntry.id || '',
    word: vocabEntry.word || vocabEntry.term || '',
    romaji: '', // Not applicable for Spanish/other languages
    definition: vocabEntry.definition || '',
    exampleSentence: vocabEntry.exampleSentence || vocabEntry.example_sentence || '',
    isGlobal: true,
    partOfSpeech: vocabEntry.partOfSpeech || vocabEntry.part_of_speech || '',
    jlptLevel: '', // Not applicable for Spanish
    frequency: 'Common', // Default
    audioUrl: '',
    secondaryDefinitions: [],
    
    // AI Enrichment Data from user_vocabulary
    synonyms: (vocabEntry.ai_synonyms || []).map((syn: string) => ({ word: syn })),
    antonyms: (vocabEntry.ai_antonyms || []).map((ant: string) => ({ word: ant })),
    relatedPhrases: (vocabEntry.ai_related_phrases || []).map((phrase: string) => ({ 
      phrase: phrase, 
      meaning: '' 
    })),
    conjugations: vocabEntry.ai_conjugation_info || {},
    culturalNote: vocabEntry.ai_cultural_note || '',
    aiCulturalExplanation: vocabEntry.ai_cultural_note || '',
    emotionTone: vocabEntry.emotion_tone || '',
    mnemonic: vocabEntry.mnemonic || '',
    emoji: vocabEntry.emoji || '',
    userNote: vocabEntry.notes_user || '',
    tags: vocabEntry.tags || [],
    
    // AI Example Sentences
    aiExampleSentences: (vocabEntry.ai_example_sentences || []).map((sentence: string, index: number) => ({
      sentence: sentence,
      translation: '', // Could be enhanced with translations
      complexity: index === 0 ? 'Beginner' : index === 1 ? 'Intermediate' : 'Advanced'
    })),
    
    // ELI5 - use database field or generate fallback
    eli5Explanation: vocabEntry.ai_eli5_explanation || 
      (vocabEntry.ai_cultural_note ? 
        `${vocabEntry.word || vocabEntry.term} means "${vocabEntry.definition}". ${vocabEntry.ai_cultural_note}` : 
        `${vocabEntry.word || vocabEntry.term} is a ${vocabEntry.language || 'Spanish'} word that means "${vocabEntry.definition}".`),
    
    // Simple flashcard preview
    flashcardPreview: {
      type: 'definition-match',
      question: vocabEntry.word || '',
      options: [
        vocabEntry.definition || '',
        'Incorrect option 1',
        'Incorrect option 2', 
        'Incorrect option 3'
      ],
      answer: vocabEntry.definition || ''
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 backdrop-blur-sm flex justify-center items-center p-4 z-50">
      <div className="bg-white dark:bg-gray-800 p-6 rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        {/* Modal Header */}
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
              {currentWord.word}{' '}
              <span className="text-xl text-gray-600 dark:text-gray-400">({currentWord.romaji})</span>
              {currentWord.emoji && <span className="ml-2 text-2xl">{currentWord.emoji}</span>}
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {currentWord.jlptLevel && <span className="mr-2 inline-block bg-gray-200 dark:bg-gray-700 px-2 py-0.5 rounded text-xs font-semibold">{currentWord.jlptLevel}</span>}
              {currentWord.frequency && <span className="mr-2 inline-block bg-blue-100 dark:bg-blue-800 text-blue-700 dark:text-blue-200 px-2 py-0.5 rounded text-xs font-semibold">{currentWord.frequency}</span>}
              {currentWord.partOfSpeech && <span className="italic">({currentWord.partOfSpeech})</span>}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700"
            aria-label="Close modal"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-5">
          {/* 1. Word Header - Audio Playback */}
          {currentWord.audioUrl && (
            <div className="border-t pt-4 dark:border-gray-700">
              <h3 className="text-md font-semibold mb-1 text-gray-700 dark:text-gray-300">Audio Pronunciation</h3>
              <audio controls src={currentWord.audioUrl} className="w-full h-10 text-sm">
                Your browser does not support the audio element.
              </audio>
            </div>
          )}

          {/* 2. Definitions */}
          <div className="border-t pt-4 dark:border-gray-700">
            <h3 className="text-md font-semibold mb-1 text-gray-700 dark:text-gray-300">Definitions</h3>
            <p className="text-gray-800 dark:text-gray-200 text-base">{currentWord.definition}</p>
            {currentWord.secondaryDefinitions && currentWord.secondaryDefinitions.length > 0 && (
              <ul className="list-disc list-inside mt-2 text-sm text-gray-600 dark:text-gray-400 space-y-1">
                {currentWord.secondaryDefinitions.map((def, index) => (
                  <li key={index}>{def}</li>
                ))}
              </ul>
            )}
          </div>

          {/* 2.5. Pronunciation Guide */}
          {vocabEntry.ai_pronunciation_guide && (
            <div className="border-t pt-4 dark:border-gray-700">
              <h3 className="text-md font-semibold mb-1 text-gray-700 dark:text-gray-300">Pronunciation Guide</h3>
              <div className="bg-blue-50 dark:bg-blue-900/30 p-3 rounded-lg border border-blue-200 dark:border-blue-700">
                <p className="text-blue-700 dark:text-blue-300 font-mono text-lg">{vocabEntry.ai_pronunciation_guide}</p>
              </div>
            </div>
          )}

          {/* 3. Example Sentences */}
          <div className="border-t pt-4 dark:border-gray-700">
            <h3 className="text-md font-semibold mb-1 text-gray-700 dark:text-gray-300">Example Sentences</h3>
            {currentWord.exampleSentence && (
               <div className="mb-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg border dark:border-gray-600">
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">From your journal:</p>
                  <p className="text-gray-700 dark:text-gray-300 italic leading-relaxed">"{currentWord.exampleSentence}"</p>
                  {/* TODO: Highlight word in sentence */}
               </div>
            )}
            {currentWord.aiExampleSentences && currentWord.aiExampleSentences.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs text-gray-500 dark:text-gray-400">AI Generated Examples:</p>
                {currentWord.aiExampleSentences.map((ex, index) => (
                  <div key={index} className="p-3 bg-sky-50 dark:bg-sky-900/30 rounded-lg border border-sky-200 dark:border-sky-700">
                    <p className="text-gray-700 dark:text-gray-300 italic leading-relaxed">"{ex.sentence}"</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Translation: {ex.translation}</p>
                    {ex.complexity && <Badge variant="outline" className="mt-1 text-xs">{ex.complexity}</Badge>}
                    {/* TODO: Highlight word in sentence */}
                  </div>
                ))}
              </div>
            )}
            {/* Placeholder for button to generate more AI examples */}
          </div>

          {/* 4. Synonyms & Antonyms */}
          {(currentWord.synonyms?.length || currentWord.antonyms?.length) && (
            <div className="border-t pt-4 dark:border-gray-700">
              <h3 className="text-md font-semibold mb-2 text-gray-700 dark:text-gray-300">Synonyms & Antonyms</h3>
              {currentWord.synonyms && currentWord.synonyms.length > 0 && (
                <div className="mb-2">
                  <h4 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">Synonyms:</h4>
                  <div className="flex flex-wrap gap-2">
                    {currentWord.synonyms.map((syn, index) => (
                      <button key={index} className="bg-sky-100 text-sky-700 px-2.5 py-1 rounded-full text-xs hover:bg-sky-200 dark:bg-sky-700 dark:text-sky-100 dark:hover:bg-sky-600 transition-colors">
                        {syn.word} {syn.romaji && <span className="text-sky-500 dark:text-sky-300">({syn.romaji})</span>}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {currentWord.antonyms && currentWord.antonyms.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">Antonyms:</h4>
                   <div className="flex flex-wrap gap-2">
                    {currentWord.antonyms.map((ant, index) => (
                      <button key={index} className="bg-rose-100 text-rose-700 px-2.5 py-1 rounded-full text-xs hover:bg-rose-200 dark:bg-rose-700 dark:text-rose-100 dark:hover:bg-rose-600 transition-colors">
                        {ant.word} {ant.romaji && <span className="text-rose-500 dark:text-rose-300">({ant.romaji})</span>}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 5. Related Phrases / Collocations */}
          {currentWord.relatedPhrases && currentWord.relatedPhrases.length > 0 && (
            <div className="border-t pt-4 dark:border-gray-700">
              <h3 className="text-md font-semibold mb-2 text-gray-700 dark:text-gray-300">Related Phrases</h3>
              <ul className="space-y-1 text-sm">
                {currentWord.relatedPhrases.map((phrase, index) => (
                  <li key={index} className="text-gray-700 dark:text-gray-300">
                    <strong className="font-medium text-gray-800 dark:text-gray-200">{phrase.phrase}</strong>: {phrase.meaning}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 6. Conjugation Chart (if verb/adjective) */}
          {currentWord.partOfSpeech && (currentWord.partOfSpeech.includes('verb') || currentWord.partOfSpeech.includes('adjective')) && currentWord.conjugations && Object.keys(currentWord.conjugations).length > 0 && (
            <div className="border-t pt-4 dark:border-gray-700">
              <h3 className="text-md font-semibold mb-2 text-gray-700 dark:text-gray-300">Conjugation Chart</h3>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
                {Object.entries(currentWord.conjugations).map(([form, value]) => (
                  <div key={form} className="flex justify-between border-b dark:border-gray-700 py-1">
                    <span className="text-gray-600 dark:text-gray-400">{form}:</span>
                    <span className="font-medium text-gray-800 dark:text-gray-200">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 7. Cultural Note / Usage Insight */}
          {currentWord.culturalNote && (
            <div className="border-t pt-4 dark:border-gray-700">
              <h3 className="text-md font-semibold mb-2 text-gray-700 dark:text-gray-300">Cultural & Usage Insights</h3>
              <p className="text-gray-700 dark:text-gray-300 mb-3 text-sm leading-relaxed bg-yellow-50 dark:bg-yellow-900/30 p-3 rounded-lg border border-yellow-200 dark:border-yellow-700">
                {currentWord.culturalNote}
              </p>
            </div>
          )}
          
          {/* 8. Emotion/Tone - combined with Header/Emoji */}
          {currentWord.emotionTone && !currentWord.emoji && /* Display only if emoji isn't already covering it */ (
             <div className="border-t pt-4 dark:border-gray-700">
                <h3 className="text-md font-semibold mb-1 text-gray-700 dark:text-gray-300">Emotion/Tone</h3>
                <p className="text-gray-700 dark:text-gray-300 text-sm">{currentWord.emotionTone}</p>
             </div>
          )}

          {/* 9. Mnemonic or Metaphor */}
          {currentWord.mnemonic && (
            <div className="border-t pt-4 dark:border-gray-700">
              <h3 className="text-md font-semibold mb-2 text-gray-700 dark:text-gray-300">Mnemonic / Metaphor</h3>
              <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed bg-indigo-50 dark:bg-indigo-900/30 p-3 rounded-lg border border-indigo-200 dark:border-indigo-700">{currentWord.mnemonic}</p>
            </div>
          )}

          {/* 9.5. Common Mistakes */}
          {vocabEntry.ai_common_mistakes && vocabEntry.ai_common_mistakes.length > 0 && (
            <div className="border-t pt-4 dark:border-gray-700">
              <h3 className="text-md font-semibold mb-2 text-gray-700 dark:text-gray-300">Common Mistakes</h3>
              <div className="space-y-3">
                {vocabEntry.ai_common_mistakes.map((mistake, index) => (
                  <div key={index} className="bg-red-50 dark:bg-red-900/30 p-3 rounded-lg border border-red-200 dark:border-red-700">
                    <div className="mb-2">
                      <span className="text-red-700 dark:text-red-300 font-medium text-sm">❌ Mistake: </span>
                      <span className="text-red-600 dark:text-red-400 text-sm">{mistake.mistake}</span>
                    </div>
                    <div className="mb-2">
                      <span className="text-green-700 dark:text-green-300 font-medium text-sm">✅ Correction: </span>
                      <span className="text-green-600 dark:text-green-400 text-sm">{mistake.correction}</span>
                    </div>
                    {mistake.explanation && (
                      <div>
                        <span className="text-blue-700 dark:text-blue-300 font-medium text-sm">💡 Explanation: </span>
                        <span className="text-blue-600 dark:text-blue-400 text-sm">{mistake.explanation}</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 10. Optional Enhancements - ELI5, Flashcard Preview, Buttons */}
          <div className="border-t pt-4 dark:border-gray-700">
            <h3 className="text-md font-semibold mb-2 text-gray-700 dark:text-gray-300">Learning Tools</h3>
            {currentWord.eli5Explanation && (
                <div className="mb-3 p-3 bg-purple-50 dark:bg-purple-900/30 rounded-lg border border-purple-200 dark:border-purple-700">
                    <h4 className="text-sm font-medium text-purple-700 dark:text-purple-300 mb-1">Explain Like I'm 5:</h4>
                    <p className="text-purple-600 dark:text-purple-200 text-sm italic">{currentWord.eli5Explanation}</p>
                </div>
            )}
            {currentWord.flashcardPreview && (
                <div className="mb-3 p-3 bg-pink-50 dark:bg-pink-900/30 rounded-lg border border-pink-200 dark:border-pink-700">
                    <h4 className="text-sm font-medium text-pink-700 dark:text-pink-300 mb-1">Mini Quiz:</h4>
                    <p className="text-sm text-pink-600 dark:text-pink-200">Q: {currentWord.flashcardPreview.question}</p>
                    {currentWord.flashcardPreview.type === 'definition-match' && currentWord.flashcardPreview.options && (
                        <div className="mt-1 space-y-1">
                        {currentWord.flashcardPreview.options.map((opt, i) => (
                            <button key={i} className="block w-full text-left text-xs p-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded text-gray-700 dark:text-gray-200">
                            {opt} {opt === currentWord.flashcardPreview?.answer ? ' ✅' : ''} {/* Basic answer check for demo */}
                            </button>
                        ))}
                        </div>
                    )}
                     {currentWord.flashcardPreview.type === 'fill-in-blank' && (
                        <p className="text-sm mt-1 text-pink-600 dark:text-pink-200">Fill in the blank with: <span className="font-bold">{currentWord.flashcardPreview.prompt}</span></p>
                        // TODO: Actual input for fill-in-blank
                    )}
                </div>
            )}
            <div className="flex flex-wrap gap-2 mt-2">
                <button className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-md text-gray-700 dark:text-gray-200 transition-colors">Toggle ELI5</button>
                <button className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-md text-gray-700 dark:text-gray-200 transition-colors">Generate 3 More Examples</button>
            </div>
          </div>

          {/* 11. User Note & Tagging */}
          <div className="border-t pt-4 dark:border-gray-700">
            <h3 className="text-md font-semibold mb-2 text-gray-700 dark:text-gray-300">My Notes & Tags</h3>
            <div>
                <label htmlFor="userNote" className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Your personal note:</label>
                <textarea
                id="userNote"
                defaultValue={currentWord.userNote}
                placeholder="e.g., Used this when talking to my language partner..."
                className="w-full p-2.5 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm dark:bg-gray-700 dark:text-white"
                rows={3}
                />
            </div>
            <div className="mt-3">
                <label htmlFor="userTags" className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Custom tags (comma-separated):</label>
                <input
                    id="userTags"
                    type="text"
                    placeholder="e.g., travel, food, business"
                    defaultValue={currentWord.tags?.join(', ')}
                    className="w-full p-2.5 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm dark:bg-gray-700 dark:text-white"
                />
                {currentWord.tags && currentWord.tags.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                    {currentWord.tags.map((tag, index) => (
                        <span key={index} className="bg-gray-200 text-gray-700 px-2 py-0.5 rounded-full text-xs dark:bg-gray-600 dark:text-gray-300">
                        #{tag.trim()}
                        </span>
                    ))}
                    </div>
                )}
            </div>
             <button className="mt-4 w-full sm:w-auto px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-colors">
                Save Note & Tags
            </button>
          </div>
        </div>

        {/* Modal Footer Actions */}
        <div className="mt-6 pt-4 border-t dark:border-gray-700 flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 dark:bg-gray-600 dark:text-gray-200 dark:hover:bg-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-400 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-colors"
          >
            Close
          </button>
          {/* Example of another action button */}
          {/* 
          <button
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-800 transition-colors"
          >
            Mark as Learned
          </button> 
          */}
        </div>
      </div>
    </div>
  );
};

export default LearnWordModal; 