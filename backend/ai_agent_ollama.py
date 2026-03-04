"""
AI Agent for natural language paper search using Ollama
Supports function calling with local open source models like Llama 3.1/3.3
"""
import json
import re
from typing import List, Dict, Any, Optional
import requests

class OllamaAIAgent:
    """AI agent that uses Ollama for natural language query processing"""

    def __init__(self, model_name: str = "llama3.1:8b", ollama_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.conversation_history = []

    def _call_ollama(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict:
        """Call Ollama API with messages and optional tools"""
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
        }

        # Add tools if provided (for function calling)
        if tools:
            payload["tools"] = tools

        try:
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ollama API error: {str(e)}")

    def parse_search_query(self, user_query: str) -> Dict[str, Any]:
        """
        Parse natural language query into structured search parameters
        Uses the LLM to extract:
        - keywords/query
        - conferences
        - year range
        - author name
        - countries
        - search type (papers vs authors)
        """

        # Define the search papers function tool
        search_papers_tool = {
            "type": "function",
            "function": {
                "name": "search_papers",
                "description": "Search for academic papers. Use this when the user wants to find specific papers, publications, or research documents.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Boolean search query with keywords. Support AND, OR, NOT operators and phrase matching with quotes. Example: 'video generation AND (diffusion OR transformer)'"
                        },
                        "conferences": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by conference names. Available: CVPR, NeurIPS, ICLR, ICML, ECCV, ICCV, ACL, EMNLP, etc."
                        },
                        "year_min": {
                            "type": "integer",
                            "description": "Minimum year (1987-2026)"
                        },
                        "year_max": {
                            "type": "integer",
                            "description": "Maximum year (1987-2026)"
                        },
                        "author": {
                            "type": "string",
                            "description": "Filter by author name (partial match)"
                        },
                        "countries": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by author countries. Common values: USA, China, UK, Germany, France, Canada, etc."
                        }
                    },
                    "required": ["query"]
                }
            }
        }

        # Define the search authors function tool
        search_authors_tool = {
            "type": "function",
            "function": {
                "name": "search_authors",
                "description": "Search for researchers/authors. Use this when the user wants to find people, researchers, authors, or academics working in a field. Examples: 'find authors working on X', 'who are the top researchers in Y', 'show me people from Z'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Research topic or keywords to find authors working on. Example: 'video generation', 'diffusion models', 'transformers'"
                        },
                        "conferences": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by conference names. Available: CVPR, NeurIPS, ICLR, ICML, ECCV, ICCV, ACL, EMNLP, etc."
                        },
                        "year_min": {
                            "type": "integer",
                            "description": "Minimum year (1987-2026)"
                        },
                        "year_max": {
                            "type": "integer",
                            "description": "Maximum year (1987-2026)"
                        },
                        "countries": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Filter by author countries. Common values: USA, China, UK, Germany, France, Canada, etc."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of top authors to return (default 10, max 50)"
                        }
                    },
                    "required": ["topic"]
                }
            }
        }

        # System prompt to guide the LLM
        system_prompt = """You are an AI assistant that helps users search academic papers and find researchers.

Your job is to understand the user's natural language query and convert it into a structured search using either:
- search_papers: When user wants to find papers, publications, or research documents
- search_authors: When user wants to find researchers, authors, people, or academics

Guidelines for choosing the right function:
- "Find papers on X" → search_papers
- "Find authors working on X" → search_authors
- "Who is researching X" → search_authors
- "Show me researchers in X" → search_authors
- "Papers by [name]" → search_papers
- "Top researchers in X" → search_authors

Guidelines for parameters:
- Extract relevant keywords and construct Boolean queries using AND, OR, NOT operators
- Use quotes for exact phrase matching (e.g., "world models")
- Expand abbreviations and synonyms where helpful (e.g., "video" could include "video generation", "video synthesis")
- Infer time ranges from relative terms (e.g., "recent" = last 2-3 years, "latest" = current year)
- Map geographic terms to countries (e.g., "Europe" → UK, Germany, France, etc.)
- Recognize conference abbreviations (e.g., CVPR, NeurIPS, ICLR)

Current year is 2026."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]

        # Call Ollama with function calling
        try:
            response = self._call_ollama(messages, tools=[search_papers_tool, search_authors_tool])

            # Check if model wants to call a function
            message = response.get("message", {})
            tool_calls = message.get("tool_calls", [])

            if tool_calls:
                # Extract the function arguments
                tool_call = tool_calls[0]
                function_name = tool_call.get("function", {}).get("name")
                arguments = tool_call["function"]["arguments"]

                return {
                    "success": True,
                    "function": function_name,
                    "parameters": arguments,
                    "raw_response": response
                }

            # Fallback: try to extract from text response
            content = message.get("content", "")
            return {
                "success": False,
                "error": "Model did not use function calling",
                "text_response": content
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def generate_search_summary(self, query: str, results: Dict[str, Any], search_params: Dict) -> str:
        """
        Generate a natural language summary of search results
        """
        total = results.get("total", 0)
        papers = results.get("results", [])

        # Build context about the search
        context_parts = []
        if search_params.get("conferences"):
            context_parts.append(f"from {', '.join(search_params['conferences'])}")
        if search_params.get("year_min") or search_params.get("year_max"):
            year_min = search_params.get("year_min", "any")
            year_max = search_params.get("year_max", "any")
            context_parts.append(f"published between {year_min} and {year_max}")
        if search_params.get("countries"):
            context_parts.append(f"with authors from {', '.join(search_params['countries'])}")
        if search_params.get("author"):
            context_parts.append(f"by authors matching '{search_params['author']}'")

        context_str = " ".join(context_parts) if context_parts else ""

        prompt = f"""The user searched for: "{query}"
{f"With filters: {context_str}" if context_str else ""}

