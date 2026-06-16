"""
AI module - NutriSnap AI features.

Provides: food recognition, nutrition analysis, AI nutritionist, and LLM API helpers.
"""
import json
import urllib.request
import urllib.error


def call_llm(api_key, api_base, model, messages, max_tokens=800, temperature=0.5):
    """Call LLM API using direct HTTP request (works with any OpenAI-compatible API).

    Args:
        api_key: API key
        api_base: API base URL (e.g. https://api.deepseek.com/v1)
        model: Model name
        messages: List of message dicts
        max_tokens: Max tokens to generate
        temperature: Sampling temperature

    Returns:
        str: LLM response content
    """
    data = json.dumps({
        'model': model,
        'messages': messages,
        'max_tokens': max_tokens,
        'temperature': temperature
    }).encode('utf-8')

    req = urllib.request.Request(
        f'{api_base}/chat/completions',
        data=data,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode())
        return result['choices'][0]['message']['content'].strip()
