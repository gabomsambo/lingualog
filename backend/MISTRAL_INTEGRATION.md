# Mistral-7B-Instruct-v0.3 Integration for LinguaLog

This document provides instructions and examples for using the Mistral-7B-Instruct-v0.3 language model in the LinguaLog application.

## Overview

The integration allows LinguaLog to use Mistral-7B-Instruct-v0.3, a powerful open-source language model, for text generation and translation instead of relying on OpenAI's API. This provides more flexibility and potentially reduces operational costs.

## Installation

### Prerequisites

- Python 3.9+
- Minimum 16GB RAM
- GPU with 8GB+ VRAM (recommended for faster inference)

### Dependencies

All required dependencies are included in the `requirements.txt` file. To install them, run:

```bash
pip install -r requirements.txt
```

Key dependencies include:
- `transformers>=4.42.0`
- `huggingface_hub>=0.20.3`
- `torch>=2.0.0`
- `mistral_inference>=0.0.10`

### Model Download

The model will be automatically downloaded the first time you run the application. By default, it will be saved to `$HOME/mistral_models/7B-Instruct-v0.3`. You can customize this location by setting the `MISTRAL_MODEL_PATH` environment variable.

To manually download the model, you can use the provided utility function:

```python
from backend.mistral_engine import download_model

# Download to default location
model_path = download_model()

# Or specify a custom location
model_path = download_model("/path/to/custom/location")
```

## Configuration

The integration can be configured through environment variables:

- `MISTRAL_MODEL_PATH`: Path to store/load the model files (default: `$HOME/mistral_models/7B-Instruct-v0.3`)
- `USE_MISTRAL`: Set to "true" to use Mistral or "false" to use OpenAI as fallback (default: "true")
- `HUGGINGFACE_TOKEN`: Your Hugging Face access token, required to download and use the Mistral model
- `OPENAI_API_KEY`: Only required if `USE_MISTRAL` is set to "false" or as a fallback

You can set these in your `.env` file:

```
MISTRAL_MODEL_PATH=/path/to/your/model
USE_MISTRAL=true
HUGGINGFACE_TOKEN=your_huggingface_token
```

### Obtaining a Hugging Face Token

1. Sign up or log in to [Hugging Face](https://huggingface.co/)
2. Go to your profile > Settings > Access Tokens
3. Create a new token with read permissions
4. Add the token to your environment variables

## Usage Examples

### Basic Text Generation

```python
from backend.mistral_engine import generate_text

# Generate text with a simple prompt
response = generate_text("Write a short paragraph about language learning:")
print(response)
```

### Translation

```python
from backend.mistral_engine import generate_text

# Translate text from French to English
french_text = "Bonjour, comment allez-vous aujourd'hui?"
prompt = f"Translate this French text to English: \"{french_text}\""
translation = generate_text(prompt)
print(translation)
```

### Complete Language Feedback

```python
from backend.feedback_engine import generate_feedback

# Generate comprehensive language feedback for a journal entry
journal_entry = "Yesterday I goed to the store and buyed some foods."
feedback = generate_feedback(journal_entry)

print(f"Corrected: {feedback['corrected']}")
print(f"Rewritten: {feedback['rewritten']}")
print(f"Fluency Score: {feedback['score']}/100")
print(f"Tone: {feedback['tone']}")
print(f"Translation: {feedback['translation']}")
print(f"Explanation: {feedback['explanation']}")
```

## Examples Script

An example script demonstrating all functionality is included at `backend/example_mistral.py`. To run it:

```bash
cd backend
python example_mistral.py
```

## Troubleshooting

### Memory Issues

If you encounter memory errors:

1. Reduce batch size or input length
2. Use a smaller version of the model
3. Use CPU inference if GPU memory is limited:
   ```python
   os.environ["CUDA_VISIBLE_DEVICES"] = ""  # Force CPU
   ```

### Slow Performance

- First run includes model download and may be slow
- GPU acceleration significantly improves performance
- Consider pre-loading the model for multiple requests

## Additional Resources

- [Mistral-7B-Instruct-v0.3 on Hugging Face](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3)
- [Transformers Documentation](https://huggingface.co/docs/transformers/index)
- [Mistral AI GitHub](https://github.com/mistralai) 