# Lara Translation API - Overview

## What is Lara?

Lara is an adaptive translation AI that combines LLM fluency and reasoning with low hallucination rates and latency. Key features:

- **Adaptive**: No training required - adapts to any domain on-the-fly
- **Context-aware**: Uses previously translated content and context
- **Multi-modal**: Supports text and document translation
- **Memory integration**: Leverages translation memories and glossaries

## Integration Options

### 1. SDK Integration
Direct integration using language-specific SDKs for full control over translation workflows.

### 2. MCP Server Integration
Model Context Protocol integration for LLM environments like Claude Desktop.

## Core Capabilities

### Text Translation
- Single sentence or batch translation
- Context-aware adaptation
- Custom instructions and styling
- Multiple language pairs

### Document Translation
- Preserves formatting and layout
- Supports various file formats
- Asynchronous processing workflow
- PDF output options

### Translation Memory Management
- Create and manage translation memories
- Import/export TMX files
- Add/delete translation units
- Context-aware matching

### Glossary Management
- Domain-specific terminology control
- CSV import/export
- Unidirectional term mapping
- Multi-language support

## Authentication

All SDK operations require credentials:
```python
from lara_sdk import Translator, Credentials

credentials = Credentials(
    access_key_id="your-access-key-id",
    access_key_secret="your-access-key-secret"
)
lara = Translator(credentials)
```

## Language Support

Supports 40+ languages with specific locale codes (e.g., `en-US`, `fr-FR`, `zh-CN`).
See supported-languages.md for complete list.

## Pro Features

Translation Memory and Glossary management requires Pro or Team subscription.

## Quick Start

1. Install SDK: `pip install lara-sdk`
2. Set up credentials
3. Initialize Translator
4. Start translating with `lara.translate()`

See specific guides for detailed implementation examples.
# Lara Text Translation Guide

## Basic Setup

```python
from lara_sdk import Translator, Credentials, TranslatePriority

# Initialize translator
credentials = Credentials(
    access_key_id="your-access-key-id",
    access_key_secret="your-access-key-secret"
)
lara = Translator(credentials)
```

## Basic Translation

### Simple Translation
```python
# Basic translation
result = lara.translate(
    text="Hello, how are you?",
    source="en-US",  # Optional - autodetected if omitted
    target="it-IT"   # Required
)
print(result.translation)  # "Ciao, come stai?"
```

### Batch Translation
```python
# Translate multiple texts
texts = ["Hello world", "Good morning", "Thank you"]
result = lara.translate(
    text=texts,
    source="en-US",
    target="fr-FR"
)
print(result.translation)  # ["Bonjour le monde", "Bonjour", "Merci"]
```

## Advanced Features

### Context-Aware Translation
```python
# Using translation memories for domain adaptation
result = lara.translate(
    text="The patient shows improvement",
    source="en-US",
    target="es-ES",
    adapt_to=["medical_memory_id"],  # Use specific translation memories
    instructions=["Use formal medical terminology"],
    style="faithful"  # Options: faithful, fluid, creative
)
```

### Using Glossaries
```python
# Apply domain-specific terminology
result = lara.translate(
    text="The server crashed during deployment",
    source="en-US",
    target="de-DE",
    glossaries=["tech_glossary_id"],
    adapt_to=["software_memory_id"]
)
```

### Custom Instructions
```python
# Fine-tune translation behavior
result = lara.translate(
    text="Thanks for your help!",
    source="en-US",
    target="ja-JP",
    instructions=[
        "Use formal Japanese (keigo)",
        "Business context",
        "Polite tone"
    ]
)
```

## Translation Options

### Core Parameters
- `text`: String, String[], or TextBlock[] - content to translate
- `source`: Source language code (autodetected if omitted)
- `target`: Target language code (required)

### Adaptation Parameters
- `adapt_to`: String[] - Translation memory IDs for domain adaptation
- `glossaries`: String[] - Glossary IDs for terminology control
- `instructions`: String[] - Custom behavior instructions

### Style Options
- `style`: "faithful" (default), "fluid", "creative"
- `content_type`: "text/plain" (default), "application/xliff+xml"

### Performance Parameters
- `timeout_ms`: Maximum translation time in milliseconds
- `priority`: TranslatePriority.NORMAL (default) or TranslatePriority.LOW
- `use_cache`: Boolean - enable caching (Pro feature)
- `cache_ttl`: Cache time-to-live in seconds

### Privacy Parameters
- `no_trace`: Boolean - incognito mode (content not saved)
- `verbose`: Boolean - return debugging info (not for production)

## Response Structure

```python
# Single string response
TextResult(
    content_type="text/plain",
    source_language="en",
    adapted_to=["memory_id"],
    translation="Translated text"
)

# Array response
TextResult(
    content_type="text/plain", 
    source_language="en",
    adapted_to=["memory_id"],
    translation=["Text 1", "Text 2", "Text 3"]
)
```

## Error Handling

```python
try:
    result = lara.translate(
        text="Hello world",
        target="invalid-code"
    )
except TimeoutException:
    print("Translation timed out")
except Exception as e:
    print(f"Translation failed: {e}")
```

## Best Practices

1. **Language Detection**: Omit `source` for automatic detection, use `source_hint` if uncertain
2. **Batch Processing**: Use arrays for multiple texts to improve efficiency
3. **Memory Usage**: Specify `adapt_to` for domain-specific translations
4. **Caching**: Enable for repeated translations (requires Pro subscription)
5. **Privacy**: Use `no_trace=True` for sensitive content
6. **Performance**: Set appropriate `timeout_ms` for your use case

## XLIFF Support

Limited support for XLIFF 1.2 and 2.0 inline tags within `<source>` elements:
- XLIFF 1.2: `<g>`, `<x>`, `<ex>`, `<bx>`, `<ph>`, `<it>`, `<mrk>`
- XLIFF 2.0: `<cp>`, `<ph>`, `<pc>`, `<sc>`, `<ec>`, `<sm>`, `<em>`, `<mrk>`

For complex XLIFF features, use Document Translation instead.
# Lara Document Translation Guide

## Overview

Document translation is an asynchronous process with three phases:
1. Upload the file
2. Poll status until translation completes
3. Download the translated document

Lara preserves formatting, layout, and structure of the original document.

## Setup

```python
from lara_sdk import Translator, Credentials

credentials = Credentials(
    access_key_id="your-access-key-id",
    access_key_secret="your-access-key-secret"
)
lara = Translator(credentials)
```

## Simple Document Translation

### All-in-One Method
```python
# Translate document with automatic handling of upload/poll/download
translated_content = lara.documents.translate(
    file_path="path/to/document.pdf",
    filename="document.pdf",
    source="en-US",  # Optional - autodetected
    target="it-IT",
    adapt_to=["memory_id"],
    glossaries=["glossary_id"],
    output_format="pdf",  # Optional: forces PDF output for PDF inputs
    style="fluid"
)

# translated_content contains the binary data of the translated document
with open("translated_document.pdf", "wb") as f:
    f.write(translated_content)
```

## Manual Process (Advanced Control)

### Step 1: Upload Document
```python
# Upload and start translation
document = lara.documents.upload(
    file_path="document.pdf",
    filename="document.pdf",
    source="en-US",
    target="fr-FR",
    options={
        "adapt_to": ["memory_id"],
        "glossaries": ["glossary_id"],
        "style": "faithful",
        "no_trace": False  # Set True for privacy
    }
)

print(f"Document ID: {document.id}")
print(f"Status: {document.status}")  # "initialized"
```

### Step 2: Poll Status
```python
import time

# Poll until translation completes
while True:
    document = lara.documents.status(document.id)
    print(f"Status: {document.status}")
    
    if document.status == "translated":
        print(f"Translation complete!")
        print(f"Translated characters: {document.translated_chars}/{document.total_chars}")
        break
    elif document.status == "error":
        print(f"Translation failed: {document.error_reason}")
        break
    
    time.sleep(5)  # Wait 5 seconds before next check
```

### Step 3: Download Translation
```python
# Download the translated document
translated_content = lara.documents.download(
    document.id,
    options={"output_format": "pdf"}  # Optional: force PDF output
)

# Save to file
with open("translated_document.pdf", "wb") as f:
    f.write(translated_content)
```

## Document Object Structure

```python
Document(
    id="doc_xyz123",           # Unique document ID
    status="translated",       # Current status
    source="en-US",           # Source language
    target="fr-FR",           # Target language
    filename="document.pdf",   # Original filename
    created_at="2025-01-15T10:00:00Z",
    updated_at="2025-01-15T10:05:00Z",
    translated_chars=1250,    # Characters translated
    total_chars=1250,         # Total characters in document
    error_reason=None         # Error message if failed
)
```

## Document Status Values

- `"initialized"`: Upload complete, translation starting
- `"processing"`: Translation in progress
- `"translated"`: Translation complete, ready for download
- `"error"`: Translation failed (check `error_reason`)

## Translation Options

### Upload/Translate Options
- `adapt_to`: String[] - Translation memory IDs
- `glossaries`: String[] - Glossary IDs for terminology
- `style`: "faithful" (default), "fluid", "creative"
- `no_trace`: Boolean - Privacy mode (content not saved)

### Download Options
- `output_format`: "pdf" - Force PDF output (only for PDF inputs)

## Supported File Formats

