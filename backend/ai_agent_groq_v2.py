"""
Robust AI Agent for natural language paper search using Groq API
Version 2.0 - Complete redesign for reliability and simplicity
"""
import json
import os
from typing import List, Dict, Any, Optional
from groq import Groq
import httpx


class GroqAIAgentV2:
    """AI agent that uses Groq API - designed to never fail"""

    def __init__(self, api_key: str = None, model_name: str = "llama-3.3-70b-versatile"):
        """Initialize Groq AI Agent"""
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("Groq API key not provided. Set GROQ_API_KEY environment variable.")

        self.model_name = model_name

        # Create HTTP client with SSL verification disabled (Windows workaround)
        http_client = httpx.Client(verify=False)
        self.client = Groq(api_key=self.api_key, http_client=http_client)

    def _call_groq_simple(self, user_prompt: str, system_prompt: str) -> str:
        """Simple Groq call that returns text response"""
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,  # Lower temp for more consistent output
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[GROQ ERROR] {e}")
            return ""

    def parse_search_query(self, user_query: str) -> Dict[str, Any]:
        """
        Parse natural language query into structured search parameters
        Version 2.0: No function calling - just structured text parsing (more reliable)
        """

        system_prompt = """You are a research search query builder. Convert user queries into JSON format.

OUTPUT FORMAT (respond ONLY with valid JSON, nothing else):
{
  "search_type": "papers" or "authors",
  "query": "search query string",
  "conferences": ["CVPR", "NeurIPS"],  // empty array if not mentioned
  "year_min": 2020,  // omit if not mentioned
  "year_max": 2024,  // omit if not mentioned
  "countries": ["USA", "China"],  // empty array if not mentioned
  "author_name": "John Smith"  // omit if not relevant
}

RULES:
1. search_type: "authors" if looking for people/researchers, "papers" otherwise
2. query: Build a simple search query with 2-4 related keywords
3. DO NOT include year_min/year_max unless user mentions time (recent, latest, 2023, etc)
4. Keep it SIMPLE - complex queries often fail

EXAMPLES:

User: "Find authors working on video generation"
{"search_type": "authors", "query": "video generation OR video synthesis", "conferences": [], "countries": []}

User: "Papers on transformers from 2023-2024"
{"search_type": "papers", "query": "transformer OR attention", "conferences": [], "year_min": 2023, "year_max": 2024, "countries": []}

User: "Recent CVPR papers on diffusion"
{"search_type": "papers", "query": "diffusion OR DDPM", "conferences": ["CVPR"], "year_min": 2024, "countries": []}

User: "Authors in reinforcement learning from USA"
{"search_type": "authors", "query": "reinforcement learning OR RL", "conferences": [], "countries": ["USA"]}

User: "Find people working on 4D in the US"
{"search_type": "authors", "query": "4D OR four-dimensional OR 4D reconstruction", "conferences": [], "countries": ["USA"]}

Now convert this query to JSON:"""

        user_prompt = f'"{user_query}"'

        # Get JSON response from Groq
        response_text = self._call_groq_simple(user_prompt, system_prompt)

        if not response_text:
            return {"success": False, "error": "No response from AI"}

        # Parse JSON response
        try:
            # Clean up response (sometimes LLMs add extra text)
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()

            parsed = json.loads(response_text)

            # Validate and clean up the response
            search_type = parsed.get("search_type", "papers")
            query = parsed.get("query", "")

            if not query:
                return {"success": False, "error": "No search query generated"}

            # Build standardized result
            result = {
                "success": True,
                "function": "search_authors" if search_type == "authors" else "search_papers",
                "parameters": {
                    "query" if search_type == "papers" else "topic": query,
                    "conferences": parsed.get("conferences", []),
                    "countries": parsed.get("countries", [])
                }
            }

            # Only add year filters if they exist and are valid
            if "year_min" in parsed and parsed["year_min"] is not None:
                result["parameters"]["year_min"] = int(parsed["year_min"])
            if "year_max" in parsed and parsed["year_max"] is not None:
                result["parameters"]["year_max"] = int(parsed["year_max"])

            # Only add author if it exists
            if "author_name" in parsed and parsed["author_name"]:
                result["parameters"]["author"] = parsed["author_name"]

            print(f"[AI PARSE] Query: {user_query}")
            print(f"[AI PARSE] Result: {json.dumps(result, indent=2)}")

            return result

        except json.JSONDecodeError as e:
            print(f"[JSON PARSE ERROR] {e}")
            print(f"[JSON PARSE ERROR] Response was: {response_text}")

            # FALLBACK: Try to extract search intent from raw text
            user_query_lower = user_query.lower()

            # Determine if looking for authors or papers
            author_keywords = ["author", "people", "researcher", "who", "find me", "person"]
            is_author_search = any(kw in user_query_lower for kw in author_keywords)

            # Extract potential search terms (very basic)
            search_terms = user_query.replace("find", "").replace("show me", "").replace("in", "").strip()

            return {
                "success": True,
                "function": "search_authors" if is_author_search else "search_papers",
                "parameters": {
                    "query" if not is_author_search else "topic": search_terms,
                    "conferences": [],
                    "countries": []
                },
                "fallback": True
            }

    def generate_search_summary(self, query: str, results: Dict[str, Any], search_params: Dict) -> str:
        """Generate a natural language summary of search results"""
        total = results.get("total", 0)
        papers = results.get("results", [])[:5]

        if total == 0:
            return f"No papers found for '{query}'. Try different keywords or remove filters."

        papers_text = "\n".join([
            f"{i+1}. {p.get('title', 'Untitled')} ({p.get('year', 'N/A')}) - {p.get('conference', 'Unknown')}"
            for i, p in enumerate(papers)
        ])

        prompt = f"""Summarize these search results in 1-2 sentences:

Query: {query}
Found: {total} papers

Top results:
{papers_text}

Provide a brief, informative summary."""

        summary = self._call_groq_simple(prompt, "You are a helpful research assistant.")
        return summary if summary else f"Found {total} papers matching '{query}'."

    def generate_author_summary(self, query: str, authors: List[Dict], search_params: Dict) -> str:
        """Generate a natural language summary of author search results"""
        if not authors:
            return f"No authors found for '{query}'. Try different keywords or broaden your search."

        authors_text = "\n".join([
            f"{i+1}. {a.get('name', 'Unknown')} - {a.get('paper_count', 0)} papers ({a.get('affiliation', 'N/A')})"
            for i, a in enumerate(authors[:5])
        ])

        prompt = f"""Summarize these author search results in 1-2 sentences:

Query: {query}
Found: {len(authors)} authors

Top authors:
{authors_text}

Provide a brief, informative summary."""

        summary = self._call_groq_simple(prompt, "You are a helpful research assistant.")
        return summary if summary else f"Found {len(authors)} authors working on '{query}'."

    def check_status(self) -> Dict[str, Any]:
        """Check if Groq API is accessible"""
        try:
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


# For backwards compatibility
GroqAIAgent = GroqAIAgentV2
