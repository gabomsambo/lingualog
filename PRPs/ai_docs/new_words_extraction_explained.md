# How "New Words from This Entry" Works - Complete Explanation

## 🎯 Quick Answer

The AI model (GPT-4o-mini) **automatically identifies** 2-5 notable vocabulary words from your journal entry based on a set of intelligent criteria. It's not random - the AI uses linguistic analysis to pick words that would be **most valuable for your learning**.

---

## 📋 The Decision Process (Step-by-Step)

### Step 1: You Submit a Journal Entry

When you write and submit a journal entry, the text is sent to the backend API endpoint `/log-entry`.

**Example:**
```
Entry text: "MIRA FUNCTIONA porque no quieres funcionar habibi porfacor funciona"
Language: Spanish (es)
```

### Step 2: Journal Analysis Agent Receives Instructions

The system prompt tells the AI **exactly what to look for** when extracting words.

**Location:** `backend/agents/core/journal_analysis_agent.py` (line 59)

**The Instruction:**
```python
"9. Extract 2-5 notable vocabulary words that are advanced,
    incorrectly used, or worth learning."
```

**Full System Instructions (lines 44-71):**
```python
steps=[
    "1. Read and understand the journal entry text and identify the language being used.",
    "2. Analyze the text for grammar errors, awkward phrasing, and areas for improvement.",
    "3. Assess the overall fluency level and assign appropriate scores for grammar, vocabulary, and complexity.",
    "4. Identify the emotional tone and style of the writing.",
    "5. Create a grammar-corrected version that fixes errors while preserving the original meaning and voice.",
    "6. Generate a more natural, native-like rewrite that improves flow and naturalness.",
    "7. Translate the original text appropriately (to English if not English, to French if already English).",
    "8. Identify 3-5 specific grammar suggestions with explanations.",
    "9. Extract 2-5 notable vocabulary words that are advanced, incorrectly used, or worth learning.",  # ← THIS IS THE KEY
    "10. Provide a brief, encouraging explanation of the main points for improvement."
]
```

### Step 3: AI's Selection Criteria

The AI model uses these criteria to decide which words to extract:

#### ✅ Words That GET Selected:

1. **Advanced vocabulary**
   - Words above the user's proficiency level
   - Example: In a beginner's entry, "habibi" (Arabic loanword) would be flagged as advanced/notable

2. **Incorrectly used words**
   - Words that are misspelled or used in wrong context
   - Example: "FUNCTIONA" instead of "funciona"
   - Example: "porfacor" instead of "por favor"

3. **Cultural/borrowed words**
   - Loanwords from other languages
   - Example: "habibi" (Arabic word used in Spanish context)

4. **Words worth learning**
   - Key vocabulary for the learner's level
   - High-frequency words the learner should master
   - Words that appear multiple times in the entry (shows learner is trying to use them)

5. **Context-rich words**
   - Words that have interesting usage patterns
   - Words that can be explained with good examples

#### ❌ Words That DON'T Get Selected:

1. **Common filler words** (e.g., "the", "a", "is", "and")
2. **Correctly used simple vocabulary** already at learner's level
3. **Proper nouns** (unless culturally significant)
4. **Words already in user's saved vocabulary** (system already knows they're learning it)

### Step 4: AI Generates Rich Metadata for Each Word

For each selected word, the AI creates a structured object with:

**Data Structure** (`backend/agents/schemas/journal_schemas.py` lines 21-30):

```python
class NewWord(BaseModel):
    term: str              # The actual word/phrase
    reading: Optional[str] # Pronunciation (e.g., for Japanese: "学生" → "がくせい")
    pos: str              # Part of speech (noun, verb, adjective, etc.)
    definition: str       # Clear English definition
    example: str          # Example sentence using the word
    proficiency: str      # Estimated level (beginner/intermediate/advanced)
```

**Example Output for "habibi":**
```json
{
  "term": "habibi",
  "reading": null,
  "pos": "noun",
  "definition": "Arabic term of endearment meaning 'my dear' or 'my love'",
  "example": "Habibi, ven aquí (Honey, come here)",
  "proficiency": "intermediate"
}
```

### Step 5: Words Are Stored with the Journal Entry

The extracted words are saved in the database as part of the entry's `ai_feedback` field.

**Database:** `journal_entries` table
**Field:** `new_words` (JSONB array)

```sql
-- Simplified schema
journal_entries (
  id UUID,
  content TEXT,
  new_words JSONB,  -- ← Stores the extracted words array
  ...
)
```

### Step 6: Frontend Displays the Words

The entry detail page (`app/(app)/entries/[id]/page.tsx`) retrieves the entry and passes the `new_words` array to the `VocabularyPanel` component.

**Component Flow:**
```
EntryDetailPage
  └─> VocabularyPanel
      └─> Displays each word with:
          - Term
          - Part of speech badge
          - Definition
          - Example sentence
          - Proficiency level
          - Save button (to add to user's vocabulary)
```

---

## 🧠 Why This Approach Works

### 1. **AI Linguistic Intelligence**
The AI model (GPT-4o-mini) has been trained on massive amounts of multilingual text, so it "understands":
- What words are advanced vs. basic in each language
- Common mistakes learners make
- Cultural context of words
- Appropriate proficiency levels

### 2. **Context-Aware Selection**
The AI looks at:
- **Your entry as a whole** (not just individual words)
- **How words are used** (correct vs. incorrect usage)
- **Your proficiency level** (passed as `user_level` parameter)
- **The language you're learning** (Spanish, French, Japanese, etc.)