### Input Formats
- PDF files
- Microsoft Word documents (.docx)
- PowerPoint presentations (.pptx)
- Excel spreadsheets (.xlsx)
- Plain text files (.txt)
- And more...

### Output Format Notes
- Most files maintain their original format
- PDF files default to .docx output unless `output_format="pdf"` is specified
- Use `output_format="pdf"` to maintain PDF format

## Error Handling

```python
try:
    # Upload document
    document = lara.documents.upload("large_file.pdf", "large_file.pdf", target="es-ES")
    
    # Poll with timeout
    max_wait_time = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        document = lara.documents.status(document.id)
        
        if document.status == "translated":
            break
        elif document.status == "error":
            raise Exception(f"Translation failed: {document.error_reason}")
        
        time.sleep(10)
    else:
        raise TimeoutError("Translation took too long")
    
    # Download result
    result = lara.documents.download(document.id)
    
except Exception as e:
    print(f"Document translation failed: {e}")
```

## Best Practices

### File Handling
1. **File Size**: Large files take longer to process
2. **Quality**: High-quality, text-based files work best
3. **Scanned Documents**: May have reduced accuracy
4. **Images**: Text in images may not be fully preserved

### Performance
1. **Polling Frequency**: Check status every 5-10 seconds
2. **Timeout Handling**: Set reasonable timeouts for large documents
3. **Error Recovery**: Always check for error status

### Privacy
1. **Sensitive Content**: Use `no_trace=True` for confidential documents
2. **Data Retention**: Normal mode saves content for translation memory learning

### Workflow Integration
1. **Async Processing**: Suitable for background processing
2. **Progress Tracking**: Use character counts to show progress
3. **Batch Processing**: Process multiple documents concurrently

## SDK Availability

Document translation is available starting from:
- Python: v1.3.0
- Node.js: v1.4.0  
- Java: v1.2.4
- PHP: v1.1.0
- Go: v1.0.0

## Example: Batch Document Processing

```python
import asyncio
import time

def translate_document_async(file_path, filename, target_lang):
    """Translate a single document asynchronously"""
    try:
        # Upload
        document = lara.documents.upload(file_path, filename, target=target_lang)
        
        # Poll status
        while True:
            document = lara.documents.status(document.id)
            if document.status == "translated":
                # Download
                content = lara.documents.download(document.id)
                return {
                    "filename": filename,
                    "status": "success", 
                    "content": content
                }
            elif document.status == "error":
                return {
                    "filename": filename,
                    "status": "error",
                    "error": document.error_reason
                }
            time.sleep(5)
            
    except Exception as e:
        return {
            "filename": filename,
            "status": "error", 
            "error": str(e)
        }

# Process multiple documents
documents = [
    ("file1.pdf", "file1.pdf", "es-ES"),
    ("file2.docx", "file2.docx", "fr-FR"),
    ("file3.txt", "file3.txt", "de-DE")
]

for file_path, filename, target in documents:
    result = translate_document_async(file_path, filename, target)
    if result["status"] == "success":
        with open(f"translated_{filename}", "wb") as f:
            f.write(result["content"])
        print(f"✓ {filename} translated successfully")
    else:
        print(f"✗ {filename} failed: {result['error']}")
```
# Lara Translation Memory Management

> **Note**: Translation Memory features require Pro or Team subscription

## Overview

Translation Memories store previously translated text segments (Translation Units/TUs) as source-target pairs. They enable domain adaptation and consistency across translations.

## Setup

```python
from lara_sdk import Translator, Credentials

credentials = Credentials(
    access_key_id="your-access-key-id", 
    access_key_secret="your-access-key-secret"
)
lara = Translator(credentials)

# All memory operations use: lara.memories
```

## Memory Object Structure

```python
Memory(
    id="mem_xyz123",                    # Unique memory ID
    secret="sec_xyz123",                # Secret for sharing
    name="Medical Translations",        # Custom name
    created_at="2025-01-15T10:00:00Z",
    updated_at="2025-01-15T10:00:00Z", 
    owner_id="acc_123xyz",              # Owner account ID
    shared_at="2025-01-15T10:00:00Z",
    collaborators_count=3               # Number of collaborators
)
```

## Basic Memory Operations

### List All Memories
```python
# Get all memories available to your account
memories = lara.memories.list()

for memory in memories:
    print(f"ID: {memory.id}")
    print(f"Name: {memory.name}")
    print(f"Collaborators: {memory.collaborators_count}")
```

### Create New Memory
```python
# Create empty memory
memory = lara.memories.create("Marketing Translations")
print(f"Created memory: {memory.id}")

# Create memory from MyMemory import
imported_memory = lara.memories.create(
    name="Imported Medical Terms",
    external_id="ext_my_aabb1122"  # MyMemory ID format
)
```

### Update Memory Name
```python
# Update memory name
updated_memory = lara.memories.update(
    id="mem_xyz123",
    name="Updated Marketing Translations"
)
print(f"Updated: {updated_memory.name}")
```

### Delete Memory
```python
# Delete memory (irreversible)
deleted_memory = lara.memories.delete("mem_xyz123")
print(f"Deleted memory: {deleted_memory.name}")
```

## Translation Unit Management

### Add Single Translation Unit
```python
# Basic translation unit
import_job = lara.memories.add_translation(
    id="mem_xyz123",
    source="en-US",
    target="es-ES", 
    sentence="Hello world",
    translation="Hola mundo"
)
print(f"Job ID: {import_job.id}")
```

### Add Translation with Context
```python
# Translation unit with context
import_job = lara.memories.add_translation(
    id="mem_xyz123",
    source="en-US",
    target="fr-FR",
    sentence="The bank is closed",
    translation="La banque est fermée",
    tuid="unique_id_123",              # Optional unique identifier
    sentence_before="I went downtown.", # Context before
    sentence_after="I'll come back tomorrow." # Context after
)
```

### Add to Multiple Memories
```python
# Add same translation to multiple memories
multi_import_job = lara.memories.add_translation(
    id=["mem_xyz123", "mem_abc456"],   # Multiple memory IDs
    source="en-US",
    target="de-DE",
    sentence="Machine learning model",
    translation="Maschinelles Lernmodell"
)
```

### Delete Translation Unit
```python
# Remove specific translation
delete_job = lara.memories.delete_translation(
    id="mem_xyz123",
    source="en-US",
    target="es-ES",
    sentence="Hello world", 
    translation="Hola mundo",
    tuid="unique_id_123"  # Optional, helps with precision
)
```

## TMX File Operations

### Import TMX File
```python
# Import TMX file to existing memory
import_job = lara.memories.import_tmx(
    id="mem_xyz123",
    tmx="path/to/translation_memory.tmx"
)

print(f"Import job started: {import_job.id}")
print(f"Progress: {import_job.progress}")  # 0.0 to 1.0
```

### Import Compressed TMX
```python
# Import gzipped TMX file
import_job = lara.memories.import_tmx(
    id="mem_xyz123", 
    tmx="path/to/translation_memory.tmx.gz",
    gzip=True  # Specify compression (auto-detected in Python/Java)
)
```

### Check Import Status
```python
import time

# Poll import progress
while True:
    status = lara.memories.get_import_status(import_job.id)
    print(f"Progress: {status.progress * 100:.1f}%")
    
    if status.progress >= 1.0:
        print("Import completed!")
        break
    
    time.sleep(5)  # Check every 5 seconds
```

## Using Memories in Translation

### Apply Memories to Text Translation
```python
# Use specific memories for domain adaptation
result = lara.translate(
    text="The patient requires immediate surgery",
    source="en-US",
    target="es-ES",
    adapt_to=["medical_memory_id", "hospital_memory_id"]  # Use multiple memories
)
print(result.translation)
```

### Apply to Document Translation
```python
# Use memories in document translation
document = lara.documents.translate(
    file_path="medical_report.pdf",
    filename="medical_report.pdf", 
    source="en-US",
    target="fr-FR",
    adapt_to=["medical_memory_id"]
)
```

## Best Practices

### Memory Organization
```python
# Create domain-specific memories
legal_memory = lara.memories.create("Legal Documents")
medical_memory = lara.memories.create("Medical Translations") 
tech_memory = lara.memories.create("Technical Documentation")

# Use descriptive names with context
client_memory = lara.memories.create("ClientName - Marketing Materials 2025")
```

### Context Usage
```python
# Always provide context for ambiguous terms
lara.memories.add_translation(
    id="banking_memory",
    source="en-US",
    target="fr-FR",
    sentence="interest rate",
    translation="taux d'intérêt",
    sentence_before="The central bank announced", # Financial context
    sentence_after="will increase next month"
)

# vs generic context
lara.memories.add_translation(
    id="general_memory", 
    source="en-US",
    target="fr-FR",
    sentence="interest", 
    translation="intérêt",
    sentence_before="He showed great",  # General interest context
    sentence_after="in the subject"
)
```

### Batch Operations
```python
# Batch add multiple translations
translations = [
    ("API endpoint", "punto final de API"),
    ("Database connection", "conexión de base de datos"), 
    ("Authentication token", "token de autenticación"),
    ("Rate limiting", "limitación de velocidad")
]

for source_text, target_text in translations:
    lara.memories.add_translation(
        id="tech_memory",
        source="en-US",
        target="es-ES",
        sentence=source_text,
        translation=target_text
    )
```

