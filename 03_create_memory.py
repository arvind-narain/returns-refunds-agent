#!/usr/bin/env python3
"""
Script to create AgentCore Memory for returns_refunds_agent.

This script creates an AgentCore Memory resource with three memory strategies:
- Summary: Maintains conversation summaries
- Preferences: Extracts and stores user preferences
- Semantic: Stores factual information with semantic search

Memory ID will be saved to memory_config.json
"""

import json
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager

# Define memory strategies in boto3 tagged union format
strategies = [
    {
        "summaryMemoryStrategy": {
            "name": "summary",
            "namespaces": [
                "app/{actorId}/{sessionId}/summary"
            ]
        }
    },
    {
        "userPreferenceMemoryStrategy": {
            "name": "preferences",
            "namespaces": [
                "app/{actorId}/preferences"
            ]
        }
    },
    {
        "semanticMemoryStrategy": {
            "name": "semantic",
            "namespaces": [
                "app/{actorId}/semantic"
            ]
        }
    }
]

print("=" * 80)
print("CREATING AGENTCORE MEMORY FOR RETURNS & REFUNDS AGENT")
print("=" * 80)
print()
print("Configuration:")
print(f"  Name: returns_refunds_memory")
print(f"  Region: us-west-2")
print(f"  Description: Stores customer interactions, preferences, and return history")
print(f"  Strategies: summary, preferences, semantic")
print()

# Create memory manager
memory_manager = MemoryManager(region_name='us-west-2')

# Create memory
print("Creating AgentCore Memory...")
print("⏳ This may take a few moments...")
print()

try:
    memory = memory_manager.get_or_create_memory(
        name="returns_refunds_memory",
        description="Stores customer interactions, preferences, and return history",
        strategies=strategies
    )
    
    # Extract memory_id
    memory_id = memory["id"]
    
    # Save memory_id to config file
    config = {
        "memory_id": memory_id,
        "name": "returns_refunds_memory",
        "region": "us-west-2",
        "description": "Stores customer interactions, preferences, and return history",
        "strategies": ["summary", "preferences", "semantic"],
        "namespaces": {
            "summary": "app/{actorId}/{sessionId}/summary",
            "preferences": "app/{actorId}/preferences",
            "semantic": "app/{actorId}/semantic"
        }
    }
    
    with open('memory_config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print("=" * 80)
    print("✅ SUCCESS!")
    print("=" * 80)
    print()
    print(f"Memory ID: {memory_id}")
    print(f"Memory Name: returns_refunds_memory")
    print()
    print("Memory Strategies Configured:")
    print("  ✓ Summary Strategy - Maintains conversation summaries")
    print("  ✓ Preferences Strategy - Extracts user preferences")
    print("  ✓ Semantic Strategy - Stores facts with semantic search")
    print()
    print("Configuration saved to: memory_config.json")
    print()
    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print()
    print("1. Set environment variable:")
    print(f"   export MEMORY_ID={memory_id}")
    print()
    print("2. Update your agent to use memory")
    print()
    print("Note: Memory strategies process data asynchronously (20-30 seconds)")
    print("=" * 80)
    
except Exception as e:
    print("=" * 80)
    print("❌ ERROR")
    print("=" * 80)
    print(f"Failed to create memory: {e}")
    print()
    import traceback
    traceback.print_exc()
