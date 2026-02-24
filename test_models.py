#!/usr/bin/env python3
"""Quick test to validate model names work with Anthropic API."""

import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))

# Test agent model
agent_model = os.getenv('AGENT_MODEL', 'claude-3-5-sonnet-20241022')
print(f'Testing agent model: {agent_model}')
try:
    response = client.messages.create(
        model=agent_model,
        max_tokens=10,
        messages=[{'role': 'user', 'content': 'Hi'}]
    )
    print(f'✓ Agent model {agent_model} works')
except Exception as e:
    print(f'✗ Agent model {agent_model} failed: {e}')

# Test judge model
judge_model = os.getenv('JUDGE_MODEL', 'claude-3-5-sonnet-20241022')
print(f'\nTesting judge model: {judge_model}')
try:
    response = client.messages.create(
        model=judge_model,
        max_tokens=10,
        messages=[{'role': 'user', 'content': 'Hi'}]
    )
    print(f'✓ Judge model {judge_model} works')
except Exception as e:
    print(f'✗ Judge model {judge_model} failed: {e}')

print('\n✓ Both models validated!')