### Memory Maintenance
```python
# Regular cleanup - remove outdated translations
outdated_translations = [
    ("old term", "término antiguo"),
    ("deprecated feature", "función obsoleta")
]

for source_text, target_text in outdated_translations:
    lara.memories.delete_translation(
        id="tech_memory",
        source="en-US", 
        target="es-ES",
        sentence=source_text,
        translation=target_text
    )
```

## Error Handling

```python
try:
    # Create memory
    memory = lara.memories.create("Test Memory")
    
    # Add translation
    job = lara.memories.add_translation(
        id=memory.id,
        source="en-US",
        target="invalid-lang",  # This will fail
        sentence="test",
        translation="prueba"
    )
    
except Exception as e:
    print(f"Memory operation failed: {e}")

try:
    # Import large TMX file with timeout
    import_job = lara.memories.import_tmx("mem_123", "large_file.tmx")
    
    # Monitor with timeout
    timeout = 300  # 5 minutes
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        status = lara.memories.get_import_status(import_job.id)
        if status.progress >= 1.0:
            break
        time.sleep(10)
    else:
        print("Import timeout - check status later")
        
except Exception as e:
    print(f"TMX import failed: {e}")
```

## Memory Sharing

Memories can be shared using the `secret` field, but this requires additional API calls not covered in basic SDK usage. Contact Lara support for collaboration features.

## Performance Tips

1. **Memory Selection**: Use specific memories rather than all available ones
2. **Context Precision**: Provide meaningful context for better matching
3. **Regular Updates**: Keep memories current with latest terminology
4. **Size Management**: Large memories may impact translation speed
5. **Import Monitoring**: Always monitor TMX import progress for large files
# Lara Glossary Management Guide

> **Note**: Glossary features require Pro or Team subscription

## Overview

Glossaries provide domain-specific terminology control for consistent translations. Lara supports unidirectional, multilingual glossaries where terms map from source language to one or more target languages.

## Setup

```python
from lara_sdk import Translator, Credentials

credentials = Credentials(
    access_key_id="your-access-key-id",
    access_key_secret="your-access-key-secret"
)
lara = Translator(credentials)

# All glossary operations use: lara.glossaries
```

## Glossary Object Structure

```python
Glossary(
    id="gls_xyz123",                    # Unique glossary ID
    name="Technical Terms",             # Custom name
    created_at="2025-01-15T10:00:00Z",
    updated_at="2025-01-15T10:00:00Z", 
    owner_id="acc_123xyz"               # Owner account ID
)
```

## Basic Glossary Operations

### List All Glossaries
```python
# Get all glossaries available to your account
glossaries = lara.glossaries.list()

for glossary in glossaries:
    print(f"ID: {glossary.id}")
    print(f"Name: {glossary.name}")
    print(f"Created: {glossary.created_at}")
```

### Create New Glossary
```python
# Create empty glossary
glossary = lara.glossaries.create("Medical Terminology")
print(f"Created glossary: {glossary.id}")
```

### Update Glossary Name
```python
# Update glossary name
updated_glossary = lara.glossaries.update(
    id="gls_xyz123",
    name="Updated Medical Terminology"
)
print(f"Updated: {updated_glossary.name}")
```

### Delete Glossary
```python
# Delete glossary (irreversible)
deleted_glossary = lara.glossaries.delete("gls_xyz123")
print(f"Deleted glossary: {deleted_glossary.name}")
```

## CSV Import/Export

### CSV Format Specification

Lara uses a specific CSV format for glossaries:

**Header Row**: Valid language codes (first column = source, others = targets)
**Data Rows**: Source term + corresponding target terms

```csv
en-US,fr-FR,it-IT,de-DE
apple,pomme,mela,Apfel
database,base de données,database,Datenbank
API,API,API,API
```

**Key Rules:**
- First column = source language
- Each row needs source term + at least one target term
- Empty cells allowed for missing translations
- Unidirectional: source → target only
- No reverse mapping (target → source)

### Import CSV File
```python
# Import CSV to existing glossary
import_job = lara.glossaries.import_csv(
    id="gls_xyz123",
    csv="path/to/glossary.csv"
)

print(f"Import job ID: {import_job.id}")
print(f"Progress: {import_job.progress}")  # 0.0 to 1.0
```

### Import Compressed CSV
```python
# Import gzipped CSV file  
import_job = lara.glossaries.import_csv(
    id="gls_xyz123",
    csv="path/to/glossary.csv.gz",
    gzip=True  # Auto-detected in Python/Java
)
```

### Check Import Status
```python
import time

# Monitor import progress
while True:
    status = lara.glossaries.get_import_status(import_job.id)
    print(f"Progress: {status.progress * 100:.1f}%")
    
    if status.progress >= 1.0:
        print("Import completed!")
        break
    
    time.sleep(5)  # Check every 5 seconds
```

### Export Glossary
```python
# Export glossary as CSV
csv_content = lara.glossaries.export(
    id="gls_xyz123",
    content_type="csv/table-uni",  # Only supported format
    source="en-US"                 # Source language for export
)

# Save to file
with open("exported_glossary.csv", "w", encoding="utf-8") as f:
    f.write(csv_content)
```

### Get Glossary Counts
```python
# Get statistics about glossary content
counts = lara.glossaries.counts("gls_xyz123")

print("Term counts by source language:")
for source_lang, count in counts.unidirectional.items():
    print(f"  {source_lang}: {count} terms")
```

## Using Glossaries in Translation

### Apply Glossaries to Text Translation
```python
# Use specific glossaries for terminology control
result = lara.translate(
    text="The API endpoint returned a database error",
    source="en-US", 
    target="fr-FR",
    glossaries=["tech_glossary_id", "error_glossary_id"],  # Multiple glossaries
    adapt_to=["tech_memory_id"]  # Can combine with memories
)
print(result.translation)
```

### Apply to Document Translation
```python
# Use glossaries in document translation
document = lara.documents.translate(
    file_path="technical_manual.pdf",
    filename="technical_manual.pdf",
    source="en-US",

# Lara Glossary Management Guide

> **Note**: Glossary features require Pro or Team subscription

## Overview

Glossaries provide domain-specific terminology control for consistent translations. Lara supports unidirectional, multilingual glossaries where terms map from source language to one or more target languages.

## Setup

```python
from lara_sdk import Translator, Credentials

credentials = Credentials(
    access_key_id="your-access-key-id",
    access_key_secret="your-access-key-secret"
)
lara = Translator(credentials)

# All glossary operations use: lara.glossaries
```

## Glossary Object Structure

```python
Glossary(
    id="gls_xyz123",                    # Unique glossary ID
    name="Technical Terms",             # Custom name
    created_at="2025-01-15T10:00:00Z",
    updated_at="2025-01-15T10:00:00Z", 
    owner_id="acc_123xyz"               # Owner account ID
)
```

## Basic Glossary Operations

### List All Glossaries
```python
# Get all glossaries available to your account
glossaries = lara.glossaries.list()

for glossary in glossaries:
    print(f"ID: {glossary.id}")
    print(f"Name: {glossary.name}")
    print(f"Created: {glossary.created_at}")
```

### Create New Glossary
```python
# Create empty glossary
glossary = lara.glossaries.create("Medical Terminology")
print(f"Created glossary: {glossary.id}")
```

### Update Glossary Name
```python
# Update glossary name
updated_glossary = lara.glossaries.update(
    id="gls_xyz123",
    name="Updated Medical Terminology"
)
print(f"Updated: {updated_glossary.name}")
```

### Delete Glossary
```python
# Delete glossary (irreversible)
deleted_glossary = lara.glossaries.delete("gls_xyz123")
print(f"Deleted glossary: {deleted_glossary.name}")
```

## CSV Import/Export

### CSV Format Specification

Lara uses a specific CSV format for glossaries:

**Header Row**: Valid language codes (first column = source, others = targets)
**Data Rows**: Source term + corresponding target terms

```csv
en-US,fr-FR,it-IT,de-DE
apple,pomme,mela,Apfel
database,base de données,database,Datenbank
API,API,API,API
```

**Key Rules:**
- First column = source language
- Each row needs source term + at least one target term
- Empty cells allowed for missing translations
- Unidirectional: source → target only
- No reverse mapping (target → source)

### Import CSV File
```python
# Import CSV to existing glossary
import_job = lara.glossaries.import_csv(
    id="gls_xyz123",
    csv="path/to/glossary.csv"
)

print(f"Import job ID: {import_job.id}")
print(f"Progress: {import_job.progress}")  # 0.0 to 1.0
```

### Import Compressed CSV
```python
# Import gzipped CSV file  
import_job = lara.glossaries.import_csv(
    id="gls_xyz123",
    csv="path/to/glossary.csv.gz",
    gzip=True  # Auto-detected in Python/Java
)
```

### Check Import Status
```python
import time

# Monitor import progress
while True:
    status = lara.glossaries.get_import_status(import_job.id)
    print(f"Progress: {status.progress * 100:.1f}%")
    
    if status.progress >= 1.0:
        print("Import completed!")
        break
    
    time.sleep(5)  # Check every 5 seconds
```

### Export Glossary
```python
# Export glossary as CSV
csv_content = lara.glossaries.export(
    id="gls_xyz123",
    content_type="csv/table-uni",  # Only supported format
    source="en-US"                 # Source language for export
)

