import React, { useState, useEffect } from 'react';
import {
  getEnrichedVocabularyDetails,
  generateMoreExamples,
  generateEli5,
  generateMiniQuiz,
  MoreExamplesRequest, // Import request types if needed for constructing payload
  ELI5Request,
  MiniQuizRequest,
  EnrichedVocabDetails
} from '../../../frontend/v0_lingua-log/lib/api'; // Corrected relative path

// Define the structure for the vocabulary word data
export interface VocabWordData {
  id: string; // Assuming an ID for each word
  word: string; // Word in native script (e.g., Japanese kanji/kana)
  romaji: string; // Romaji (or transliteration)
  language: string; // Language code (e.g., 'en', 'ja') - Added for consistency
  definition: string; // English definition
  exampleSentence?: string; // Example sentence from journal
  isGlobal?: boolean; // Whether it's in the user's global vocabulary or not
  partOfSpeech?: string; // e.g., noun, verb, adjective
  jlptLevel?: string; // e.g., N3, N2
  frequency?: 'Common' | 'Uncommon' | 'Rare'; // Frequency indicator
  audioUrl?: string; // URL for TTS audio playback
  secondaryDefinitions?: string[];
  synonyms?: Array<{ word: string; romaji?: string }>;
  antonyms?: Array<{ word: string; romaji?: string }>;
  relatedPhrases?: Array<{ phrase: string; meaning: string }>;
  conjugations?: { [key: string]: string }; // e.g., { 'Plain Form': 'する', 'Polite Form': 'します' }
  culturalNote?: string;
  aiCulturalExplanation?: string; // Placeholder for GPT-based explanation
  emotionTone?: string; // e.g., "nervous anticipation"
  mnemonic?: string; // e.g., "緊 (tight) + 張 (stretch) = tightly stretched nerves"
  emoji?: string; // e.g., 😰
  userNote?: string;
  tags?: string[];
  // Enhancements for more comprehensive placeholder data
  aiExampleSentences?: Array<{
    sentence: string;
    translation: string;
    complexity?: 'Beginner' | 'Intermediate' | 'Advanced';
  }>;
  eli5Explanation?: string;
  flashcardPreview?: {
    type: 'definition-match' | 'fill-in-blank';
    question: string; // For definition-match, this is the word; for fill-in-blank, this is the sentence with a blank
    prompt?: string; // For fill-in-blank, the word to fill in
    options?: string[]; // For definition-match, multiple choice definitions
    answer: string; // Correct definition or the word for the blank
  };
  // On-demand generated content
  miniQuiz?: MiniQuizData; // Structure to be defined or imported
}

// Define structure for MiniQuiz (can be moved to a types file if shared)
interface MiniQuizQuestionData {
  question_text: string;
  options: string[];
  correct_answer_index: number;
  explanation?: string;
}

interface MiniQuizData {
  quiz_title: string;
  questions: MiniQuizQuestionData[];
}

interface LearnWordModalProps {
  vocabEntry: VocabWordData;
  isOpen: boolean;
  onClose: () => void;
}

