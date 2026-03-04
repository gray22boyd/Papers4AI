"""
Test script for AI Agent functionality
Run this to validate your AI agent implementation

Usage:
    python examples/test_ai_agent.py
"""
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from ai_agent import create_agent
from search_engine import search_engine
from config import ANTHROPIC_API_KEY

def test_ai_agent():
    """Test the AI agent with sample queries"""

    print("\n" + "="*60)
    print("AI Agent Test Suite")
    print("="*60)

    # Check API key
    if not ANTHROPIC_API_KEY:
        print("\n❌ ERROR: ANTHROPIC_API_KEY not set in environment")
        print("   Please set it in your .env file or environment variables")
        return False

    print(f"\n✓ API Key found: {ANTHROPIC_API_KEY[:15]}...")

    # Initialize search engine
    print("\n📚 Loading paper database...")
    search_engine.load_data()
    print(f"✓ Loaded {len(search_engine.papers):,} papers")

    # Create AI agent
    print("\n🤖 Initializing AI agent...")
    agent = create_agent(ANTHROPIC_API_KEY)
    print("✓ Agent initialized")

    # Test queries
    test_queries = [
        "Find authors working on video generation in the USA",
        "Show me CVPR 2024 papers on diffusion models",
        "Who are top researchers in transformers from Europe?",
    ]

    results = []

    for i, query in enumerate(test_queries, 1):
        print(f"\n{'─'*60}")
        print(f"Test {i}/{len(test_queries)}: {query}")
        print('─'*60)

        try:
            result = agent.query(
                user_message=query,
                search_engine=search_engine,
                max_tokens=2048
            )

            if "error" in result:
                print(f"❌ Error: {result['error']}")
                results.append(False)
                continue

            # Display results
            print("\n🔍 Search Parameters Used:")
            if result.get("search_params"):
                for key, value in result["search_params"].items():
                    print(f"   {key}: {value}")
            else:
                print("   (No search performed)")

            print("\n🤖 AI Response:")
            response = result["response"]
            # Print first 500 chars
            if len(response) > 500:
                print(f"   {response[:500]}...")
                print(f"   ... ({len(response)} total characters)")
            else:
                print(f"   {response}")

            print(f"\n📊 Tool Calls Made: {len(result.get('tool_calls', []))}")
            for tool_call in result.get("tool_calls", []):
                tool_name = tool_call.get("tool")
                summary = tool_call.get("result_summary", {})
                print(f"   - {tool_name}: {summary.get('total', 0)} results")

            print("\n✅ Query successful")
            results.append(True)

        except Exception as e:
            print(f"\n❌ Query failed: {e}")
            results.append(False)

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed!")
        return True
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return False


def test_specific_query(query: str):
    """Test a specific query"""

    if not ANTHROPIC_API_KEY:
        print("❌ ANTHROPIC_API_KEY not set")
        return

    print("\n" + "="*60)
    print(f"Testing query: {query}")
    print("="*60)

    search_engine.load_data()
    agent = create_agent(ANTHROPIC_API_KEY)

    result = agent.query(
        user_message=query,
        search_engine=search_engine,
        max_tokens=4096
    )

    if "error" in result:
        print(f"\n❌ Error: {result['error']}")
        return

    print("\n🔍 Search Parameters:")
    print(result.get("search_params", "None"))

    print("\n🤖 Response:")
    print(result["response"])

    print(f"\n📊 Tools Used: {len(result.get('tool_calls', []))}")
    for tool_call in result.get("tool_calls", []):
        print(f"   - {tool_call}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test AI Agent")
    parser.add_argument(
        "--query",
        type=str,
        help="Test a specific query instead of running full test suite"
    )

    args = parser.parse_args()

    if args.query:
        test_specific_query(args.query)
    else:
        success = test_ai_agent()
        sys.exit(0 if success else 1)