# Save to file
with open("exported_glossary.csv", "w", encoding="utf-8") as f:
    f.write(csv_content)
```

### Get Glossary Counts
```python
# Get statistics about glossary content
counts = lara.glossaries.counts("gls_xyz123")

print("Term counts by source language:")
for source_lang, count in counts.unidirectional.items():
    print(f"  {source_lang}: {count} terms")
```

## Using Glossaries in Translation

### Apply Glossaries to Text Translation
```python
# Use specific glossaries for terminology control
result = lara.translate(
    text="The API endpoint returned a database error",
    source="en-US", 
    target="fr-FR",
    glossaries=["tech_glossary_id", "error_glossary_id"],  # Multiple glossaries
    adapt_to=["tech_memory_id"]  # Can combine with memories
)
print(result.translation)
```

### Apply to Document Translation
```python
# Use glossaries in document translation
document = lara.documents.translate(
    file_path="technical_manual.pdf",
    filename="technical_manual.pdf",
    source="en-US",
    target="de-DE",
    glossaries=["tech_glossary_id"]
)
```

## Practical Examples

### Creating Technical Glossary
```python
# 1. Create glossary
tech_glossary = lara.glossaries.create("Software Development Terms")

# 2. Prepare CSV content
csv_content = """en-US,es-ES,fr-FR,de-DE
API,API,API,API
database,base de datos,base de données,Datenbank
authentication,autenticación,authentification,Authentifizierung
endpoint,punto final,point de terminaison,Endpunkt
repository,repositorio,dépôt,Repository
deployment,despliegue,déploiement,Bereitstellung
framework,marco de trabajo,framework,Framework"""

# 3. Save to file and import
with open("tech_terms.csv", "w", encoding="utf-8") as f:
    f.write(csv_content)

# 4. Import to glossary
import_job = lara.glossaries.import_csv(tech_glossary.id, "tech_terms.csv")

# 5. Monitor import
while True:
    status = lara.glossaries.get_import_status(import_job.id)
    if status.progress >= 1.0:
        print("Glossary ready!")
        break
    time.sleep(2)
```

### Medical Terminology Glossary
```python
# Medical terms with specialized translations
medical_csv = """en-US,es-ES,pt-BR
hypertension,hipertensión,hipertensão
myocardial infarction,infarto de miocardio,infarto do miocárdio
diabetes mellitus,diabetes mellitus,diabetes mellitus
bradycardia,bradicardia,bradicardia
tachycardia,taquicardia,taquicardia
arrhythmia,arritmia,arritmia"""

medical_glossary = lara.glossaries.create("Medical Terminology")
# ... import process same as above
```

### Legal Terms Glossary
```python
# Legal terminology requiring precision
legal_csv = """en-US,fr-FR,it-IT
plaintiff,demandeur,attore
defendant,défendeur,convenuto
jurisdiction,juridiction,giurisdizione
litigation,contentieux,contenzioso
settlement,règlement,accordo
injunction,injonction,ingiunzione
precedent,précédent,precedente"""

legal_glossary = lara.glossaries.create("Legal Terms")
# ... import process
```

## Advanced Usage Patterns

### Combining Glossaries and Memories
```python
# Use both glossaries and translation memories
result = lara.translate(
    text="The authentication API endpoint requires database connection",
    source="en-US",
    target="es-ES",
    glossaries=["tech_glossary_id"],        # Terminology control
    adapt_to=["software_memory_id"],        # Domain adaptation
    instructions=["Technical documentation style"]
)
```

### Domain-Specific Translation Pipeline
```python
def translate_technical_content(text, target_language):
    """Specialized translation for technical content"""
    return lara.translate(
        text=text,
        target=target_language,
        glossaries=["tech_glossary_id", "api_glossary_id"],
        adapt_to=["software_memory_id"],
        style="faithful",  # Preserve technical accuracy
        instructions=[
            "Maintain technical terminology", 
            "Preserve code references",
            "Use industry standard terms"
        ]
    )

# Usage
result = translate_technical_content(
    "The REST API authenticates using JWT tokens",
    "fr-FR"
)
```

### Glossary Maintenance Workflow
```python
def update_glossary_from_feedback(glossary_id, term_updates):
    """Update glossary based on translation feedback"""
    
    # Export current glossary
    current_csv = lara.glossaries.export(
        id=glossary_id,
        content_type="csv/table-uni", 
        source="en-US"
    )
    
    # Process updates (implementation depends on your needs)
    updated_csv = process_term_updates(current_csv, term_updates)
    
    # Create new glossary with updates
    new_glossary = lara.glossaries.create(f"Updated_{glossary_id}")
    
    # Import updated terms
    with open("updated_terms.csv", "w") as f:
        f.write(updated_csv)
    
    import_job = lara.glossaries.import_csv(new_glossary.id, "updated_terms.csv")
    
    return new_glossary.id
```

## Best Practices

### Glossary Design
1. **Single Domain**: Keep one glossary per domain/subject area
2. **Consistent Style**: Use consistent terminology style within each glossary
3. **Regular Updates**: Update glossaries based on translation feedback
4. **Source Authority**: Use authoritative sources for term definitions

### CSV File Preparation
```python
# Good CSV structure example
good_csv = """en-US,es-ES,fr-FR
user interface,interfaz de usuario,interface utilisateur
machine learning,aprendizaje automático,apprentissage automatique
artificial intelligence,inteligencia artificial,intelligence artificielle"""