Found {total} papers total. Here are the top {min(len(papers), 10)} results:

"""
        # Add paper details
        for i, paper in enumerate(papers[:10], 1):
            prompt += f"{i}. {paper.get('title', 'No title')} ({paper.get('year', 'N/A')})\n"
            authors = paper.get('authors_data', [])
            if authors:
                author_names = [a.get('name', 'Unknown') for a in authors[:3]]
                prompt += f"   Authors: {', '.join(author_names)}"
                if len(authors) > 3:
                    prompt += f" + {len(authors) - 3} more"
                prompt += "\n"
            prompt += f"   Conference: {paper.get('conference', 'Unknown')}\n\n"

        prompt += f"\nProvide a brief (2-3 sentences) natural language summary of these search results highlighting key findings, trends, or notable papers."

        messages = [
            {"role": "system", "content": "You are a helpful research assistant. Provide concise, informative summaries of academic paper search results."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = self._call_ollama(messages)
            return response.get("message", {}).get("content", "No summary available")
        except Exception as e:
            return f"Error generating summary: {str(e)}"

    def generate_author_summary(self, query: str, authors: List[Dict], search_params: Dict) -> str:
        """
        Generate a natural language summary of author search results
        """
        total = len(authors)

        # Build context about the search
        context_parts = []
        if search_params.get("topic"):
            context_parts.append(f"working on '{search_params['topic']}'")
        if search_params.get("conferences"):
            context_parts.append(f"publishing at {', '.join(search_params['conferences'])}")
        if search_params.get("year_min") or search_params.get("year_max"):
            year_min = search_params.get("year_min", "any")
            year_max = search_params.get("year_max", "any")
            context_parts.append(f"between {year_min} and {year_max}")
        if search_params.get("countries"):
            context_parts.append(f"from {', '.join(search_params['countries'])}")

        context_str = " ".join(context_parts) if context_parts else ""

        prompt = f"""The user searched for authors: "{query}"
{f"Criteria: {context_str}" if context_str else ""}

Found {total} authors. Here are the top {min(len(authors), 10)}:

"""
        # Add author details
        for i, author in enumerate(authors[:10], 1):
            prompt += f"{i}. {author.get('name', 'Unknown')}\n"
            prompt += f"   Papers: {author.get('paper_count', 0)}\n"
            if author.get('affiliation'):
                prompt += f"   Affiliation: {author.get('affiliation')}\n"
            if author.get('country'):
                prompt += f"   Country: {author.get('country')}\n"
            if author.get('conferences'):
                prompt += f"   Conferences: {', '.join(author['conferences'][:3])}\n"
            prompt += "\n"

        prompt += f"\nProvide a brief (2-3 sentences) natural language summary of these author search results, highlighting key researchers or trends."

        messages = [
            {"role": "system", "content": "You are a helpful research assistant. Provide concise, informative summaries of author search results."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = self._call_ollama(messages)
            return response.get("message", {}).get("content", "No summary available")
        except Exception as e:
            return f"Error generating summary: {str(e)}"

    def answer_question(self, user_query: str, context: Optional[Dict] = None) -> str:
        """
        Answer general questions about papers, authors, or research trends
        """
        system_prompt = """You are an AI research assistant for an academic paper database containing 237,000+ papers from top AI/ML conferences (CVPR, NeurIPS, ICLR, ICML, ECCV, etc.).

You help users:
- Search for papers and authors
- Understand research trends
- Find collaborations and connections
- Discover papers by topic, conference, year, or country

Be helpful, concise, and accurate. If you need to search papers, tell the user what search you would run."""

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        # Add context if provided
        if context:
            context_msg = f"Context: {json.dumps(context, indent=2)}"
            messages.append({"role": "user", "content": context_msg})

        messages.append({"role": "user", "content": user_query})

        try:
            response = self._call_ollama(messages)
            return response.get("message", {}).get("content", "No response")
        except Exception as e:
            return f"Error: {str(e)}"

    def check_ollama_status(self) -> Dict[str, Any]:
        """Check if Ollama is running and the model is available"""
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            response.raise_for_status()

            models = response.json().get("models", [])
            model_names = [m["name"] for m in models]

            return {
                "status": "ok",
                "ollama_running": True,
                "model_available": self.model_name in model_names,
                "available_models": model_names,
                "current_model": self.model_name
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "ollama_running": False,
                "error": "Ollama is not running. Please start Ollama."
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


# Example usage
if __name__ == "__main__":
    agent = OllamaAIAgent()

    # Test status
    status = agent.check_ollama_status()
    print("Status:", json.dumps(status, indent=2))

    # Test query parsing
    test_query = "Find recent papers on video generation from USA authors at CVPR"
    print(f"\nParsing: {test_query}")
    result = agent.parse_search_query(test_query)
    print(json.dumps(result, indent=2))