### 3. **Educational Value**
Words are selected to **maximize learning**:
- Focus on mistakes to help you improve
- Highlight advanced vocabulary to expand your skills
- Provide clear examples to reinforce learning

---

## 🔍 Real Example Breakdown

### Your Entry:
```
"MIRA FUNCTIONA porque no quieres funcionar habibi porfacor funciona"
```

### AI's Analysis Process:

1. **Identifies the language:** Spanish
2. **Detects errors:**
   - "FUNCTIONA" → should be "funciona"
   - "porfacor" → should be "por favor"
3. **Finds notable words:**
   - "habibi" → Arabic loanword (culturally interesting, not standard Spanish)
   - "funcionar" → Key verb being practiced (appears 3 times, shows learner focus)

### Words Extracted (Likely):

**Word 1: "habibi"**
- **Why selected:** Arabic loanword, culturally notable, informal register
- **Part of speech:** noun
- **Definition:** "Arabic term of endearment meaning 'my dear' or 'darling'"
- **Example:** "Ven aquí, habibi" (Come here, darling)
- **Proficiency:** intermediate

**Word 2: "funcionar"**
- **Why selected:** Core vocabulary, practiced multiple times in entry
- **Part of speech:** verb
- **Definition:** "to work, to function, to operate"
- **Example:** "El teléfono no funciona" (The phone doesn't work)
- **Proficiency:** beginner

---

## 🛠️ Technical Implementation Details

### Backend Code References

**1. Agent Definition:**
- File: `backend/agents/core/journal_analysis_agent.py`
- Key lines: 44-71 (system prompt with extraction instruction)
- Key lines: 100-138 (analyze method that runs the AI)

**2. Schema Definition:**
- File: `backend/agents/schemas/journal_schemas.py`
- Lines 21-30: `NewWord` class definition
- Lines 63-66: `new_words` field in output schema

**3. API Endpoint:**
- File: `backend/server.py`
- Endpoint: `POST /log-entry`
- The agent is called, analyzes text, returns `new_words` array

### Frontend Code References

**1. Entry Display:**
- File: `frontend/v0_lingua-log/app/(app)/entries/[id]/page.tsx`
- Retrieves entry with `new_words` from API
- Passes to `VocabularyPanel`

**2. Vocabulary Panel:**
- File: `frontend/v0_lingua-log/components/vocabulary-panel.tsx`
- Renders each word with save/unsave functionality
- Shows word details, examples, proficiency

---

## 💡 Customization Options

### If You Want to Change the Selection Criteria:

**Modify the system prompt** in `backend/agents/core/journal_analysis_agent.py`:

```python
# Current (line 59):
"9. Extract 2-5 notable vocabulary words that are advanced, incorrectly used, or worth learning."

# Could change to:
"9. Extract 3-7 vocabulary words focusing on verbs and advanced adjectives."
# Or:
"9. Extract 5-10 words that the user misspelled or used incorrectly."
# Or:
"9. Extract all proper nouns and cultural references from the text."
```

### If You Want More/Fewer Words:

Change the range in the instruction:
- Current: "2-5 notable vocabulary words"
- More words: "5-10 notable vocabulary words"
- Fewer words: "1-3 most important vocabulary words"

---

## 🎓 Educational Philosophy

The system is designed around these principles:

1. **Learn from mistakes** - Highlight words you used incorrectly
2. **Expand vocabulary** - Introduce advanced words naturally encountered
3. **Cultural awareness** - Flag interesting cultural/loanwords
4. **Spaced repetition** - Save words for future review
5. **Contextual learning** - Always show words in sentence context

---

## 🔮 Behind the Scenes: AI Magic

What the AI model actually does (simplified):

```
1. Parse entry text → "MIRA FUNCTIONA porque..."
2. Tokenize words → ["MIRA", "FUNCTIONA", "porque", "no", ...]
3. Analyze each word:
   - Check spelling against Spanish dictionary
   - Assess difficulty level
   - Evaluate cultural significance
   - Consider learner's proficiency
4. Rank words by "learning value"
5. Select top 2-5 words
6. Generate metadata (definition, example, etc.)
7. Return structured JSON response
```

The model uses:
- **Language models** trained on billions of words
- **Linguistic rules** for each language
- **Statistical analysis** of word frequency and difficulty
- **Context understanding** to evaluate proper usage

---

## 📊 Summary

**Decision Process:**
1. ✅ AI receives your journal entry
2. ✅ AI analyzes text for errors, difficulty, cultural elements
3. ✅ AI selects 2-5 words based on learning value criteria
4. ✅ AI generates rich metadata for each word
5. ✅ Words are stored with entry and displayed in UI

**Selection Criteria:**
- Advanced vocabulary above learner's level
- Incorrectly used or misspelled words
- Cultural/borrowed words (loanwords)
- High-value words worth mastering
- Words used multiple times (shows learner focus)

**Why It Works:**
- Powered by GPT-4o-mini's linguistic intelligence
- Context-aware (understands your whole entry)
- Educationally optimized (maximizes learning value)
- Consistent criteria across all languages

The system is **smart, adaptive, and focused on your learning journey**! 🚀

---

**Last Updated:** 2025-01-05
**Model Used:** GPT-4o-mini via OpenAI
**Framework:** Atomic Agents 2.1.0+