# Avoid these issues:
# - Mixed domains in one glossary
# - Inconsistent terminology
# - Missing target translations
# - Overly generic terms
```

### Performance Optimization
1. **Focused Glossaries**: Use specific glossaries rather than large general ones
2. **Strategic Application**: Apply glossaries only when terminology control is needed
3. **Regular Cleanup**: Remove outdated or unused terms
4. **Size Management**: Keep glossaries reasonably sized for better performance

### Quality Control
```python
def validate_glossary_terms(csv_file_path):
    """Basic validation before importing"""
    with open(csv_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Check header
    header = lines[0].strip().split(',')
    if len(header) < 2:
        raise ValueError("Need at least source and one target language")
    
    # Check each data row
    for i, line in enumerate(lines[1:], 2):
        fields = line.strip().split(',')
        if not fields[0]:  # Missing source term
            raise ValueError(f"Line {i}: Missing source term")
        if not any(fields[1:]):  # No target terms
            raise ValueError(f"Line {i}: No target translations provided")
    
    print("CSV validation passed")

# Use before importing
validate_glossary_terms("my_glossary.csv")
```

## Error Handling

```python
try:
    # Create and populate glossary
    glossary = lara.glossaries.create("Test Glossary")
    
    # Import with error handling
    import_job = lara.glossaries.import_csv(glossary.id, "terms.csv")
    
    # Monitor with timeout
    timeout = 120  # 2 minutes
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        status = lara.glossaries.get_import_status(import_job.id)
        if status.progress >= 1.0:
            print("Import completed successfully")
            break
        time.sleep(5)
    else:
        print("Import timeout - check status manually")
    
except FileNotFoundError:
    print("CSV file not found")
except Exception as e:
    print(f"Glossary operation failed: {e}")
    # Clean up if needed
    try:
        lara.glossaries.delete(glossary.id)
    except:
        pass
```

## Integration Tips

1. **Version Control**: Track glossary versions for rollback capability
2. **Backup Strategy**: Regular exports for backup purposes  
3. **Team Collaboration**: Share glossary exports with translation teams
4. **Quality Metrics**: Monitor translation consistency with glossary usage
5. **Feedback Loop**: Collect translator feedback to improve glossaries
# Lara MCP Server Integration Guide

## Overview

The Lara Translate MCP Server brings Lara's translation capabilities to Model Context Protocol (MCP) environments like Claude Desktop. It acts as a specialized translation agent for LLM workflows.

## What It Does

The MCP Server bridges Lara's specialized translation models with the MCP ecosystem, enabling:
- Higher quality translations (especially for non-English content)
- Consistent domain handling
- Context-aware translations
- Custom instruction support

## Installation & Setup

```bash
# Install the MCP server (example - check official docs)
npm install @lara/mcp-server

# Configure in your MCP client (e.g., Claude Desktop)
# Add to configuration file
```

## Core Translation Tool

### translate

The primary tool for performing translations between supported language pairs.

**Input Format:**
```json
{
  "text": [
    {
      "text": "Hello, how are you?",
      "translatable": true
    },
    {
      "text": "Non-translatable content",
      "translatable": false
    }
  ],
  "source": "en-US",           // Optional - auto-detected if omitted
  "target": "fr-FR",          // Required
  "context": "Casual conversation with a friend",  // Optional
  "instructions": [           // Optional
    "Use informal tone",
    "Avoid slang"
  ],
  "source_hint": "This might be in English or French"  // Optional
}
```

**Response Format:**
```json
[
  {
    "text": "Bonjour, comment allez-vous ?",
    "translatable": true
  },
  {
    "text": "Non-translatable content", 
    "translatable": false
  }
]
```

## Translation Memory Tools

### list_memories

Lists all translation memories linked to your account.

**Usage:**
```
No input parameters required
```

**Response:**
```json
[
  {
    "id": "mem_XYZ",
    "secret": "sec_XYZ", 
    "ownerId": "acc_XYZ",
    "collaboratorsCount": 1,
    "createdAt": "2025-04-17T15:24:19.867Z",
    "updatedAt": "2025-04-17T15:24:19.881Z",
    "sharedAt": "2025-04-17T15:24:19.874Z",
    "name": "Memory Name"
  }
]
```

### create_memory

Creates a new translation memory.

**Input:**
```json
{
  "name": "New Memory Name",
  "external_id": "ext_my_123456"  // Optional - import from MyMemory
}
```

**Response:**
```json
{
  "id": "mem_XYZ",
  "name": "New Memory Name",
  "ownerId": "acc_XYZ",
  "createdAt": "2025-04-17T15:24:19.867Z",
  // ... other memory fields
}
```

### update_memory

Updates a translation memory name.

**Input:**
```json
{
  "id": "mem_XYZ",
  "name": "Updated Memory Name"
}
```

### delete_memory

Deletes a translation memory.

**Input:**
```json
{
  "id": "mem_XYZ"
}
```

### add_translation

Adds a translation unit to existing memory/memories.

**Input:**
```json
{
  "id": "mem_XYZ",              // Single memory ID
  "source": "en-US",
  "target": "fr-FR",
  "sentence": "Hello world",
  "translation": "Bonjour le monde",
  "tuid": "unique_123",         // Optional
  "sentence_before": "Context before",  // Optional
  "sentence_after": "Context after"     // Optional
}
```

**Multiple Memories:**
```json
{
  "id": ["mem_XYZ", "mem_ABC"], // Multiple memory IDs
  "source": "en-US",
  "target": "fr-FR", 
  "sentence": "Hello world",
  "translation": "Bonjour le monde"
}
```

**Response:**
```json
{
  "id": "JobID",
  "begin": 10918552,
  "end": 10918552,
  "channel": 1,
  "size": 1,
  "progress": 1.0  // 1.0 = completed, <1.0 = in progress
}
```

### delete_translation

Removes a translation unit from memory.

**Input:**
```json
{
  "id": "mem_XYZ",
  "source": "en-US",
  "target": "fr-FR",
  "sentence": "Hello world",
  "translation": "Bonjour le monde",
  "tuid": "unique_123"  // Optional but recommended
}
```

### import_tmx

Imports a TMX file into a translation memory.

**Input:**
```json
{
  "id": "mem_XYZ",
  "tmx": "/path/to/file.tmx",  // File path
  "gzip": false               // Set true for .gz files
}
```

**Response:**
```json
{
  "id": "JobID",
  "progress": 0.0,  // Monitor this field
  "size": 1000,
  "begin": 10918552,
  "end": 10918552,
  "channel": 1
}
```

### check_import_status

Monitors the progress of TMX import jobs.

**Input:**
```json
{
  "id": "JobID"  // From import_tmx response
}
```

**Response:**
```json
{
  "id": "JobID",
  "progress": 0.75,  // 0.0 to 1.0 (1.0 = complete)
  "size": 1000,
  "begin": 10918552,
  "end": 10918552,
  "channel": 1
}
```

## Practical Examples

### Context-Aware Translation
```
User: "Translate with Lara: 'la terra è rossa', I'm talking with a tennis player."

MCP Request:
{
  "text": [{"text": "la terra è rossa", "translatable": true}],
  "target": "en-US",
  "context": "Conversation with a tennis player"
}

Response:
[{"text": "The clay is red.", "translatable": true}]
```

### Multi-Text Translation with Instructions
```
MCP Request:
{
  "text": [
    {"text": "Bonjour", "translatable": true},
    {"text": "Comment ça va?", "translatable": true},
    {"text": "[USER_ID_123]", "translatable": false}
  ],
  "source": "fr-FR",
  "target": "en-US", 
  "instructions": ["Use casual tone", "American English"],
  "context": "Informal chat application"
}

Response:
[
  {"text": "Hello", "translatable": true},
  {"text": "How's it going?", "translatable": true},
  {"text": "[USER_ID_123]", "translatable": false}
]
```

### Working with Translation Memories
```
1. List available memories:
   Tool: list_memories

2. Create project-specific memory:
   Tool: create_memory
   Input: {"name": "Mobile App UI Terms"}

3. Add common translations:
   Tool: add_translation
   Input: {
     "id": "mem_mobile_ui",
     "source": "en-US",
     "target": "es-ES", 
     "sentence": "Sign in",
     "translation": "Iniciar sesión"
   }

4. Use memory in translation:
   Tool: translate
   Input: {
     "text": [{"text": "Please sign in to continue", "translatable": true}],
     "target": "es-ES",
     "context": "Mobile app authentication"
   }
```

## Integration Benefits

### Why Use Lara with LLMs

1. **Specialized Translation**: Purpose-built translation models vs general LLM translation
2. **Non-English Strength**: Better performance on non-English languages  
3. **Cost Efficiency**: Translate before LLM processing to reduce token costs
4. **Domain Adaptation**: Translation memories provide context-specific translations
5. **Consistency**: Glossaries ensure terminology consistency
6. **Speed**: Parallel processing reduces latency

### Workflow Integration

```
User Input (Non-English) 
    ↓
Lara Translation (to English)
    ↓  
LLM Processing (in English)
    ↓
LLM Response (in English)
    ↓
Lara Translation (back to original language)
    ↓
Final Response to User
```

## Best Practices

### Context Provision
- Always provide context for ambiguous terms
- Include domain information (medical, legal, technical)
- Specify tone/formality level

### Memory Management
- Create domain-specific memories
- Regularly update with new terminology
- Use descriptive memory names

### Error Handling
- Monitor import job progress
- Check translation quality for critical content
- Implement fallback for translation failures

### Performance Optimization
- Use appropriate batch sizes for multi-text translation
- Cache common translations locally if possible
- Select relevant memories rather than using all available

## Configuration Example

```json
// MCP client configuration
{
  "mcpServers": {
    "lara-translate": {
      "command": "npx",
      "args": ["@lara/mcp-server"],
      "env": {
        "LARA_ACCESS_KEY_ID": "your-access-key-id",
        "LARA_ACCESS_KEY_SECRET": "your-access-key-secret"
      }
    }
  }
}
```

This MCP integration allows you to leverage Lara's specialized translation capabilities directly within LLM workflows, providing better translation quality and domain-specific adaptation compared to general-purpose language models.
# Lara Supported Languages Reference

## Complete Language List

Lara supports 40+ languages with specific locale codes. Always use the full locale code (e.g., `en-US`, not `en`) for best results.

### Language Codes and Locales

| Language | Locale Code | Region |
|----------|------------|---------|
| Arabic | `ar-SA` | Saudi Arabia |
| Bulgarian | `bg-BG` | Bulgaria |
| Catalan | `ca-ES` | Spain |
| Chinese (Simplified) | `zh-CN` | Mainland China |
| Chinese (Traditional) | `zh-TW` | Taiwan |
| Chinese (Traditional) | `zh-HK` | Hong Kong |
| Croatian | `hr-HR` | Croatia |
| Czech | `cs-CZ` | Czech Republic |
| Danish | `da-DK` | Denmark |
| Dutch | `nl-BE` | Belgium |
| Dutch | `nl-NL` | Netherlands |
| English | `en-AU` | Australia |
| English | `en-CA` | Canada |
| English | `en-IE` | Ireland |
| English | `en-GB` | United Kingdom |
| English | `en-US` | United States |
| Finnish | `fi-FI` | Finland |
| French | `fr-CA` | Canada |
| French | `fr-FR` | France |
| German | `de-DE` | Germany |
| Greek | `el-GR` | Greece |
| Hebrew | `he-IL` | Israel |
| Hungarian | `hu-HU` | Hungary |
| Indonesian | `id-ID` | Indonesia |
| Italian | `it-IT` | Italy |
| Japanese | `ja-JP` | Japan |
| Korean | `ko-KR` | Korea |
| Malay | `ms-MY` | Malaysia |
| Norwegian Bokmål | `nb-NO` | Norway |
| Polish | `pl-PL` | Poland |
| Portuguese | `pt-BR` | Brazil |
| Portuguese | `pt-PT` | Portugal |
| Russian | `ru-RU` | Russia |
| Slovak | `sk-SK` | Slovakia |
| Spanish | `es-AR` | Argentina |
| Spanish | `es-419` | Latin America |
| Spanish | `es-MX` | Mexico |
| Spanish | `es-ES` | Spain |
| Swedish | `sv-SE` | Sweden |
| Thai | `th-TH` | Thailand |
| Turkish | `tr-TR` | Turkey |
| Ukrainian | `uk-UA` | Ukraine |

## Default Language Mappings

When using two-letter language codes, Lara applies these defaults:

| Two-Letter Code | Default Locale | Applied Code |
|-----------------|---------------|--------------|
| `en` | English (US) | `en-US` |
| `es` | Spanish (Spain) | `es-ES` |
| `fr` | French (France) | `fr-FR` |
| `pt` | Portuguese (Brazil) | `pt-BR` |
| `zh` | Chinese (Simplified) | `zh-CN` |
| `nl` | Dutch (Netherlands) | `nl-NL` |

## Usage Examples

### Programmatic Language List
```python
# Get all supported languages
languages = lara.languages()
print(languages)
# Returns: ["ar-SA", "bg-BG", "ca-ES", "zh-CN", ...]
```

### Common Language Pairs

**English to Major Languages:**
```python
# English to Spanish (Spain)
lara.translate("Hello", source="en-US", target="es-ES")

# English to French (France)  
lara.translate("Hello", source="en-US", target="fr-FR")

# English to German
lara.translate("Hello", source="en-US", target="de-DE")

# English to Japanese
lara.translate("Hello", source="en-US", target="ja-JP")

# English to Chinese (Simplified)
lara.translate("Hello", source="en-US", target="zh-CN")
```

**Regional Variants:**
```python
# Spanish variants
lara.translate("Hello", target="es-ES")   # Spain Spanish
lara.translate("Hello", target="es-MX")   # Mexican Spanish  
lara.translate("Hello", target="es-AR")   # Argentinian Spanish
lara.translate("Hello", target="es-419")  # Latin American Spanish

# English variants
lara.translate("Hello", target="en-US")   # American English
lara.translate("Hello", target="en-GB")   # British English
lara.translate("Hello", target="en-AU")   # Australian English
lara.translate("Hello", target="en-CA")   # Canadian English

# Portuguese variants
lara.translate("Hello", target="pt-BR")   # Brazilian Portuguese
lara.translate("Hello", target="pt-PT")   # European Portuguese

# Chinese variants
lara.translate("Hello", target="zh-CN")   # Simplified Chinese
lara.translate("Hello", target="zh-TW")   # Traditional Chinese (Taiwan)
lara.translate("Hello", target="zh-HK")   # Traditional Chinese (Hong Kong)
```

## Language Detection

Lara can automatically detect source languages:

```python
# Automatic detection
result = lara.translate(
    text="Bonjour, comment allez-vous?",  # French input
    target="en-US"  # No source specified
)
print(result.source_language)  # "fr-FR"

# With detection hint
result = lara.translate(
    text="Ambiguous text that could be multiple languages",
    target="en-US",
    source_hint="fr-FR"  # Hint that it might be French
)
```

## Regional Considerations

### Cultural Adaptation
Different locales may require different cultural approaches:

```python
# Formal vs informal cultures
lara.translate(
    "Thank you very much",
    target="ja-JP",  # Japanese - highly formal culture
    instructions=["Use appropriate politeness level"]
)

lara.translate(
    "Thanks a lot",  
    target="en-AU",  # Australian - more casual culture
    instructions=["Use casual Australian English"]
)
```

### Business Context
```python
# Business communication styles vary by region
lara.translate(
    "We need to discuss this proposal",
    target="de-DE",  # German - direct communication
    context="Business meeting",
    instructions=["Direct, professional tone"]
)

lara.translate(
    "We should consider discussing this proposal", 
    target="ja-JP",  # Japanese - indirect communication
    context="Business meeting", 
    instructions=["Polite, indirect business style"]
)
```

## Language Selection Best Practices

### Choose Specific Locales
```python
# Good - specific locale
result = lara.translate("Hello", target="es-MX")  # Mexican Spanish

# Less optimal - generic code (will default to es-ES)
result = lara.translate("Hello", target="es")     # Defaults to Spain Spanish
```

### Match Your Audience
```python
# For Brazilian audience
lara.translate("Welcome", target="pt-BR")

# For Portuguese audience  
lara.translate("Welcome", target="pt-PT")

# For Latin American audience (general)
lara.translate("Welcome", target="es-419")
```

### Consider Regional Business Practices
```python
# Canadian French (different from France French)
lara.translate(
    "Privacy policy", 
    target="fr-CA",
    context="Legal document for Canadian users"
)

# Belgian Dutch (different from Netherlands Dutch)
lara.translate(
    "Terms of service",
    target="nl-BE", 
    context="Legal document for Belgian users"
)
```

## Validation

### Check Language Support
```python
def is_language_supported(language_code):
    """Check if a language code is supported by Lara"""
    supported_languages = lara.languages()
    return language_code in supported_languages

# Usage
if is_language_supported("sw-KE"):  # Swahili - not supported
    print("Language supported")
else:
    print("Language not supported")
```

### Validate Language Pairs
```python
def validate_translation_request(source, target):
    """Validate a translation request"""
    supported = lara.languages()
    
    if source and source not in supported:
        raise ValueError(f"Source language {source} not supported")
    
    if target not in supported:
        raise ValueError(f"Target language {target} not supported")
    
    if source == target:
        raise ValueError("Source and target languages cannot be the same")

# Usage
try:
    validate_translation_request("en-US", "fr-FR")
    print("Valid language pair")
except ValueError as e:
    print(f"Invalid: {e}")
```

## Future Language Support

New languages are automatically added to Lara as they become available. Check the supported languages list programmatically to ensure your application handles new languages correctly:

```python
# Dynamic language support check
def get_available_languages():
    """Get current list of supported languages"""
    try:
        return lara.languages()
    except Exception as e:
        print(f"Could not fetch languages: {e}")
        return []

# Update your application's language options
supported_languages = get_available_languages()
```
# Lara Quick Start Examples

## Installation & Setup

```bash
# Install the SDK
pip install lara-sdk
```

```python
# Import and initialize
from lara_sdk import Translator, Credentials

# Set up credentials
credentials = Credentials(
    access_key_id="your-access-key-id",
    access_key_secret="your-access-key-secret"
)

# Initialize translator
lara = Translator(credentials)
```

## Basic Translation Examples

### Simple Text Translation
```python
# Translate a simple phrase
result = lara.translate(
    text="Hello, how are you today?",
    source="en-US",
    target="fr-FR"
)
print(result.translation)
# Output: "Bonjour, comment allez-vous aujourd'hui ?"
```

### Auto-Detect Source Language
```python
# Let Lara detect the source language
result = lara.translate(
    text="Guten Tag, wie geht es Ihnen?",  # German
    target="en-US"
)
print(f"Detected: {result.source_language}")  # "de-DE"
print(result.translation)  # "Good day, how are you?"
```

### Batch Translation
```python
# Translate multiple texts at once
texts = [
    "Welcome to our application",
    "Please enter your password",
    "Login successful"
]

result = lara.translate(
    text=texts,
    source="en-US",
    target="es-ES"
)

for i, translation in enumerate(result.translation):
    print(f"{texts[i]} → {translation}")

# Output:
# Welcome to our application → Bienvenido a nuestra aplicación
# Please enter your password → Por favor, introduzca su contraseña
# Login successful → Inicio de sesión exitoso
```

## Context-Aware Translation

### Using Context for Better Results
```python
# Without context - generic translation
result1 = lara.translate(
    text="The bank is closed",
    target="es-ES"
)
print(result1.translation)  # "El banco está cerrado"

# With financial context
result2 = lara.translate(
    text="The bank is closed", 
    target="es-ES",
    instructions=["Financial institution context"]
)
print(result2.translation)  # "El banco está cerrado"

# With riverbank context
result3 = lara.translate(
    text="The bank is muddy",
    target="es-ES", 
    instructions=["Referring to riverbank"]
)
print(result3.translation)  # "La orilla está fangosa"
```

### Domain-Specific Translation
```python
# Medical translation
medical_text = "The patient shows signs of acute myocardial infarction"
result = lara.translate(
    text=medical_text,
    source="en-US",
    target="es-ES",
    instructions=[
        "Medical terminology",
        "Professional medical context",
        "Use formal register"
    ]
)
print(result.translation)
# "El paciente muestra signos de infarto agudo de miocardio"
```

## Document Translation Examples

### Simple Document Translation
```python
# Translate a PDF document
translated_content = lara.documents.translate(
    file_path="contract.pdf",
    filename="contract.pdf",
    # Lara Quick Start Examples

## Installation & Setup

```bash
# Install the SDK
pip install lara-sdk
```

```python
# Import and initialize
from lara_sdk import Translator, Credentials

# Set up credentials
credentials = Credentials(
    access_key_id="your-access-key-id",
    access_key_secret="your-access-key-secret"
)

# Initialize translator
lara = Translator(credentials)
```

## Basic Translation Examples

### Simple Text Translation
```python
# Translate a simple phrase
result = lara.translate(
    text="Hello, how are you today?",
    source="en-US",
    target="fr-FR"
)
print(result.translation)
# Output: "Bonjour, comment allez-vous aujourd'hui ?"
```

### Auto-Detect Source Language
```python
# Let Lara detect the source language
result = lara.translate(
    text="Guten Tag, wie geht es Ihnen?",  # German
    target="en-US"
)
print(f"Detected: {result.source_language}")  # "de-DE"
print(result.translation)  # "Good day, how are you?"
```

### Batch Translation
```python
# Translate multiple texts at once
texts = [
    "Welcome to our application",
    "Please enter your password",
    "Login successful"
]

result = lara.translate(
    text=texts,
    source="en-US",
    target="es-ES"
)

for i, translation in enumerate(result.translation):
    print(f"{texts[i]} → {translation}")

# Output:
# Welcome to our application → Bienvenido a nuestra aplicación
# Please enter your password → Por favor, introduzca su contraseña
# Login successful → Inicio de sesión exitoso
```

## Context-Aware Translation

### Using Context for Better Results
```python
# Without context - generic translation
result1 = lara.translate(
    text="The bank is closed",
    target="es-ES"
)
print(result1.translation)  # "El banco está cerrado"

# With financial context
result2 = lara.translate(
    text="The bank is closed", 
    target="es-ES",
    instructions=["Financial institution context"]
)
print(result2.translation)  # "El banco está cerrado"

# With riverbank context
result3 = lara.translate(
    text="The bank is muddy",
    target="es-ES", 
    instructions=["Referring to riverbank"]
)
print(result3.translation)  # "La orilla está fangosa"
```

### Domain-Specific Translation
```python
# Medical translation
medical_text = "The patient shows signs of acute myocardial infarction"
result = lara.translate(
    text=medical_text,
    source="en-US",
    target="es-ES",
    instructions=[
        "Medical terminology",
        "Professional medical context",
        "Use formal register"
    ]
)
print(result.translation)
# "El paciente muestra signos de infarto agudo de miocardio"
```

## Document Translation Examples

### Simple Document Translation
```python
# Translate a PDF document
translated_content = lara.documents.translate(
    file_path="contract.pdf",
    filename="contract.pdf",
    source="en-US",
    target="es-ES"
)

# Save the translated document
with open("contract_spanish.pdf", "wb") as f:
    f.write(translated_content)

print("Document translated and saved!")
```

### Document Translation with Custom Settings
```python
# Translate with specific formatting and domain adaptation
translated_content = lara.documents.translate(
    file_path="technical_manual.docx",
    filename="technical_manual.docx",
    source="en-US", 
    target="de-DE",
    options={
        "style": "faithful",  # Preserve technical accuracy
        "output_format": "pdf",  # Convert to PDF
        "adapt_to": ["tech_memory_id"],  # Use technical memory
        "glossaries": ["tech_glossary_id"]  # Apply technical terms
    }
)
```

## Translation Memory Examples

### Creating and Using Memories
```python
# Create a new translation memory
memory = lara.memories.create("E-commerce Translations")
print(f"Created memory: {memory.id}")

# Add some common e-commerce terms
translations = [
    ("Add to cart", "Añadir al carrito"),
    ("Checkout", "Finalizar compra"), 
    ("Free shipping", "Envío gratis"),
    ("Customer reviews", "Reseñas de clientes")
]

for en_text, es_text in translations:
    lara.memories.add_translation(
        id=memory.id,
        source="en-US",
        target="es-ES",
        sentence=en_text,
        translation=es_text
    )

# Use the memory for consistent translations
result = lara.translate(
    text="Add to cart and proceed to checkout for free shipping",
    source="en-US",
    target="es-ES", 
    adapt_to=[memory.id]
)
print(result.translation)
# "Añadir al carrito y proceder a finalizar compra para envío gratis"
```

## Glossary Examples

### Creating Domain-Specific Glossary
```python
# Create a medical glossary
glossary = lara.glossaries.create("Medical Terms")

# Prepare CSV content
medical_csv = """en-US,es-ES,fr-FR
hypertension,hipertensión,hypertension
diabetes,diabetes,diabète
medication,medicamento,médicament
diagnosis,diagnóstico,diagnostic
treatment,tratamiento,traitement"""

# Save and import
with open("medical_terms.csv", "w", encoding="utf-8") as f:
    f.write(medical_csv)

import_job = lara.glossaries.import_csv(glossary.id, "medical_terms.csv")

# Wait for import to complete
import time
while True:
    status = lara.glossaries.get_import_status(import_job.id)
    if status.progress >= 1.0:
        break
    time.sleep(2)

# Use glossary for medical translation
result = lara.translate(
    text="The patient's hypertension requires immediate medication adjustment",
    source="en-US",
    target="es-ES",
    glossaries=[glossary.id]
)
print(result.translation)
```

## Real-World Application Examples

### Multi-Language Customer Support
```python
def translate_support_message(message, customer_language):
    """Translate customer support messages with appropriate tone"""
    
    # Detect if message is from customer (non-English) or agent (English)
    if customer_language != "en-US":
        # Customer message -> English for agent
        agent_message = lara.translate(
            text=message,
            source=customer_language,
            target="en-US",
            instructions=[
                "Customer support context",
                "Preserve emotional tone",
                "Maintain urgency level"
            ]
        )
        return agent_message.translation
    else:
        # Agent response -> Customer language
        customer_message = lara.translate(
            text=message,
            source="en-US", 
            target=customer_language,
            instructions=[
                "Professional customer service tone",
                "Helpful and courteous",
                "Clear and reassuring"
            ]
        )
        return customer_message.translation

# Usage examples
customer_msg = "Mi pedido no ha llegado y estoy muy preocupado"
agent_sees = translate_support_message(customer_msg, "es-ES")
print(f"Agent sees: {agent_sees}")

agent_response = "I understand your concern. Let me check your order status immediately."
customer_sees = translate_support_message(agent_response, "es-ES") 
print(f"Customer sees: {customer_sees}")
```

### E-commerce Product Translation
```python
def translate_product_listing(product_data, target_language):
    """Translate product information maintaining SEO and marketing appeal"""
    
    # Create marketing-focused memory if not exists
    try:
        marketing_memory = lara.memories.create("E-commerce Marketing")
        
        # Add common marketing terms
        marketing_terms = [
            ("premium quality", "calidad premium"),
            ("best seller", "más vendido"),
            ("limited time offer", "oferta por tiempo limitado"),
            ("customer favorite", "favorito de los clientes")
        ]
        
        for en_term, translated_term in marketing_terms:
            lara.memories.add_translation(
                id=marketing_memory.id,
                source="en-US",
                target=target_language,
                sentence=en_term,
                translation=translated_term
            )
    except:
        marketing_memory = None  # Use existing memory
    
    # Translate product fields
    translated_product = {}
    
    # Product title - marketing focused
    translated_product['title'] = lara.translate(
        text=product_data['title'],
        target=target_language,
        adapt_to=[marketing_memory.id] if marketing_memory else [],
        instructions=[
            "Marketing copy",
            "Appealing and engaging",
            "SEO-friendly"
        ]
    ).translation
    
    # Product description - detailed and persuasive
    translated_product['description'] = lara.translate(
        text=product_data['description'],
        target=target_language,
        adapt_to=[marketing_memory.id] if marketing_memory else [],
        instructions=[
            "E-commerce product description",
            "Persuasive marketing tone",
            "Highlight key benefits"
        ]
    ).translation
    
    # Specifications - technical and accurate
    translated_product['specifications'] = lara.translate(
        text=product_data['specifications'],
        target=target_language,
        style="faithful",  # Preserve technical accuracy
        instructions=[
            "Technical specifications",
            "Precise and accurate",
            "Maintain measurements and numbers"
        ]
    ).translation
    
    return translated_product

# Usage
product = {
    'title': "Premium Wireless Headphones - Best Seller",
    'description': "Experience crystal-clear sound with our customer favorite wireless headphones. Limited time offer!",
    'specifications': "Bluetooth 5.0, 30-hour battery life, noise cancellation"
}

spanish_product = translate_product_listing(product, "es-ES")
print("Spanish Product:")
for key, value in spanish_product.items():
    print(f"{key}: {value}")
```

### Content Localization Pipeline
```python
import os
from pathlib import Path

def localize_content_directory(source_dir, target_languages, content_type="marketing"):
    """Localize all text files in a directory for multiple languages"""
    
    source_path = Path(source_dir)
    
    # Create glossary for content type if needed
    if content_type == "marketing":
        instructions = ["Marketing content", "Engaging tone", "Brand-appropriate"]
    elif content_type == "technical":
        instructions = ["Technical documentation", "Precise terminology", "Clear instructions"]
    elif content_type == "legal":
        instructions = ["Legal document", "Formal language", "Precise legal terms"]
    else:
        instructions = ["Professional tone"]
    
    # Process each text file
    for file_path in source_path.glob("*.txt"):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Translate to each target language
        for target_lang in target_languages:
            translated_content = lara.translate(
                text=content,
                source="en-US",
                target=target_lang,
                instructions=instructions,
                style="fluid"  # Natural sounding
            ).translation
            
            # Create localized directory structure
            lang_dir = source_path / target_lang
            lang_dir.mkdir(exist_ok=True)
            
            # Save translated file
            output_file = lang_dir / file_path.name
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(translated_content)
            
            print(f"Localized {file_path.name} to {target_lang}")

# Usage
localize_content_directory(
    source_dir="./content/english",
    target_languages=["es-ES", "fr-FR", "de-DE", "it-IT"],
    content_type="marketing"
)
```

## Error Handling Examples

### Robust Translation Function
```python
def safe_translate(text, target_language, max_retries=3):
    """Translate with error handling and retries"""
    
    for attempt in range(max_retries):
        try:
            result = lara.translate(
                text=text,
                target=target_language,
                timeout_ms=5000  # 5 second timeout
            )
            return {
                'success': True,
                'translation': result.translation,
                'source_language': result.source_language
            }
            
        except TimeoutError:
            print(f"Attempt {attempt + 1}: Translation timed out")
            if attempt == max_retries - 1:
                return {
                    'success': False,
                    'error': 'Translation timed out after multiple attempts'
                }
                
        except Exception as e:
            print(f"Attempt {attempt + 1}: Translation failed: {e}")
            if attempt == max_retries - 1:
                return {
                    'success': False,
                    'error': str(e)
                }
    
    return {'success': False, 'error': 'Maximum retries exceeded'}

# Usage
result = safe_translate("Hello world", "es-ES")
if result['success']:
    print(f"Translation: {result['translation']}")
else:
    print(f"Translation failed: {result['error']}")
```

### Batch Processing with Error Recovery
```python
def batch_translate_with_recovery(texts, target_language):
    """Process multiple texts with individual error handling"""
    
    results = []
    
    for i, text in enumerate(texts):
        try:
            result = lara.translate(text=text, target=target_language)
            results.append({
                'index': i,
                'original': text,
                'translation': result.translation,
                'status': 'success'
            })
            
        except Exception as e:
            print(f"Failed to translate item {i}: {text[:50]}...")
            results.append({
                'index': i,
                'original': text,
                'translation': None,
                'status': 'failed',
                'error': str(e)
            })
    
    # Summary
    successful = sum(1 for r in results if r['status'] == 'success')
    failed = len(results) - successful
    
    print(f"Batch translation complete: {successful} successful, {failed} failed")
    return results

# Usage
texts = [
    "Welcome to our platform",
    "Invalid text with special chars: \x00\x01", 
    "Please contact support",
    "Thank you for choosing us"
]

results = batch_translate_with_recovery(texts, "fr-FR")
for result in results:
    if result['status'] == 'success':
        print(f"✓ {result['original']} → {result['translation']}")
    else:
        print(f"✗ {result['original']} → Error: {result['error']}")
```

## Integration Patterns

### Flask Web Application Integration
```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/translate', methods=['POST'])
def translate_text():
    """API endpoint for text translation"""
    
    data = request.json
    
    try:
        result = lara.translate(
            text=data.get('text'),
            source=data.get('source'),  # Optional
            target=data.get('target'),
            instructions=data.get('instructions', []),
            style=data.get('style', 'faithful')
        )
        
        return jsonify({
            'success': True,
            'translation': result.translation,
            'source_language': result.source_language
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/translate/document', methods=['POST'])
def translate_document():
    """API endpoint for document translation"""
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    target_lang = request.form.get('target')
    
    try:
        # Save uploaded file temporarily
        temp_path = f"/tmp/{file.filename}"
        file.save(temp_path)
        
        # Translate document
        translated_content = lara.documents.translate(
            file_path=temp_path,
            filename=file.filename,
            target=target_lang
        )
        
        # Clean up
        os.remove(temp_path)
        
        return translated_content, 200, {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="translated_{file.filename}"'
        }
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
```

These examples demonstrate practical, real-world usage patterns for Lara's translation capabilities, showing how to handle errors, optimize performance, and integrate with applications effectively.
# Lara Translation API - Complete Documentation

> AI-Optimized Documentation for Cursor and Code Assistants

## Documentation Structure

This documentation is organized into focused files that AI assistants can easily reference and understand:

### Core Guides
- **[Overview](lara-overview.md)** - What Lara is and integration options
- **[Text Translation](lara-text-translation.md)** - Complete text translation guide
- **[Document Translation](lara-document-translation.md)** - Document translation workflows
- **[Quick Start Examples](lara-quickstart-examples.md)** - Practical code examples

### Advanced Features
- **[Translation Memory Management](lara-memory-management.md)** - Creating and using translation memories
- **[Glossary Management](lara-glossary-management.md)** - Domain-specific terminology control
- **[MCP Integration](lara-mcp-integration.md)** - Model Context Protocol integration

### Reference
- **[Supported Languages](lara-supported-languages.md)** - Complete language code reference

## Quick Reference

### Basic Setup
```python
from lara_sdk import Translator, Credentials

credentials = Credentials(
    access_key_id="your-access-key-id",
    access_key_secret="your-access-key-secret"
)
lara = Translator(credentials)
```

### Simple Translation
```python
result = lara.translate(
    text="Hello, world!",
    source="en-US",  # Optional - autodetected
    target="es-ES"   # Required
)
print(result.translation)  # "¡Hola, mundo!"
```

### Document Translation
```python
translated_content = lara.documents.translate(
    file_path="document.pdf",
    filename="document.pdf",
    target="fr-FR"
)
```

## Key Features

### Adaptive Translation
- No training required
- Adapts to domains on-the-fly
- Uses translation memories and glossaries
- Context-aware processing

### Translation Memories (Pro Feature)
```python
# Create memory
memory = lara.memories.create("Technical Documentation")

# Add translation unit
lara.memories.add_translation(
    id=memory.id,
    source="en-US",
    target="es-ES", 
    sentence="API endpoint",
    translation="punto final de API"
)

# Use in translation
result = lara.translate(
    text="Configure the API endpoint",
    target="es-ES",
    adapt_to=[memory.id]
)
```

### Glossaries (Pro Feature)
```python
# Create glossary
glossary = lara.glossaries.create("Medical Terms")

# Import CSV terms
import_job = lara.glossaries.import_csv(glossary.id, "medical_terms.csv")

# Use in translation
result = lara.translate(
    text="Patient diagnosis shows hypertension",
    target="es-ES",
    glossaries=[glossary.id]
)
```

## Common Use Cases

### Customer Support
```python
def translate_support_message(message, customer_language):
    return lara.translate(
        text=message,
        target=customer_language,
        instructions=[
            "Customer support context",
            "Professional and helpful tone",
            "Clear and reassuring"
        ]
    ).translation
```

### E-commerce Product Localization
```python
def localize_product(product_data, target_language):
    return {
        'title': lara.translate(
            text=product_data['title'],
            target=target_language,
            instructions=["Marketing copy", "Engaging tone"]
        ).translation,
        'description': lara.translate(
            text=product_data['description'], 
            target=target_language,
            instructions=["E-commerce description", "Persuasive"]
        ).translation
    }
```

### Technical Documentation
```python
def translate_technical_docs(content, target_language, tech_glossary_id):
    return lara.translate(
        text=content,
        target=target_language,
        glossaries=[tech_glossary_id],
        style="faithful",  # Preserve technical accuracy
        instructions=[
            "Technical documentation",
            "Precise terminology",
            "Clear instructions"
        ]
    ).translation
```

## Language Support

Lara supports 40+ languages including:

| Major Languages | Locale Codes |
|----------------|--------------|
| English | `en-US`, `en-GB`, `en-AU`, `en-CA` |
| Spanish | `es-ES`, `es-MX`, `es-AR`, `es-419` |
| French | `fr-FR`, `fr-CA` |
| German | `de-DE` |
| Chinese | `zh-CN`, `zh-TW`, `zh-HK` |
| Japanese | `ja-JP` |
| Korean | `ko-KR` |
| Portuguese | `pt-BR`, `pt-PT` |
| Italian | `it-IT` |
| Russian | `ru-RU` |

See [Supported Languages](lara-supported-languages.md) for the complete list.

## Error Handling Patterns

### Robust Translation Function
```python
def safe_translate(text, target_language, max_retries=3):
    for attempt in range(max_retries):
        try:
            return lara.translate(
                text=text,
                target=target_language,
                timeout_ms=5000
            )
        except TimeoutError:
            if attempt == max_retries - 1:
                raise
            continue
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            continue
```

### Batch Processing with Recovery
```python
def batch_translate_with_recovery(texts, target_language):
    results = []
    for i, text in enumerate(texts):
        try:
            result = lara.translate(text=text, target=target_language)
            results.append({
                'index': i,
                'success': True,
                'translation': result.translation
            })
        except Exception as e:
            results.append({
                'index': i, 
                'success': False,
                'error': str(e)
            })
    return results
```

## Performance Best Practices

### Text Translation
1. Use batch translation for multiple texts
2. Specify source language when known
3. Use appropriate timeout values
4. Enable caching for repeated translations (Pro)
5. Use `no_trace=True` for sensitive content

### Document Translation
1. Monitor translation status for large files
2. Use appropriate output formats
3. Handle timeouts gracefully
4. Consider file quality for best results

### Memory & Glossary Usage
1. Create domain-specific memories and glossaries
2. Provide context when adding translation units
3. Regular maintenance and updates
4. Use specific memories rather than all available

## MCP Integration

For LLM environments supporting Model Context Protocol:

```json
{
  "text": [
    {"text": "Hello, world!", "translatable": true}
  ],
  "target": "es-ES",
  "context": "Friendly greeting",
  "instructions": ["Casual tone"]
}
```

Response:
```json
[
  {"text": "¡Hola, mundo!", "translatable": true}
]
```

## SDK Versions

- **Python**: v1.3.0+ (Document translation available)
- **Node.js**: v1.4.0+ (Document translation available)  
- **Java**: v1.2.4+ (Document translation available)
- **PHP**: v1.1.0+ (Document translation available)
- **Go**: v1.0.0+ (Document translation available)

## Pro Features

Translation Memory and Glossary management require Pro or Team subscription:
- Create and manage translation memories
- Import/export TMX files
- Create and manage glossaries
- Import/export CSV glossaries
- Advanced caching options

## Getting Help

For specific implementation questions:
1. Check the relevant guide in this documentation
2. Review the Quick Start Examples
3. Refer to language support documentation
4. Contact Lara support for Pro feature assistance

## File Organization for AI Assistants

This documentation is structured for optimal AI assistant usage:
- Each file focuses on a single topic
- Code examples are complete and runnable
- Error handling patterns are included
- Common use cases are demonstrated
- Performance considerations are noted

Place all files in your project's documentation directory for easy AI assistant reference.