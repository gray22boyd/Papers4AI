"""
AI Agent for natural language paper search using Groq API
Supports function calling with Groq's hosted models (Llama 3.3, Mixtral, etc.)
"""
import json
import os
from typing import List, Dict, Any, Optional
from groq import Groq
import httpx

class GroqAIAgent:
    """AI agent that uses Groq API for natural language query processing"""

    def __init__(self, api_key: str = None, model_name: str = "llama-3.3-70b-versatile"):
        """
        Initialize Groq AI Agent

        Args:
            api_key: Groq API key (if not provided, reads from GROQ_API_KEY env var)
            model_name: Model to use (default: llama-3.3-70b-versatile)
                       Options: llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key not provided. Set GROQ_API_KEY environment variable.")

        self.model_name = model_name

        # Create HTTP client with SSL verification disabled (Windows SSL certificate workaround)
        # This is needed for corporate networks with custom SSL certificates
        http_client = httpx.Client(verify=False)
        self.client = Groq(api_key=self.api_key, http_client=http_client)
        self.conversation_history = []

    def _call_groq(self, messages: List[Dict], tools: Optional[List[Dict]] = None) -> Dict:
        """Call Groq API with messages and optional tools"""
        try:
            kwargs = {
                "model": self.model_name,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000,
            }

            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = self.client.chat.completions.create(**kwargs)

            # Convert to dict format
            return {
                "message": {
                    "content": response.choices[0].message.content,
                    "tool_calls": [
                        {
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": json.loads(tool_call.function.arguments)
                            }
                        }
                        for tool_call in (response.choices[0].message.tool_calls or [])
                    ]
                }
            }
        except Exception as e:
            raise Exception(f"Groq API error: {str(e)}")

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
        system_prompt = """You are an intelligent research sourcing agent for an academic database with 237,000+ AI/ML papers from top conferences.

FUNCTION SELECTION:
- search_papers: When user wants to find papers, publications, or research documents
- search_authors: When user wants to find researchers, authors, people, or academics working in a field

QUERY CONSTRUCTION RULES - FOLLOW EXACTLY:

1. START SIMPLE, EXPAND CAREFULLY:
   - Always include the base term first
   - Add 2-4 closely related synonyms or abbreviations
   - Don't over-complicate - queries that are too complex often return zero results

   Examples:
   ✅ GOOD: "reinforcement learning OR RL OR \"policy gradient\" OR Q-learning"
   ✅ GOOD: "video generation OR \"video synthesis\" OR \"temporal generation\""
   ❌ BAD: Too many OR clauses (>6), overly specific combinations with AND

2. FOR BROAD TOPICS, USE CORE TERMS:
   - "Reinforcement Learning" → "reinforcement learning OR RL"
   - "Computer Vision" → "computer vision OR vision"
   - "NLP" → "natural language processing OR NLP OR language model"
   - "Deep Learning" → "deep learning OR neural network"

3. FOR SPECIFIC TOPICS, ADD KEY METHODS:
   - "Diffusion Models" → "diffusion OR DDPM OR \"score-based\""
   - "Transformers" → "transformer OR attention OR BERT OR GPT"
   - "GANs" → "GAN OR \"generative adversarial\" OR StyleGAN"

4. YEAR HANDLING - BE CONSERVATIVE:
   - If user says "recent": year_min=2022 (NOT 2024 - too restrictive!)
   - If user says "latest": year_min=2024
   - If user doesn't mention time: DON'T SET year_min/year_max (None) - let all years through
   - NEVER set year_max unless explicitly requested

5. GEOGRAPHY:
   - "US" or "USA" or "United States" → countries: ["USA"]
   - "Europe" → ["UK", "Germany", "France", "Switzerland", "Netherlands"]
   - "Asia" → ["China", "Japan", "South Korea", "Singapore"]

6. CONFERENCES:
   - Only specify conferences if user explicitly mentions them
   - Otherwise leave conferences empty to search all

CRITICAL RULES:
- PREFER SIMPLER QUERIES: A simple query that returns 1000 results is better than a complex query that returns 0
- ALWAYS RETURN A VALID QUERY: Never return empty topic/query
- TEST MENTALLY: Would this query match papers in the field? If uncertain, simplify!
- DON'T ADD year filters unless user specifically mentions time period

Current year is 2026."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]

        # Call Groq with function calling
        try:
            response = self._call_groq(messages, tools=[search_papers_tool, search_authors_tool])

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
            response = self._call_groq(messages)
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
            response = self._call_groq(messages)
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
            response = self._call_groq(messages)
            return response.get("message", {}).get("content", "No response")
        except Exception as e:
            return f"Error: {str(e)}"

    def check_status(self) -> Dict[str, Any]:
        """Check if Groq API is accessible and working"""
        try:
            # Simple test call
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )

            return {
                "status": "ok",
                "groq_accessible": True,
                "model": self.model_name,
                "api_key_configured": bool(self.api_key)
            }
        except Exception as e:
            return {
                "status": "error",
                "groq_accessible": False,
                "error": str(e)
            }


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    agent = GroqAIAgent()

    # Test status
    status = agent.check_status()
    print("Status:", json.dumps(status, indent=2))

    # Test query parsing
    test_query = "Find authors working on video generation from USA"
    print(f"\nParsing: {test_query}")
    result = agent.parse_search_query(test_query)
    print(json.dumps(result, indent=2))