const LearnWordModal: React.FC<LearnWordModalProps> = ({ vocabEntry, isOpen, onClose }) => {
  if (!isOpen) return null;

  // State for initial enrichment
  const [enrichedData, setEnrichedData] = useState<EnrichedVocabDetails | null>(null);
  const [isLoadingEnrichment, setIsLoadingEnrichment] = useState(false);
  const [enrichmentError, setEnrichmentError] = useState<string | null>(null);

  // State for on-demand AI content
  const [additionalExamples, setAdditionalExamples] = useState<string[]>([]);
  const [isLoadingMoreExamples, setIsLoadingMoreExamples] = useState(false);
  const [moreExamplesError, setMoreExamplesError] = useState<string | null>(null);

  const [eli5Content, setEli5Content] = useState<string | null>(null);
  const [isLoadingEli5, setIsLoadingEli5] = useState(false);
  const [eli5Error, setEli5Error] = useState<string | null>(null);

  const [quizData, setQuizData] = useState<MiniQuizData | null>(null);
  const [isLoadingQuiz, setIsLoadingQuiz] = useState(false);
  const [quizError, setQuizError] = useState<string | null>(null);

  // Reset on-demand content when vocabEntry changes or modal opens
  useEffect(() => {
    if (isOpen) {
        setAdditionalExamples([]);
        setMoreExamplesError(null);
        setEli5Content(null);
        setEli5Error(null);
        setQuizData(null);
        setQuizError(null);
        
        // Clear previous enrichment data and errors
        setEnrichedData(null);
        setEnrichmentError(null);

        // Fetch initial enrichment data
        if (vocabEntry && vocabEntry.id && vocabEntry.language) { // Changed to vocabEntry.language
            setIsLoadingEnrichment(true);
            getEnrichedVocabularyDetails(vocabEntry.id, vocabEntry.language) // Changed to vocabEntry.language
                .then(data => {
                    setEnrichedData(data);
                })
                .catch(err => {
                    setEnrichmentError(err.message || "Failed to load enriched details.");
                })
                .finally(() => {
                    setIsLoadingEnrichment(false);
                });
        } else if (isOpen) {
            // Handle case where vocabEntry or its essential fields are missing
            setEnrichmentError("Cannot fetch enriched details: Vocabulary item data is incomplete.");
        }
    }        
  }, [isOpen, vocabEntry]); // vocabEntry directly in dependency array

  // Placeholder data - replace with actual data from vocabEntry
  const placeholderData: VocabWordData = {
    id: '1',
    word: '緊張',
    romaji: 'kinchou',
    language: 'en',
    definition: 'tension, nervousness, strain',
    exampleSentence: '大事なプレゼンテーションの前はいつも緊張します。',
    isGlobal: true,
    partOfSpeech: 'noun, verb (suru)',
    jlptLevel: 'N3',
    frequency: 'Common',
    audioUrl: 'https://example.com/audio/kinchou.mp3',
    secondaryDefinitions: ['mental stress', 'being keyed up'],
    synonyms: [{ word: '不安', romaji: 'fuan' }, { word: '心配', romaji: 'shinpai' }],
    antonyms: [{ word: 'リラックス', romaji: 'rirakkusu' }],
    relatedPhrases: [
      { phrase: '緊張する', meaning: 'to get nervous' },
      { phrase: '緊張が走る', meaning: 'tension runs high' },
    ],
    conjugations: {
      'Dictionary Form': '緊張する (kinchou suru)',
      'Masu Form': '緊張します (kinchou shimasu)',
      'Te Form': '緊張して (kinchou shite)',
      'Past Tense (Ta Form)': '緊張した (kinchou shita)',
      'Negative Form (Nai)': '緊張しない (kinchou shinai)',
    },
    culturalNote: 'Often used before giving speeches or important events in Japan, indicating a state of heightened awareness and pressure.',
    aiCulturalExplanation: 'Imagine you are about to go on stage for a big performance. That feeling of butterflies in your stomach and your heart beating a little faster? That\'s 緊張 (kinchou). In Japan, it\'s a common feeling before important tasks, showing you\'re taking it seriously.',
    emotionTone: 'Nervous anticipation, focused stress',
    mnemonic: 'Think of 緊 (tight) like a tightrope, and 張 (stretch) like stretching a bow. When you are nervous, your nerves are stretched tight like a tightrope walker\'s rope or a taut bowstring.',
    emoji: '😰',
    userNote: 'Felt this way before my first client meeting.',
    tags: ['#work', '#feelings', '#presentation'],
    // Added comprehensive placeholder fields
    aiExampleSentences: [
      {
        sentence: '会議中、彼は少し緊張しているように見えた。',
        translation: 'He looked a little nervous during the meeting.',
        complexity: 'Intermediate',
      },
      {
        sentence: '彼女は初めての飛行機で緊張を隠せなかった。',
        translation: 'She couldn\'t hide her nervousness on her first flight.',
        complexity: 'Advanced',
      },
    ],
    eli5Explanation: '緊張 (kinchou) is like when you have to do something new or important, and your tummy feels a bit wobbly like jelly, and your heart goes thump-thump fast! It means you really care about doing a good job!',
    flashcardPreview: {
      type: 'definition-match',
      question: '緊張 (kinchou)',
      options: [
        'Excitement, joy, happiness',
        'Tension, nervousness, strain',
        'Sadness, despair, grief',
        'Relaxation, calmness, peace',
      ],
      answer: 'Tension, nervousness, strain',
    },
    miniQuiz: undefined, // Initialize in placeholder if needed
  };

  const currentWord = (() => {
    // Prioritize fully enriched data if available
    if (enrichedData) {
      // Map EnrichedVocabDetails to VocabWordData structure
      // This mapping needs to be comprehensive based on how fields align.
      // For now, a partial mapping focusing on directly usable fields or slight transformations.
      return {
        ...vocabEntry, // Base from prop, provides things like userNote, tags etc.
        id: enrichedData.word_vocabulary_id || vocabEntry.id, // Prefer ID from vocab item if cache ID is different
        word: vocabEntry.word, // Keep original word, romaji from vocabEntry as source of truth
        romaji: vocabEntry.romaji,
        language: enrichedData.language || vocabEntry.language, // Use enriched or fallback to vocabEntry's language
        definition: enrichedData.ai_definitions && enrichedData.ai_definitions.length > 0 
                      ? enrichedData.ai_definitions[0].definition 
                      : vocabEntry.definition,
        secondaryDefinitions: enrichedData.ai_definitions && enrichedData.ai_definitions.length > 1 
                              ? enrichedData.ai_definitions.slice(1).map(d => d.definition) 
                              : vocabEntry.secondaryDefinitions,
        aiExampleSentences: enrichedData.ai_example_sentences?.map(s => ({ sentence: s, translation: '' })) || vocabEntry.aiExampleSentences,
        synonyms: enrichedData.ai_synonyms?.map(s => ({ word: s })) || vocabEntry.synonyms,
        antonyms: enrichedData.ai_antonyms?.map(a => ({ word: a })) || vocabEntry.antonyms,
        relatedPhrases: enrichedData.ai_related_phrases?.map(p => ({ phrase: p, meaning: '' })) || vocabEntry.relatedPhrases, // Meaning might need separate fetching or be part of phrase
        culturalNote: enrichedData.ai_cultural_note || vocabEntry.culturalNote,
        // aiCulturalExplanation could map to ai_cultural_note or be a specific field if added to EnrichedVocabDetails
        // emotionTone, mnemonic, emoji are not directly in EnrichedVocabDetails, rely on vocabEntry or need specific AI calls
        // eli5Explanation: if enrichedData contains a specific ELI5 field, map it here.
      } as VocabWordData; // Type assertion
    }
    // Fallback to vocabEntry or placeholderData
    return vocabEntry || placeholderData;
  })();

  // Placeholder API call functions - to be implemented later
  const handleGenerateMoreExamples = async () => {
    if (!currentWord.word || !currentWord.romaji) { // Ensure word and language (romaji as proxy for lang here) are present
        setMoreExamplesError("Word details are missing to generate examples.");
        return;
    }
    setIsLoadingMoreExamples(true);
    setMoreExamplesError(null);
    try {
      const requestPayload: MoreExamplesRequest = {
        word: currentWord.word, // Assuming currentWord.word is the term itself
        language: currentWord.language || 'en', // Assuming language_code is available, or default
        // existing_examples: currentWord.aiExampleSentences?.map(ex => ex.sentence), // Optional: send existing to avoid duplicates
      };
      const response = await generateMoreExamples(requestPayload);
      setAdditionalExamples(prev => [...prev, ...response.new_example_sentences]);
    } catch (error: any) {
      setMoreExamplesError(error.message || "Failed to load examples. Please try again.");
    } finally {
      setIsLoadingMoreExamples(false);
    }
  };

  const handleGenerateEli5 = async () => {
    if (!currentWord.word || !currentWord.romaji) { 
        setEli5Error("Word details are missing for ELI5.");
        return;
    }
    setIsLoadingEli5(true);
    setEli5Error(null);
    try {
      const requestPayload: ELI5Request = {
        term: currentWord.word, // Or currentWord.term if that is the intended field
        language: currentWord.language || 'en', // Changed to currentWord.language
      };
      const response = await generateEli5(requestPayload);
      setEli5Content(response.explanation);
    } catch (error: any) {
      setEli5Error(error.message || "Could not get ELI5. Try again?");
    } finally {
      setIsLoadingEli5(false);
    }
  };

  const handleGenerateQuiz = async () => {
    if (!currentWord.word || !currentWord.romaji) { 
        setQuizError("Word details are missing for Quiz generation.");
        return;
    }
    setIsLoadingQuiz(true);
    setQuizError(null);
    try {
      const requestPayload: MiniQuizRequest = {
        word: currentWord.word,
        language: currentWord.language || 'en', // Changed to currentWord.language
      };
      const response = await generateMiniQuiz(requestPayload);
      // Assuming MiniQuizData on frontend matches MiniQuizResponse from backend
      setQuizData(response);
    } catch (error: any) {
      setQuizError(error.message || "Quiz generation failed.");
    } finally {
      setIsLoadingQuiz(false);
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
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {currentWord.jlptLevel && <span className="mr-2">{currentWord.jlptLevel}</span>}
              {currentWord.frequency && <span className="mr-2">{currentWord.frequency}</span>}
              {currentWord.partOfSpeech && <span>({currentWord.partOfSpeech})</span>}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            aria-label="Close modal"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-6 h-6">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Display loading/error for initial enrichment */}
        {isLoadingEnrichment && (
            <div className="my-4 p-4 text-center bg-blue-50 dark:bg-blue-900 dark:bg-opacity-25 rounded">
                <p className="text-blue-600 dark:text-blue-300">Loading enhanced details...</p>
            </div>
        )}
        {enrichmentError && !isLoadingEnrichment && (
            <div className="my-4 p-3 bg-red-50 dark:bg-red-900 dark:bg-opacity-25 rounded">
                <p className="text-red-600 dark:text-red-300 text-sm">Error: {enrichmentError}</p>
            </div>
        )}

        {/* Placeholder for all sections */}
        <div className="space-y-6">
          {/* 1. Word Header (already partially done) - Audio Playback */}
          {currentWord.audioUrl && (
            <div className="border-b pb-4 dark:border-gray-700">
              <h3 className="text-lg font-semibold mb-2 text-gray-800 dark:text-gray-200">Audio</h3>
              <audio controls src={currentWord.audioUrl} className="w-full">
                Your browser does not support the audio element.
              </audio>
            </div>
          )}

          {/* 2. Definitions + Part of Speech (Primary definition already in header) */}
          <div className="border-b pb-4 dark:border-gray-700">
            <h3 className="text-lg font-semibold mb-2 text-gray-800 dark:text-gray-200">Definitions</h3>
            <p className="text-gray-700 dark:text-gray-300">{currentWord.definition}</p>
            {currentWord.secondaryDefinitions && currentWord.secondaryDefinitions.length > 0 && (
              <ul className="list-disc list-inside mt-2 text-sm text-gray-600 dark:text-gray-400">
                {currentWord.secondaryDefinitions.map((def, index) => (
                  <li key={index}>{def}</li>
                ))}
              </ul>
            )}
          </div>

          {/* 3. Example Sentences */}
          {(currentWord.exampleSentence || currentWord.aiCulturalExplanation) && ( // Simplified condition for now
            <div className="border-b pb-4 dark:border-gray-700">
              <h3 className="text-lg font-semibold mb-2 text-gray-800 dark:text-gray-200">Example Sentences</h3>
              {currentWord.exampleSentence && (
                 <div className="mb-2 p-3 bg-gray-50 dark:bg-gray-700 rounded">
                    <p className="text-gray-700 dark:text-gray-300 italic">"{currentWord.exampleSentence}"</p>
                    {/* TODO: Highlight word in sentence */}
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1"> (From your journal)</p>
                 </div>
              )}
              {/* Placeholder for AI-generated examples */}
               {/* <button className="text-sm text-blue-500 hover:underline">Generate more examples</button> */}
               {currentWord.aiExampleSentences && currentWord.aiExampleSentences.length > 0 && (
                <div className="mt-3">
                  <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-1">AI Generated Examples:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-gray-600 dark:text-gray-400">
                    {currentWord.aiExampleSentences.map((ex, index) => (
                      <li key={`ai-ex-${index}`}>
                        {ex.sentence}
                        {ex.translation && <span className="italic text-gray-500 dark:text-gray-500"> - {ex.translation}</span>}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {additionalExamples.length > 0 && (
                <div className="mt-3">
                  <h4 className="font-medium text-gray-700 dark:text-gray-300 mb-1">More AI Examples:</h4>
                  <ul className="list-disc list-inside space-y-1 text-sm text-gray-600 dark:text-gray-400">
                    {additionalExamples.map((ex, index) => (
                      <li key={`add-ex-${index}`}>{ex}</li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="mt-3">
                <button 
                    onClick={handleGenerateMoreExamples} 
                    disabled={isLoadingMoreExamples}
                    className="text-sm text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoadingMoreExamples ? 'Generating...' : 'Show 3 More Examples'}
                </button>
                {moreExamplesError && <p className="text-xs text-red-500 mt-1">{moreExamplesError}</p>}
              </div>
            </div>
          )}

          {/* 4. Synonyms & Antonyms */}
          {(currentWord.synonyms?.length || currentWord.antonyms?.length) && (
            <div className="border-b pb-4 dark:border-gray-700">
              <h3 className="text-lg font-semibold mb-2 text-gray-800 dark:text-gray-200">Synonyms & Antonyms</h3>
              {currentWord.synonyms && currentWord.synonyms.length > 0 && (
                <div className="mb-2">
                  <h4 className="font-medium text-gray-700 dark:text-gray-300">Synonyms:</h4>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {currentWord.synonyms.map((syn, index) => (
                      <button key={index} className="bg-blue-100 text-blue-700 px-2 py-1 rounded-md text-sm hover:bg-blue-200 dark:bg-blue-700 dark:text-blue-100 dark:hover:bg-blue-600">
                        {syn.word} {syn.romaji && `(${syn.romaji})`}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {currentWord.antonyms && currentWord.antonyms.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-700 dark:text-gray-300">Antonyms:</h4>
                   <div className="flex flex-wrap gap-2 mt-1">
                    {currentWord.antonyms.map((ant, index) => (
                      <button key={index} className="bg-green-100 text-green-700 px-2 py-1 rounded-md text-sm hover:bg-green-200 dark:bg-green-700 dark:text-green-100 dark:hover:bg-green-600">
                        {ant.word} {ant.romaji && `(${ant.romaji})`}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 5. Related Phrases / Collocations */}
          {currentWord.relatedPhrases && currentWord.relatedPhrases.length > 0 && (
            <div className="border-b pb-4 dark:border-gray-700">
              <h3 className="text-lg font-semibold mb-2 text-gray-800 dark:text-gray-200">Related Phrases</h3>
              <ul className="list-disc list-inside text-gray-700 dark:text-gray-300">
                {currentWord.relatedPhrases.map((phrase, index) => (
                  <li key={index}>
                    <strong>{phrase.phrase}</strong>: {phrase.meaning}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 6. Conjugation Chart (if verb/adjective) */}
          {currentWord.conjugations && Object.keys(currentWord.conjugations).length > 0 && (
            <div className="border-b pb-4 dark:border-gray-700">
              <h3 className="text-lg font-semibold mb-2 text-gray-800 dark:text-gray-200">Conjugation Chart</h3>
              <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                {Object.entries(currentWord.conjugations).map(([form, value]) => (
                  <div key={form} className="flex justify-between">
                    <span className="text-gray-600 dark:text-gray-400">{form}:</span>
                    <span className="font-medium text-gray-800 dark:text-gray-200">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 7. Cultural Note / Usage Insight */}
          {(currentWord.culturalNote || currentWord.aiCulturalExplanation) && (
            <div className="border-b pb-4 dark:border-gray-700">
              <h3 className="text-lg font-semibold mb-2 text-gray-800 dark:text-gray-200">Cultural Insight</h3>
              {currentWord.culturalNote && <p className="text-gray-700 dark:text-gray-300 mb-2">{currentWord.culturalNote}</p>}
              {currentWord.aiCulturalExplanation && (
                <div>
                  <h4 className="font-medium text-gray-600 dark:text-gray-400 text-sm mb-1">AI Explanation for Beginners:</h4>
                  <p className="text-gray-700 dark:text-gray-300 italic bg-yellow-50 dark:bg-yellow-900 p-2 rounded">{currentWord.aiCulturalExplanation}</p>
                </div>
              )}
            </div>
          )}
          
          {/* 8. Emotion/Tone */}
          {currentWord.emotionTone && (
             <div className="border-b pb-4 dark:border-gray-700">
                <h3 className="text-lg font-semibold mb-2 text-gray-800 dark:text-gray-200">Emotion/Tone</h3>
                <p className="text-gray-700 dark:text-gray-300">{currentWord.emotionTone} {currentWord.emoji && <span>{currentWord.emoji}</span>}</p>
             </div>
          )}

          {/* 9. Mnemonic or Metaphor */}
          {currentWord.mnemonic && (
            <div className="border-b pb-4 dark:border-gray-700">
              <h3 className="text-lg font-semibold mb-2 text-gray-800 dark:text-gray-200">Mnemonic / Metaphor</h3>
              <p className="text-gray-700 dark:text-gray-300">{currentWord.mnemonic}</p>
            </div>
          )}

          {/* 10. Optional Enhancements (Placeholders) */}
          <div className="border-b pb-4 dark:border-gray-700">
            <h3 className="text-lg font-semibold mb-2 text-gray-800 dark:text-gray-200">Optional Enhancements</h3>
            <div className="space-y-2">
                <button className="text-sm text-blue-500 hover:underline dark:text-blue-400">Explain Like I'm 5</button><br/>
                <button className="text-sm text-blue-500 hover:underline dark:text-blue-400">Generate 3 more example sentences</button>
                {/* Flashcard preview could be a small component here */}
            </div>
          </div>

          {/* 11. User Note & Tagging */}
          <div className="pb-4">
            <h3 className="text-lg font-semibold mb-2 text-gray-800 dark:text-gray-200">My Notes & Tags</h3>
            <textarea
              defaultValue={currentWord.userNote}
              placeholder="Add your personal note..."
              className="w-full p-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              rows={3}
            />
            <div className="mt-2">
              <input
                type="text"
                placeholder="Add tags (comma-separated)..."
                defaultValue={currentWord.tags?.join(', ')}
                className="w-full p-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 dark:text-white"
              />
              {/* Display tags */}
              {currentWord.tags && currentWord.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {currentWord.tags.map((tag, index) => (
                    <span key={index} className="bg-gray-200 text-gray-700 px-2 py-1 rounded-full text-xs dark:bg-gray-600 dark:text-gray-200">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>
             <button className="mt-3 px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600">
                Save Note & Tags
            </button>
          </div>

          {/* NEW: ELI5 Section */}
          <div className="border-b pb-4 dark:border-gray-700">
            <h3 className="text-lg font-semibold mb-2 text-gray-800 dark:text-gray-200">Explain Like I'm 5 (ELI5)</h3>
            {eli5Content && (
                <div className="p-3 bg-yellow-50 dark:bg-yellow-900 dark:bg-opacity-25 rounded text-sm text-gray-700 dark:text-gray-300">
                    {eli5Content}
                </div>
            )}
            {currentWord.eli5Explanation && !eli5Content && (
                 <div className="p-3 bg-yellow-50 dark:bg-yellow-900 dark:bg-opacity-25 rounded text-sm text-gray-700 dark:text-gray-300">
                    <p className="italic">(Saved ELI5)</p>
                    {currentWord.eli5Explanation}
                </div>
            )}
            <div className="mt-3">
                <button 
                    onClick={handleGenerateEli5} 
                    disabled={isLoadingEli5}
                    className="text-sm text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoadingEli5 ? 'Explaining...' : (eli5Content || currentWord.eli5Explanation ? 'Explain Again' : 'Explain It Simply')}
                </button>
                {eli5Error && <p className="text-xs text-red-500 mt-1">{eli5Error}</p>}
            </div>
          </div>

          {/* NEW: Mini Quiz Section */}
          <div className="border-b pb-4 dark:border-gray-700">
            <h3 className="text-lg font-semibold mb-2 text-gray-800 dark:text-gray-200">Mini Quiz</h3>
            {quizData && (
                <div className="p-3 bg-indigo-50 dark:bg-indigo-900 dark:bg-opacity-25 rounded space-y-3">
                    <h4 className="font-medium text-gray-800 dark:text-gray-200">{quizData.quiz_title}</h4>
                    {quizData.questions.map((q, idx) => (
                        <div key={idx} className="text-sm">
                            <p className="font-semibold text-gray-700 dark:text-gray-300">{idx + 1}. {q.question_text}</p>
                            <ul className="list-disc list-inside ml-4 mt-1 space-y-1">
                                {q.options.map((opt, oIdx) => (
                                    <li key={oIdx} className="text-gray-600 dark:text-gray-400">
                                        {opt}
                                        {/* Basic display, not interactive yet */}
                                        {oIdx === q.correct_answer_index && <span className="text-green-500 ml-2">(Correct)</span>}
                                    </li>
                                ))}
                            </ul>
                            {q.explanation && <p className="text-xs italic text-gray-500 dark:text-gray-500 mt-1">Explanation: {q.explanation}</p>}
                        </div>
                    ))}
                </div>
            )}
             {currentWord.miniQuiz && !quizData && (
                 <div className="p-3 bg-indigo-50 dark:bg-indigo-900 dark:bg-opacity-25 rounded text-sm text-gray-700 dark:text-gray-300">
                    <p className="italic">(Saved Mini Quiz)</p>
                    {/* Render saved quiz data if available */}
                </div>
            )}
            <div className="mt-3">
                <button 
                    onClick={handleGenerateQuiz} 
                    disabled={isLoadingQuiz}
                    className="text-sm text-blue-600 dark:text-blue-400 hover:underline disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoadingQuiz ? 'Generating Quiz...' : (quizData || currentWord.miniQuiz ? 'Generate New Quiz' : 'Generate Mini Quiz') }
                </button>
                {quizError && <p className="text-xs text-red-500 mt-1">{quizError}</p>}
            </div>
          </div>

        </div>

        {/* Modal Footer Actions */}
        <div className="mt-6 flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
          >
            Close
          </button>
          {/* Additional actions like "Mark as Learned" could go here */}
        </div>
      </div>
    </div>
  );
};

export default LearnWordModal; 