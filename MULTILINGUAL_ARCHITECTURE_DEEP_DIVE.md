# Multilingual Architecture: Deep Dive Analysis

## Table of Contents
1. [How Advanced Settings Work](#how-advanced-settings-work)
2. [Current Prompt Strategy](#current-prompt-strategy)
3. [Translation Strategy Options](#translation-strategy-options)
4. [Lara Translate Integration Approaches](#lara-translate-integration-approaches)
5. [Recommendations](#recommendations)

---

## 1. How Advanced Settings Work

### Question: Are these just affecting prompts or does it matter?

**Answer: They ONLY affect prompts. No code logic changes based on these settings.**

### Current Implementation Flow

```
User Settings (DB)
    ↓
resolve_effective() → EffectiveSettings
    ↓
explanation_instruction() → English text instructions
    ↓
build_messages() → System prompt with instructions
    ↓
AI Model → Interprets instructions → Outputs in appropriate language(s)
```

### How Each Setting Works

#### 1. **explanationMode** (native_only, target_only, bilingual, smart)

**What it does:**
```python
# From lang_policy.py:191-195
explanations = {
    'native_only': f"Provide all explanations in {l1_name} only.",
    'target_only': f"Provide all explanations in {l2_name} only.",
    'bilingual': f"Provide explanations in both {l1_name} and {l2_name}.",
    'smart': f"Provide explanations primarily in {l1_name}, with key terms in {l2_name}."
}
```

**Example Output:**
- Setting: `bilingual` (English native, Spanish target)
- AI receives: "Provide explanations in both English and Spanish."
- AI returns: Explanations like:
  ```
  "You used 'fui' (I went) correctly here. 'Ir' is irregular: voy, fui, he ido..."
  ```

**Impact:**
- ✅ Affects: Language of explanation text in response
- ❌ Does NOT affect: API logic, data storage, routing, or validation

#### 2. **strictness** (gentle, medium, strict, pedantic)

**What it does:**
```python
# From lang_policy.py:198-203
strictness_instructions = {
    'gentle': "Be encouraging and focus on positive reinforcement. Only point out major errors.",
    'medium': "Provide balanced feedback with both corrections and encouragement.",
    'strict': "Be thorough in corrections and point out all errors, including minor ones.",
    'pedantic': "Provide extremely detailed corrections including style and advanced grammar rules."
}
```

**Example Output:**
- Setting: `pedantic`
- AI receives: "Provide extremely detailed corrections including style and advanced grammar rules."
- AI behavior: Flags subjunctive mood errors, comma splices, register mismatches, etc.

**Impact:**
- ✅ Affects: Number and depth of grammar_suggestions, tone of feedback
- ❌ Does NOT affect: Scoring algorithm (AI interprets, not hardcoded)

#### 3. **formality** (casual, neutral, formal, academic)

**What it does:**
```python
# From lang_policy.py:205-209
formality_instructions = {
    'casual': "Use a friendly, conversational tone.",
    'neutral': "Use a professional but approachable tone.",
    'formal': "Use a formal, academic tone.",
    'academic': "Use scholarly language appropriate for academic writing."
}
```

**Example Output:**
- Setting: `casual`
- AI tone: "Hey, nice work! Just a heads up about 'fui' vs 'fue'..."
- Setting: `academic`
- AI tone: "The preterite conjugation demonstrates appropriate temporal reference; however, consider..."

**Impact:**
- ✅ Affects: Tone and register of explanations and corrections
- ❌ Does NOT affect: Quality of corrections (same errors caught, different presentation)

### Key Insight

**These settings are "soft constraints" - they guide AI behavior through natural language, not code logic.**

**Pros:**
- ✅ Flexible - easy to add new settings without code changes
- ✅ Nuanced - AI can interpret complex combinations naturally
- ✅ Maintainable - changes don't require algorithm updates

**Cons:**
- ⚠️ Non-deterministic - AI may interpret differently across runs
- ⚠️ Hard to test - no unit tests for "gentle vs strict" behavior
- ⚠️ Model-dependent - different models may interpret differently

---

## 2. Current Prompt Strategy

### System Prompt Language: **English Only**

```python
# From prompt_builder.py:16
# System template for AI analysis (always in English for consistency)
SYSTEM_TEMPLATE = """You are an expert language learning assistant...
```

### Why English Prompts?

**Current Rationale:**
1. **Consistency**: English is lingua franca for AI models
2. **Model Training**: Most LLMs are primarily trained on English instructions
3. **Performance**: English prompts generally produce better structured outputs
4. **Debugging**: Easier for developers to debug and iterate

### How Multilingual Outputs Work

**Current Flow:**
```
English System Prompt:
  "You are a language learning assistant..."
  "Provide explanations in Spanish only."  ← Settings-driven instruction

User Payload:
  {
    "target_language": "es",
    "native_language": "en",
    "entry_text": "Hoy fui al mercado..."
  }

AI Model:
  - Reads English instructions
  - Understands to explain in Spanish
  - Outputs explanation in Spanish
```

**Example:**
```json
{
  "explanation": "Has escrito 'fui al mercado' correctamente. 'Ir' es un verbo irregular en pretérito perfecto simple...",
  "corrected": "Hoy fui al mercado y compré verduras.",
  "translation": "Today I went to the market..."
}
```

### Current Approach Effectiveness

**What Works Well:**
- ✅ Corrected text (L2) - Always accurate
- ✅ Rewritten text (L2) - Native-like quality
- ✅ Grammar suggestions - Technically correct
- ✅ Tone detection - Works across languages
- ✅ Translations - Good quality

**Potential Issues:**
- ⚠️ Explanations in non-Latin scripts (Arabic, Japanese, Chinese) - May be less natural
- ⚠️ Cultural nuances - English prompt may miss culture-specific pedagogical patterns
- ⚠️ Formality levels - English "formal" ≠ Japanese "keigo" ≠ French "vouvoiement"

---

## 3. Translation Strategy Options

### Option A: **Keep English Prompts + AI Handles Multilingual Output** (Current)

**Architecture:**
```
Prompt Builder (English) → AI Model → Multilingual Response
```

**Pros:**
- ✅ Simple architecture - no translation layer needed
- ✅ Proven approach - this is how most multilingual apps work
- ✅ Fast - single AI call
- ✅ Context-aware - AI understands language nuances
- ✅ Cost-effective - one API call

**Cons:**
- ⚠️ Explanation quality may vary for non-Western languages
- ⚠️ Cultural pedagogy - English teaching style ≠ Japanese teaching style
- ⚠️ No explicit control over translation quality

**Best For:**
- Users learning languages with Latin scripts (Spanish, French, German, Italian, Portuguese)
- Intermediate to advanced learners
- Cost-sensitive deployments

---

### Option B: **Translate System Prompts to L1 (Native Language)**

**Architecture:**
```
English Prompt → Lara Translate → L1 Prompt → AI Model → Response
```

**Example:**
For Japanese native speaker learning French:
```
1. English prompt: "You are a language learning assistant..."
2. Lara translates to Japanese: "あなたは言語学習アシスタントです..."
3. AI receives Japanese instructions
4. AI outputs in Japanese (explanations) and French (corrections)
```

**Pros:**
- ✅ More natural explanations in learner's native language
- ✅ Cultural pedagogy - teaching style matches L1 culture
- ✅ Better formality control (keigo, vouvoiement, etc.)
- ✅ Clearer for non-English speakers

**Cons:**
- ❌ Extra API call (Lara translate) - adds 100-200ms latency
- ❌ Extra cost (~$0.0001 per translation)
- ❌ Complexity - translation caching needed
- ❌ Potential translation errors in prompts
- ❌ Harder to debug - prompts no longer in English

**Best For:**
- Users with native languages very different from English (CJK, Arabic, RTL)
- Beginners who need maximum clarity
- Premium tier users

---

### Option C: **Hybrid: English Prompts + Lara for Translation Field Only**

**Architecture:**
```
English Prompt → AI Model → Response with translation field
                                      ↓ (if needed)
                              Lara Translate → High-quality translation
```

**Example:**
```json
{
  "corrected": "Hoy fui al mercado.",     // From AI
  "explanation": "Good use of preterite...", // From AI
  "translation": "Today I went to market"   // From Lara (if policy requires)
}
```

**Pros:**
- ✅ Best translation quality - Lara is specialized
- ✅ Consistency - Lara uses translation memory
- ✅ Lower latency than Option B - only one field translated
- ✅ Cost-effective - only translate when policy requires
- ✅ Debugging stays easy - prompts in English

**Cons:**
- ⚠️ Complexity - two AI systems to manage
- ⚠️ Not needed for most cases - AI does good translations already
- ⚠️ Inconsistency - some fields from AI, some from Lara

**Best For:**
- Professional/enterprise users who need perfect translations
- Legal/medical language learning (high accuracy requirements)
- Users who need translation memory (domain-specific terminology)

---

### Option D: **Smart Hybrid: Multilingual Prompts for Non-Western Languages**

**Architecture:**
```
resolve_effective() checks L1:
  - If L1 in [en, es, fr, de, it, pt] → English prompt
  - If L1 in [ja, zh, ar, he, ko, th] → Translate prompt to L1
```

**Pros:**
- ✅ Best of both worlds - simple for Western, advanced for Eastern
- ✅ Cost-optimized - only translate when beneficial
- ✅ Culturally appropriate - matches pedagogical expectations
- ✅ Scalable - add languages to "translate" list as needed

**Cons:**
- ⚠️ Increased complexity - conditional logic
- ⚠️ Maintenance - which languages get translated?
- ⚠️ Testing burden - need to test both paths

**Best For:**
- Global product with diverse user base
- Users across Western and Eastern languages
- Long-term scalability

---

## 4. Lara Translate Integration Approaches

### Lara Translate Capabilities Relevant to LinguaLog

**From Lara documentation:**
- ✅ 40+ languages supported
- ✅ Context-aware translation (uses previous translations)
- ✅ Custom instructions (style, tone, formality)
- ✅ Translation memory (glossaries for domain terms)
- ✅ Low latency (~100-200ms for short text)
- ✅ Batch translation support
- ✅ No training required

### Integration Option 1: **MCP Server** (Model Context Protocol)

**What is MCP?**
- Standard protocol for connecting AI assistants to external tools
- Claude Desktop native support
- Tools exposed as functions the AI can call

**Architecture:**
```
Backend → Lara MCP Server → Lara API
```

**How It Works:**
```python
# In your agent system prompt
available_tools = [
    "translate_text",  # Lara MCP tool
    "batch_translate", # Lara MCP tool
]

# AI decides when to call
if needs_translation:
    result = call_tool("translate_text", {
        "text": "Hello world",
        "source": "en",
        "target": "es"
    })
```

**Pros:**
- ✅ Declarative - AI decides when to translate
- ✅ Flexible - AI can chain translations
- ✅ Future-proof - MCP is an emerging standard
- ✅ Tool discovery - AI knows what's available

**Cons:**
- ❌ Non-deterministic - AI might not call when you want
- ❌ Token overhead - tool descriptions use input tokens
- ❌ Latency - extra round trip for tool call
- ❌ Over-engineering for simple use case

**Best For:**
- Agentic workflows where AI decides translation strategy
- Complex multi-step processes
- Exploratory/experimental features

---

### Integration Option 2: **SDK Direct Integration**

**Architecture:**
```python
from lara_sdk import Translator, Credentials

# Initialize once
lara = Translator(credentials)

# Use directly in code
def translate_prompt(prompt: str, target_lang: str) -> str:
    result = lara.translate(
        text=prompt,
        source="en",
        target=target_lang,
        style="faithful",
        instructions=["Preserve technical terminology"]
    )
    return result.translation
```

**Pros:**
- ✅ Deterministic - you control exactly when translation happens
- ✅ Fast - direct API call, no AI intermediary
- ✅ Cacheable - can cache translated prompts by L1+immersion+settings
- ✅ Debuggable - clear control flow
- ✅ Cost-effective - only pay for translations you explicitly request

**Cons:**
- ⚠️ Manual integration - you write the logic
- ⚠️ Maintenance - need to update when Lara SDK changes

**Best For:**
- Production use cases with clear requirements
- Performance-sensitive applications
- Deterministic workflows

---

### Integration Option 3: **Hybrid MCP + SDK**

**Architecture:**
```python
# SDK for system-critical translations (prompts, UI)
lara_sdk = Translator(credentials)
translated_prompt = lara_sdk.translate(prompt, target=L1)

# MCP for user-facing features (on-demand translation button)
# AI can call translate_text tool when user clicks "Translate this"
```

**Pros:**
- ✅ Best of both worlds
- ✅ SDK for backend, MCP for frontend agentic features
- ✅ Flexibility for future features

**Cons:**
- ⚠️ Two integration points to maintain
- ⚠️ Potentially confusing architecture

**Best For:**
- Large-scale apps with both deterministic and agentic features
- Teams that want to experiment with MCP while using SDK for core

---

## 5. Recommendations

### Immediate Term (Next 2-4 Weeks)

**Recommendation: Option A + Targeted Improvements**

**Keep current approach:**
- ✅ English prompts
- ✅ AI handles multilingual output
- ✅ Settings affect prompt instructions only

**Add these enhancements:**

1. **Improve explanation instructions for non-Western languages:**
   ```python
   # lang_policy.py enhancement
   def explanation_instruction(effective: EffectiveSettings) -> str:
       # Add cultural pedagogy hints
       if effective.l1 in ['ja', 'zh', 'ko']:
           cultural_note = "Use examples relevant to East Asian learners. "
       elif effective.l1 in ['ar', 'he']:
           cultural_note = "Use RTL-appropriate examples. "
       else:
           cultural_note = ""

       return base_instruction + cultural_note
   ```

2. **Add prompt templates per language family:**
   ```python
   SYSTEM_TEMPLATE_CJK = """あなたは言語学習の専門家です... (in native language)"""
   SYSTEM_TEMPLATE_ARABIC = """أنت مساعد تعلم اللغة... (in native language)"""

   # Select template based on L1
   template = get_template_for_language_family(effective.l1)
   ```

3. **Cache translated prompts:**
   ```python
   # Key: (template_id, l1, immersion_level, strictness, formality)
   prompt_cache = {}

   cache_key = f"{template_id}:{effective.l1}:{effective.immersion_level}:{effective.strictness}"
   if cache_key in prompt_cache:
       return prompt_cache[cache_key]
   ```

**Why this approach:**
- ✅ Low risk - incremental improvements
- ✅ Fast to implement - no new dependencies
- ✅ Covers 80% of use cases
- ✅ Easy to rollback if issues

---

### Medium Term (1-3 Months)

**Recommendation: Add Lara SDK for Option D (Smart Hybrid)**

**Implementation:**

1. **Install Lara SDK:**
   ```bash
   pip install lara-sdk
   ```

2. **Add translation layer:**
   ```python
   # backend/translation_service.py
   from lara_sdk import Translator

   class PromptTranslationService:
       def __init__(self):
           self.lara = Translator(credentials)
           self.cache = {}  # Redis in production

       def translate_prompt_if_needed(
           self,
           prompt: str,
           target_lang: str
       ) -> str:
           # Only translate for specific languages
           if target_lang in ['ja', 'zh', 'ar', 'he', 'ko', 'th']:
               cache_key = f"{hash(prompt)}:{target_lang}"

               if cache_key not in self.cache:
                   result = self.lara.translate(
                       text=prompt,
                       source="en",
                       target=target_lang,
                       style="faithful",
                       instructions=[
                           "Preserve technical terminology",
                           "Keep formatting"
                       ]
                   )
                   self.cache[cache_key] = result.translation

               return self.cache[cache_key]

           return prompt  # Return English for Western languages
   ```

3. **Integrate into prompt builder:**
   ```python
   # prompt_builder.py
   def build_messages(entry_text: str, effective: EffectiveSettings):
       # Build English prompt
       system_prompt = SYSTEM_TEMPLATE.format(...)

       # Translate if L1 is non-Western
       if should_translate_prompt(effective.l1):
           translation_service = get_translation_service()
           system_prompt = translation_service.translate_prompt_if_needed(
               system_prompt,
               effective.l1
           )

       return system_prompt, user_payload
   ```

**Benefits:**
- ✅ Better quality for CJK/Arabic users
- ✅ Culturally appropriate pedagogy
- ✅ Still fast (cached prompts)
- ✅ Opt-in per language - low risk

**Cost Analysis:**
- Prompt size: ~1,500 characters
- Lara cost: ~$0.0002 per translation
- With caching: ~10 unique prompt variations
- Total cost per user: $0.002 (negligible)

---

### Long Term (3-6 Months)

**Recommendation: Add On-Demand Lara Features**

**Features to add:**

1. **Post-hoc translation toggle (from plan):**
   ```typescript
   // Frontend component
   <Button onClick={() => translateExplanation('L1')}>
     👁️ Show in {nativeLanguage}
   </Button>
   ```

   ```python
   # New endpoint
   @app.post("/entries/{entry_id}/translate-explanation")
   async def translate_explanation(
       entry_id: str,
       target_lang: str,
       user_id: str
   ):
       entry = fetch_single_entry(entry_id, user_id)

       # Use Lara for high-quality translation
       result = lara.translate(
           text=entry['explanation'],
           source=entry['explanation_language_snapshot'],
           target=target_lang,
           adapt_to=[f"user_{user_id}_memory"],  # Use user's TM
           style="fluid"  # More natural than AI translation
       )

       return {"translated_explanation": result.translation}
   ```

2. **Translation memory per user:**
   - Save all L2→L1 translations to user's TM
   - Use TM for domain adaptation
   - Improves consistency over time

3. **Glossary support:**
   - Let users add custom terminology
   - Medical students: "myocardial infarction" → "infarto de miocardio"
   - Legal students: "habeas corpus" → keep in Latin

**Why wait:**
- ⏳ These are nice-to-have features
- ⏳ Core functionality works well without them
- ⏳ Better to validate user demand first

---

## Final Architecture Recommendation

### Recommended Stack

```
┌─────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                  │
│  - Settings UI (3 languages + immersion slider)        │
│  - Entry view (with translation toggle button)         │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│                  Backend (FastAPI)                      │
│  ┌──────────────────────────────────────────────────┐  │
│  │  resolve_effective() → EffectiveSettings         │  │
│  └──────────────────┬───────────────────────────────┘  │
│                     │                                   │
│                     ▼                                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Prompt Builder                                   │  │
│  │  - English base prompt                            │  │
│  │  - explanation_instruction() for settings         │  │
│  │  - [FUTURE] translate_if_needed() for CJK/Arabic  │  │
│  └──────────────────┬───────────────────────────────┘  │
│                     │                                   │
│                     ▼                                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │  AI Model (OpenAI GPT-4o-mini)                    │  │
│  │  - Receives prompt (English or L1)                │  │
│  │  - Returns multilingual response                  │  │
│  └──────────────────┬───────────────────────────────┘  │
│                     │                                   │
│                     ▼                                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │  [FUTURE] Lara SDK (Optional)                     │  │
│  │  - Translate prompts for CJK/Arabic               │  │
│  │  - On-demand explanation translation              │  │
│  │  - Translation memory for consistency             │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Decision Matrix

| Use Case | Approach | Why |
|----------|----------|-----|
| **Western language learners** (ES, FR, DE) | English prompts + AI | ✅ Works great, simple, fast |
| **CJK/Arabic beginners** | Translated prompts (Lara SDK) | ✅ Better explanations, cultural fit |
| **On-demand translation** | Lara SDK endpoint | ✅ User control, high quality |
| **Translation field in feedback** | AI (current) | ✅ Good enough for most cases |
| **Premium users needing perfect translations** | Lara SDK | ✅ Professional quality |

---

## Implementation Checklist

### Phase 1: Fix Critical Issues (Week 1)
- [ ] Fix immersion level DB constraint (0-3)
- [ ] Remove unused levels 4-5 from code
- [ ] Update tests for 0-3 range
- [ ] Migration to update existing data

### Phase 2: Enhance Current System (Week 2-3)
- [ ] Add cultural hints to explanation_instruction()
- [ ] Test with non-Western languages
- [ ] Improve formality mapping for CJK languages
- [ ] Add prompt caching layer

### Phase 3: Evaluate Lara Integration (Week 4)
- [ ] Set up Lara SDK dev account
- [ ] Test prompt translation quality for JA, ZH, AR
- [ ] Benchmark latency with caching
- [ ] Calculate cost per user
- [ ] Decision: Proceed with Smart Hybrid or stay with current?

### Phase 4: Implement Smart Hybrid (If approved, Month 2-3)
- [ ] Add translation_service.py
- [ ] Integrate with prompt_builder.py
- [ ] Add Redis cache for prod
- [ ] A/B test with CJK users
- [ ] Monitor quality and costs

### Phase 5: On-Demand Features (Month 4-6)
- [ ] Add translate-explanation endpoint
- [ ] Add translation memory per user
- [ ] Add glossary support
- [ ] Add 👁️ toggle UI component

---

## Conclusion

**Key Insights:**

1. **Settings are prompt modifiers only** - they don't affect code logic, making them flexible but non-deterministic.

2. **Current English prompt approach works for 80% of use cases** - especially Western language learners.

3. **Lara integration makes sense for:**
   - CJK/Arabic native speakers (better pedagogy)
   - On-demand translation features (user control)
   - Premium users (professional quality)

4. **SDK > MCP for deterministic workflows** - use MCP only for experimental agentic features.

5. **Smart Hybrid is the sweet spot** - translate only when beneficial, keep simple otherwise.

**Next Steps:**
1. Fix immersion level bug (critical)
2. Test current system with diverse languages
3. Prototype Lara integration for one CJK language
4. Measure quality improvement vs cost
5. Decide on Smart Hybrid based on data
