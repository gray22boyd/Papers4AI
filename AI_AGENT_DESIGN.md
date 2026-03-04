# AI Agent Integration for Papers4AI
## Comprehensive Design Document for Candidate Sourcing Automation

**Version:** 1.0
**Date:** March 3, 2026
**Author:** AI Architecture Design Team

---

## Executive Summary

This document outlines a comprehensive strategy to integrate an AI agent into the Papers4AI platform to enable natural language-based candidate sourcing automation. The solution will transform queries like "find me authors with papers in video generation in the US" into structured searches, automatically filtering and ranking candidates based on research expertise, geographic location, publication history, and other relevant criteria.

---

## 1. Current System Architecture Analysis

### 1.1 Existing Infrastructure

**Backend (Python Flask):**
- **Main API:** `/c/Users/graboyd/Desktop/MyBottleRocketProject/Papers4AI/backend/app.py`
- **Search Engine:** `/c/Users/graboyd/Desktop/MyBottleRocketProject/Papers4AI/backend/search_engine.py`
- **Authentication:** User/session management with role-based access
- **Notes System:** Author note tracking for recruiters

**Data Structure:**
- **Total Papers:** 237,735 papers from major AI/ML conferences
- **Paper Schema:**
  ```json
  {
    "id": int,
    "title": str,
    "abstract": str,
    "authors": str,
    "authors_data": [
      {
        "name": str,
        "affiliation": str,
        "country": str,
        "google_scholar": str,
        "homepage": str,
        "dblp": str,
        "linkedin": str,
        "orcid": str
      }
    ],
    "year": int,
    "conference": str,
    "countries": [str],
    "keywords": [str]
  }
  ```

**Current Search Capabilities:**
- Boolean query parsing (AND, OR, NOT, phrase matching)
- Filters: conference, year range, author name, country
- Relevance scoring (title weight: 3x, abstract weight: 1x, phrase multiplier: 2x)
- Author profile aggregation with co-authors, affiliations, publication counts

**Frontend:**
- Single-page vanilla JavaScript application
- 3,194 lines of HTML/CSS/JS in `/frontend/index.html`
- Search interface with filter dropdowns
- Author popovers with profile links and notes

### 1.2 Key Strengths for AI Integration

1. **Rich Author Metadata:** Countries, affiliations, links already indexed
2. **Author Index:** Pre-built author profiles with publication history
3. **Boolean Search Engine:** Existing sophisticated text matching
4. **Authentication System:** Ready for premium AI features
5. **Notes System:** Can store AI-generated candidate insights

### 1.3 Current Gaps

1. No natural language query processing
2. No automated candidate ranking/scoring
3. No query history or saved searches
4. No batch candidate extraction
5. No conversational interface

---

## 2. AI Agent Integration Approaches

### 2.1 Approach A: Function-Calling LLM Backend (RECOMMENDED)

**Architecture:**
```
User Query → AI Agent API → Claude/GPT-4 → Function Calls → Search Engine → Results → AI Summary → User
```

**Components:**

1. **AI Agent Service** (`backend/ai_agent.py`)
   - Natural language query parser
   - Uses Claude 3.5 Sonnet or GPT-4 with function calling
   - Translates user intent into search parameters
   - Iterative query refinement

2. **Query Translation Pipeline:**
   ```python
   User: "Find authors in video generation from US with CVPR papers"
   ↓
   AI extracts:
   {
     "keywords": ["video generation", "video synthesis", "video diffusion"],
     "countries": ["USA"],
     "conferences": ["CVPR"],
     "additional_filters": {
       "year_min": 2020,  # recent work implied
       "first_author_preference": true
     }
   }
   ↓
   Search Engine Query
   ↓
   Ranked Results + AI Summary
   ```

3. **New API Endpoints:**
   - `POST /api/ai/query` - Natural language search
   - `POST /api/ai/refine` - Refine existing query
   - `GET /api/ai/history` - Query history
   - `POST /api/ai/batch-extract` - Extract top N candidates
   - `POST /api/ai/compare-authors` - Compare multiple authors

**Pros:**
- Leverages existing search infrastructure
- Cost-effective (only API calls, no model hosting)
- Easy to iterate and improve prompts
- Claude API provides excellent reasoning
- Can use tool use for multi-step queries

**Cons:**
- Requires API keys and incurs per-query costs
- Network latency for API calls
- Rate limits on external APIs

**Cost Estimate:**
- Claude 3.5 Sonnet: ~$0.003 per query (with function calling)
- GPT-4 Turbo: ~$0.005 per query
- Expected: $50-100/month for 10,000-20,000 queries

---

### 2.2 Approach B: Local Embedding + Semantic Search

**Architecture:**
```
Papers → Embedding Model (local) → Vector DB →
User Query → Embed Query → Semantic Search → Rerank → Results
```

**Components:**

1. **Embedding Pipeline:**
   - Use sentence-transformers (e.g., `all-MiniLM-L6-v2`)
   - Embed paper titles + abstracts
   - Store in ChromaDB or FAISS

2. **Hybrid Search:**
   - Semantic search for concept matching
   - Boolean search for precise filtering
   - Combine scores with weighted fusion

**Pros:**
- No per-query API costs
- Fast local inference
- Privacy-preserving (no external API calls)
- Good for semantic similarity

**Cons:**
- Requires embedding generation upfront (237K papers)
- Storage overhead for vectors (~2GB)
- Less intelligent query understanding than LLMs
- Can't handle complex multi-step reasoning

**Cost Estimate:**
- One-time setup: ~$0 (open-source models)
- Ongoing: Server storage/compute only

---

### 2.3 Approach C: Hybrid (LLM + Embeddings)

**Architecture:**
```
User Query → LLM (query parsing) →
  ├─ Semantic Search (embeddings)
  └─ Boolean Search (existing)
       ↓
    Merge Results → LLM (ranking & summary) → User
```

**Components:**
- LLM for query understanding and result synthesis
- Local embeddings for semantic concept matching
- Existing Boolean engine for precise filtering

**Pros:**
- Best of both worlds
- Intelligent query parsing + semantic relevance
- Fallback to Boolean for precision

**Cons:**
- Most complex to implement
- Higher initial setup cost
- Maintenance overhead

---

## 3. RECOMMENDED SOLUTION: Function-Calling LLM Backend

### 3.1 Technical Implementation Plan

#### Phase 1: AI Agent Backend (Week 1-2)

**File: `backend/ai_agent.py`**

```python
"""
AI Agent for Natural Language Candidate Sourcing
Uses Claude API with function calling to translate queries
"""
import anthropic
import json
from typing import Dict, List, Optional
from search_engine import search_engine

class CandidateSourcingAgent:
    """AI agent for natural language paper and author search"""

    def __init__(self, api_key: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.conversation_history = []

    def query(self, user_message: str, max_results: int = 20) -> Dict:
        """
        Process natural language query and return search results

        Args:
            user_message: User's natural language query
            max_results: Maximum number of results to return

        Returns:
            {
                "search_params": {...},
                "results": [...],
                "summary": "AI-generated summary",
                "suggestions": ["follow-up question 1", ...]
            }
        """

        # Define tools for the AI agent
        tools = [
            {
                "name": "search_papers",
                "description": "Search academic papers by keywords, filters, and constraints. Returns papers matching the criteria.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Boolean search query with keywords (supports AND, OR, NOT, phrases)"
                        },
                        "conferences": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Conference names to filter by (e.g., ['CVPR', 'NeurIPS'])"
                        },
                        "year_min": {
                            "type": "integer",
                            "description": "Minimum publication year"
                        },
                        "year_max": {
                            "type": "integer",
                            "description": "Maximum publication year"
                        },
                        "countries": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Countries to filter authors by (e.g., ['USA', 'UK'])"
                        },
                        "author": {
                            "type": "string",
                            "description": "Author name to search for (partial match)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_author_profile",
                "description": "Get detailed profile for a specific author including all papers, co-authors, affiliations",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "author_name": {
                            "type": "string",
                            "description": "Full or partial author name"
                        }
                    },
                    "required": ["author_name"]
                }
            },
            {
                "name": "get_available_conferences",
                "description": "Get list of all available conferences with paper counts",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_available_countries",
                "description": "Get list of all countries with author counts",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

        # System prompt for the agent
        system_prompt = """You are an expert AI research recruiter assistant. Your role is to help users find academic authors and papers based on their research interests and criteria.

When a user asks to find authors or papers:
1. Extract key information: research topics, geographic constraints, conference preferences, time ranges
2. Translate into appropriate search queries and filters
3. Use the available tools to search the database
4. Analyze results and provide insightful summaries
5. Suggest relevant follow-up questions

For research topics:
- Expand keywords with related terms (e.g., "video generation" → "video generation OR video synthesis OR video diffusion")
- Consider both specific and general terms
- Use phrase matching for exact concepts (e.g., "world models")

For author finding:
- Focus on first-author papers when looking for independent researchers
- Consider recent publications (last 2-3 years) for active researchers
- Note affiliations and countries from the data

Always provide:
- A clear summary of findings
- Key insights about the authors/papers found
- Suggestions for refining the search"""

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Call Claude with function calling
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=self.conversation_history
        )

        # Process tool calls
        tool_results = []
        search_params = {}

        while response.stop_reason == "tool_use":
            # Execute tool calls
            for content_block in response.content:
                if content_block.type == "tool_use":
                    tool_name = content_block.name
                    tool_input = content_block.input

                    # Execute the tool
                    if tool_name == "search_papers":
                        search_params = tool_input
                        result = search_engine.search(
                            query=tool_input.get("query", ""),
                            conferences=tool_input.get("conferences"),
                            year_min=tool_input.get("year_min"),
                            year_max=tool_input.get("year_max"),
                            countries=tool_input.get("countries"),
                            author=tool_input.get("author"),
                            limit=max_results
                        )
                    elif tool_name == "get_author_profile":
                        result = search_engine.get_author_profile(tool_input["author_name"])
                    elif tool_name == "get_available_conferences":
                        result = search_engine.get_conferences()
                    elif tool_name == "get_available_countries":
                        result = search_engine.get_countries()
                    else:
                        result = {"error": f"Unknown tool: {tool_name}"}

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": json.dumps(result)
                    })

            # Continue conversation with tool results
            self.conversation_history.append({"role": "assistant", "content": response.content})
            self.conversation_history.append({"role": "user", "content": tool_results})

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                system=system_prompt,
                tools=tools,
                messages=self.conversation_history
            )
            tool_results = []

        # Extract final response
        assistant_message = ""
        for content_block in response.content:
            if hasattr(content_block, "text"):
                assistant_message += content_block.text

        self.conversation_history.append({"role": "assistant", "content": assistant_message})

        return {
            "search_params": search_params,
            "response": assistant_message,
            "conversation_history": self.conversation_history
        }
```

**File: `backend/config.py` (additions)**

```python
# AI Agent Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AI_AGENT_ENABLED = bool(ANTHROPIC_API_KEY)
AI_MAX_CONVERSATION_LENGTH = 20  # Maximum messages in conversation history
AI_CACHE_TIMEOUT = 3600  # Cache query results for 1 hour
```

**File: `backend/app.py` (new endpoints)**

```python
from ai_agent import CandidateSourcingAgent

# Initialize AI agent if enabled
ai_agent = None
if config.AI_AGENT_ENABLED:
    ai_agent = CandidateSourcingAgent(config.ANTHROPIC_API_KEY)

@app.route("/api/ai/query", methods=["POST"])
@require_auth
@limiter.limit("20 per hour")  # Stricter limit for AI queries
def ai_query():
    """
    Natural language search powered by AI agent

    Request:
        {
            "message": "find me authors with papers in video generation in the US",
            "max_results": 20,
            "conversation_id": "optional-session-id"
        }

    Response:
        {
            "search_params": {...},
            "response": "AI-generated response with insights",
            "conversation_id": "session-id",
            "suggestions": ["follow-up question 1", ...]
        }
    """
    if not ai_agent:
        return jsonify({"error": "AI agent not enabled. Please configure ANTHROPIC_API_KEY"}), 503

    try:
        data = request.get_json() or {}
        message = data.get("message", "").strip()
        max_results = min(int(data.get("max_results", 20)), 50)

        if not message:
            return jsonify({"error": "Message is required"}), 400

        # Process query
        result = ai_agent.query(message, max_results=max_results)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/ai/extract-candidates", methods=["POST"])
@require_auth
@limiter.limit("10 per hour")
def ai_extract_candidates():
    """
    Extract and rank candidates based on natural language criteria

    Request:
        {
            "message": "Find top 10 authors in diffusion models from USA or UK",
            "ranking_criteria": {
                "prefer_first_author": true,
                "prefer_recent": true,
                "min_papers": 3
            }
        }

    Response:
        {
            "candidates": [
                {
                    "name": "Author Name",
                    "paper_count": 12,
                    "first_author_count": 8,
                    "recent_papers": 5,
                    "score": 0.95,
                    "reasoning": "AI explanation of why this candidate matches",
                    "affiliations": [...],
                    "top_papers": [...]
                }
            ],
            "summary": "Overall insights about the candidate pool"
        }
    """
    # Implementation here
    pass

@app.route("/api/ai/compare", methods=["POST"])
@require_auth
def ai_compare_authors():
    """
    Compare multiple authors side-by-side with AI insights

    Request:
        {
            "authors": ["Author 1", "Author 2", "Author 3"],
            "comparison_aspects": ["research_focus", "publication_velocity", "collaborations"]
        }

    Response:
        {
            "comparison_table": {...},
            "insights": "AI-generated comparative analysis",
            "recommendations": "Which author to prioritize and why"
        }
    """
    pass
```

---

#### Phase 2: Frontend Chat Interface (Week 2-3)

**New UI Components:**

1. **AI Search Tab** (add to existing search interface)
   - Chat-style interface alongside traditional search
   - Message history display
   - Suggested follow-up questions
   - "Export candidates" button

2. **Candidate List View**
   - Ranked author cards with AI-generated insights
   - Side-by-side comparison mode
   - Bulk export to CSV
   - Integration with existing notes system

**File: `frontend/index.html` (additions)**

```html
<!-- AI Search Tab (add to search section) -->
<div id="ai-search-panel" class="search-panel" style="display: none;">
    <div class="ai-chat-container">
        <div class="ai-messages" id="ai-messages">
            <div class="ai-welcome-message">
                <h3>AI Candidate Sourcing Assistant</h3>
                <p>Ask me to find authors and papers using natural language. For example:</p>
                <ul>
                    <li>"Find authors working on video generation in the US"</li>
                    <li>"Show me CVPR papers on diffusion models from 2023-2024"</li>
                    <li>"Who are the top researchers in world models from DeepMind?"</li>
                </ul>
            </div>
        </div>

        <div class="ai-input-container">
            <textarea
                id="ai-query-input"
                placeholder="Ask me to find authors or papers..."
                rows="2"
            ></textarea>
            <button id="ai-send-btn" class="primary-btn">
                Send
            </button>
        </div>

        <div class="ai-suggestions" id="ai-suggestions">
            <!-- Dynamically populated with suggested follow-ups -->
        </div>
    </div>

    <div class="ai-results-panel" id="ai-results-panel">
        <!-- AI search results displayed here -->
    </div>
</div>

<script>
// AI Search functionality
class AISearchInterface {
    constructor() {
        this.conversationId = null;
        this.messageHistory = [];
    }

    async sendQuery(message) {
        try {
            const response = await fetch(`${API_BASE}/api/ai/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${getAuthToken()}`
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: this.conversationId,
                    max_results: 20
                })
            });

            const data = await response.json();

            if (data.error) {
                this.displayError(data.error);
                return;
            }

            // Display AI response
            this.displayMessage('user', message);
            this.displayMessage('assistant', data.response);

            // Show suggestions
            if (data.suggestions) {
                this.displaySuggestions(data.suggestions);
            }

            // Display search results if any
            if (data.search_params) {
                this.displaySearchResults(data.search_params);
            }

            this.conversationId = data.conversation_id;

        } catch (error) {
            console.error('AI query failed:', error);
            this.displayError('Failed to process your query. Please try again.');
        }
    }

    displayMessage(role, content) {
        const messagesDiv = document.getElementById('ai-messages');
        const messageEl = document.createElement('div');
        messageEl.className = `ai-message ai-message-${role}`;
        messageEl.innerHTML = `
            <div class="message-content">${this.formatMessage(content)}</div>
            <div class="message-timestamp">${new Date().toLocaleTimeString()}</div>
        `;
        messagesDiv.appendChild(messageEl);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    formatMessage(content) {
        // Convert markdown-style formatting to HTML
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }

    displaySuggestions(suggestions) {
        const suggestionsDiv = document.getElementById('ai-suggestions');
        suggestionsDiv.innerHTML = suggestions.map(s =>
            `<button class="suggestion-chip" onclick="aiSearch.sendQuery('${s}')">${s}</button>`
        ).join('');
    }
}

// Initialize AI search
const aiSearch = new AISearchInterface();

document.getElementById('ai-send-btn').addEventListener('click', () => {
    const input = document.getElementById('ai-query-input');
    const message = input.value.trim();
    if (message) {
        aiSearch.sendQuery(message);
        input.value = '';
    }
});
</script>
```

---

#### Phase 3: Advanced Features (Week 3-4)

1. **Query History & Saved Searches**
   - Store user's AI queries and results
   - Allow replaying/refining past searches
   - Share searches with team members

2. **Candidate Collections**
   - Create named collections of authors
   - Add AI-generated tags and insights
   - Export collections with customizable fields

3. **Smart Alerts**
   - Monitor for new papers from tracked authors
   - Alert when new candidates match saved searches
   - Weekly digest of relevant publications

---

### 3.2 Example Queries and Expected Behavior

#### Query 1: Basic Author Search
```
User: "Find authors working on video generation in the US"

AI Agent Processing:
1. Extracts keywords: ["video generation", "video synthesis", "video diffusion", "video modeling"]
2. Extracts country filter: ["USA"]
3. Infers year range: 2022-2024 (recent work)
4. Calls search_papers with expanded query
5. Groups results by author
6. Ranks by publication count and recency

Response:
"I found 47 authors working on video generation in the USA with recent publications.
Here are the top researchers:

Top 5 Authors:
1. **Saining Xie** (Meta AI / NYU)
   - 8 papers on video generation (2022-2024)
   - 5 first-author CVPR/NeurIPS papers
   - Key work: "VideoMAE", "Masked Autoencoders"

2. **William Peebles** (UC Berkeley)
   - 6 papers on diffusion models for video
   - Notable: "Scalable Diffusion Models with Transformers"
   - Affiliations: UC Berkeley, OpenAI

[... more candidates ...]

Would you like me to:
- Filter by specific conferences (CVPR, NeurIPS)?
- Focus on first-author papers only?
- Show authors from specific institutions?"
```

#### Query 2: Complex Multi-Criteria Search
```
User: "Show me CVPR 2024 papers on world models from UK or European researchers"

AI Processing:
1. Conference: ["CVPR"]
2. Year: 2024
3. Keywords: "world models"
4. Countries: ["UK", "Germany", "France", "Switzerland", "Netherlands", ...]
5. Executes search
6. Enriches with author profiles

Response:
"Found 12 CVPR 2024 papers on world models from European researchers.

**Key Findings:**
- UK leads with 5 papers (Oxford: 3, Cambridge: 2)
- Strong representation from ETH Zurich (2 papers)
- Emerging trend: combining world models with diffusion processes

**Top Papers:**
1. "Scaling World Models for Visual Planning"
   - Authors: J. Smith et al. (Oxford)
   - First author: Jane Smith (PhD student, VGG group)

2. "Latent World Models for Robotics"
   - Authors: M. Chen et al. (ETH Zurich)
   - Collaboration with Google DeepMind

[Export candidates] [View all papers] [Refine search]"
```

#### Query 3: Comparative Analysis
```
User: "Compare the research output of Yann LeCun and Yoshua Bengio in the last 3 years"

AI Processing:
1. Fetches author profiles for both
2. Filters papers from 2021-2024
3. Analyzes publication patterns, collaborations, topics
4. Generates comparative summary

Response:
"**Comparison: Yann LeCun vs. Yoshua Bengio (2021-2024)**

| Metric | Yann LeCun | Yoshua Bengio |
|--------|------------|---------------|
| Total Papers | 28 | 34 |
| First Author | 3 | 5 |
| Top Conferences | NeurIPS (12), ICML (8) | NeurIPS (15), ICLR (10) |
| Primary Topics | Self-supervised learning, Energy-based models | Deep learning theory, AI safety |
| Key Collaborators | Meta AI team | Mila researchers |

**Research Focus Differences:**
- LeCun: More industry-focused (Meta AI), emphasis on practical SSL methods
- Bengio: Broader academic collaborations, theoretical foundations + ethics

**Recommendation:**
For practical ML engineering roles → LeCun's group (Meta)
For research/academic positions → Bengio's group (Mila)"
```

---

### 3.3 Cost and Performance Projections

**API Costs (Claude 3.5 Sonnet):**
- Average query: 2-3 function calls
- Input tokens: ~500 (system prompt + user message + function schemas)
- Output tokens: ~800 (reasoning + response)
- Cost per query: $0.003 - $0.005

**Monthly Cost Scenarios:**
- Light use (100 queries/month): ~$0.50
- Medium use (1,000 queries/month): ~$5
- Heavy use (10,000 queries/month): ~$50
- Enterprise (100,000 queries/month): ~$500

**Performance:**
- Query latency: 2-5 seconds (including API calls)
- Search execution: <100ms (existing engine)
- Total user-perceived latency: 3-6 seconds

**Optimization Strategies:**
- Cache common queries (e.g., "available conferences")
- Stream responses for better UX
- Batch similar queries
- Use Claude's prompt caching for system prompts

---

## 4. Alternative Model Options

### 4.1 Claude vs OpenAI Comparison

| Feature | Claude 3.5 Sonnet | GPT-4 Turbo |
|---------|-------------------|-------------|
| **Function Calling** | Excellent, native tool use | Good, JSON mode |
| **Cost** | $3/$15 per 1M tokens | $10/$30 per 1M tokens |
| **Context Window** | 200K tokens | 128K tokens |
| **Reasoning Quality** | Superior for complex queries | Good, but more verbose |
| **Latency** | ~2s average | ~3s average |
| **Prompt Caching** | Yes (90% cost reduction) | Limited |

**Recommendation:** Claude 3.5 Sonnet for better cost-effectiveness and reasoning.

### 4.2 Local Model Options (Budget Alternative)

If API costs are prohibitive:

**Option 1: Llama 3.1 70B**
- Open-source, can self-host
- Good function calling with proper prompting
- Requires GPU server (~$500/month for hosting)

**Option 2: Mixtral 8x7B**
- Lighter than Llama 70B
- Decent reasoning capabilities
- Can run on consumer hardware with quantization

**Trade-offs:**
- Local models: No per-query cost, but worse reasoning
- Hosted models: Better reasoning, pay-per-use
- Hybrid: Use Claude for complex queries, local for simple ones

---

## 5. Implementation Roadmap

### Week 1-2: Backend Foundation
- [ ] Set up Claude API integration
- [ ] Implement `ai_agent.py` with function calling
- [ ] Add `/api/ai/query` endpoint
- [ ] Test query translation with sample queries
- [ ] Add error handling and rate limiting

### Week 2-3: Frontend Interface
- [ ] Design chat UI component
- [ ] Implement message rendering
- [ ] Add conversation state management
- [ ] Integrate with existing search results display
- [ ] Mobile responsive design

### Week 3-4: Advanced Features
- [ ] Query history and saved searches
- [ ] Candidate collections/lists
- [ ] Batch export functionality
- [ ] AI-generated candidate summaries
- [ ] Comparison view

### Week 4-5: Testing & Optimization
- [ ] User acceptance testing
- [ ] Prompt engineering optimization
- [ ] Cost monitoring dashboard
- [ ] Performance profiling
- [ ] Documentation

### Week 5-6: Launch & Iteration
- [ ] Beta release to select users
- [ ] Gather feedback
- [ ] Iterate on prompts and features
- [ ] Public launch

---

## 6. Challenges and Mitigation Strategies

### Challenge 1: Query Ambiguity
**Problem:** "Find authors in vision" could mean computer vision OR visionary work

**Mitigation:**
- Contextual disambiguation in prompts
- Ask clarifying questions in response
- Learn from user feedback/refinements

### Challenge 2: Hallucination/Inaccuracy
**Problem:** AI might invent authors or papers that don't exist

**Mitigation:**
- Use ONLY function calls to retrieve data (no generative answers without verification)
- Include disclaimer: "Results based on database search"
- Show search parameters used for transparency

### Challenge 3: Cost Control
**Problem:** Unchecked API usage could lead to high costs

**Mitigation:**
- Strict rate limiting (20 queries/hour per user)
- Cache common queries
- Use prompt caching for system prompts
- Monitor costs with usage dashboards
- Implement user quotas (free tier: 10/month, premium: unlimited)

### Challenge 4: Complex Queries Requiring Multiple Steps
**Problem:** "Find authors who transitioned from NLP to vision in the last 2 years"

**Mitigation:**
- Use agentic loops (multiple function calls)
- Break down complex queries into sub-queries
- Show reasoning steps to user
- Allow manual refinement at each step

### Challenge 5: Data Freshness
**Problem:** Paper database may be outdated

**Mitigation:**
- Add "last updated" timestamp to responses
- Implement incremental data updates
- Add arxiv.org integration for latest papers
- Show publication dates prominently

---

## 7. Success Metrics

### User Engagement
- **AI Query Adoption Rate:** % of users who try AI search
- **Repeat Usage:** % of users who use AI search >3 times
- **Query Success Rate:** % of queries that lead to results
- **Refinement Rate:** % of queries that are refined (indicates engagement)

### Business Impact
- **Time Saved:** Avg. time to find candidates (before vs after)
- **Candidate Quality:** Relevance ratings from recruiters
- **Conversion Rate:** % of AI-found candidates that are contacted
- **User Satisfaction:** NPS score for AI feature

### Technical Metrics
- **Query Latency:** p50, p95, p99
- **API Cost per Query:** Average cost
- **Error Rate:** % of failed queries
- **Cache Hit Rate:** % of queries served from cache

---

## 8. Future Enhancements

### Phase 2 Features (3-6 months)

1. **Multi-Modal Search**
   - Upload paper PDFs, extract authors
   - Image-based search (find papers with similar figures)
   - Video presentation analysis

2. **Proactive Recommendations**
   - "You might also be interested in..." suggestions
   - Auto-discovery of rising stars in fields
   - Trend analysis: "Video generation is trending up 40% this year"

3. **Collaboration Network Analysis**
   - Visualize author collaboration graphs
   - Identify research communities
   - Find bridge researchers between fields

4. **Integration with External Sources**
   - Semantic Scholar API
   - arXiv.org for latest preprints
   - GitHub for code repositories
   - Twitter/LinkedIn for profiles

5. **Advanced Ranking Models**
   - Train custom ML model for candidate scoring
   - Learn from recruiter feedback (which authors were contacted)
   - Personalized ranking based on company preferences

---

## 9. Conclusion and Next Steps

### Recommended Approach Summary

**Primary Solution:** Function-calling LLM backend with Claude 3.5 Sonnet

**Why this approach wins:**
1. Fastest time-to-market (2-3 weeks to MVP)
2. Leverages existing search infrastructure
3. Cost-effective at projected scale ($50-200/month)
4. Excellent reasoning quality from Claude
5. Easy to iterate on prompts
6. No infrastructure overhead (serverless)

### Immediate Next Steps

1. **Get API Key:** Obtain Claude API key (anthropic.com)
2. **Prototype:** Build minimal `ai_agent.py` with 1-2 function calls
3. **Test Queries:** Validate with 10-20 sample recruiting queries
4. **Estimate Costs:** Monitor token usage on test queries
5. **Design UI:** Mockup chat interface
6. **Stakeholder Review:** Demo prototype to team
7. **Go/No-Go Decision:** Decide to proceed with full implementation

### Resource Requirements

**Development:**
- 1 Backend Engineer (3-4 weeks)
- 1 Frontend Engineer (2-3 weeks)
- 1 AI/Prompt Engineer (ongoing refinement)

**Costs:**
- Claude API: $50-200/month (scales with usage)
- Infrastructure: $0 (uses existing backend)
- Total: <$300/month operational cost

### Risk Assessment

**Low Risk:**
- Technical feasibility (well-proven approach)
- Cost predictability (usage-based, capped)
- User experience (chat UX is familiar)

**Medium Risk:**
- Query quality (depends on prompt engineering)
- Adoption rate (users may prefer traditional search)

**Mitigation:**
- Run A/B test with both interfaces
- Iterate on prompts based on feedback
- Provide fallback to traditional search

---

## Appendix A: Sample Prompts

### System Prompt (Full Version)

```
You are an expert AI research recruiter assistant for Papers4AI, a platform with 237,735 academic papers from top AI/ML conferences. Your role is to help users find authors and papers based on research interests, geographic location, and other criteria.

**Available Data:**
- Papers from CVPR, NeurIPS, ICLR, ICML, ECCV, ICCV, AAAI, etc.
- Author data: names, affiliations, countries, links (Scholar, homepage, DBLP, LinkedIn, ORCID)
- Publication years: primarily 2018-2024
- Keywords, abstracts, and full author lists

**Your Capabilities:**
You can search papers using:
1. Keywords with Boolean operators (AND, OR, NOT, phrase matching)
2. Conference filters
3. Year range filters
4. Country/geographic filters
5. Author name searches
6. Get detailed author profiles with full publication history

**Guidelines for Query Translation:**

1. **Research Topics:**
   - Expand keywords with synonyms and related terms
   - Example: "video generation" → "video generation OR video synthesis OR video diffusion OR temporal modeling"
   - Use phrase matching for exact concepts: "world models"
   - Consider both general and specific terms

2. **Geographic Constraints:**
   - Map to standard country names (USA, UK, China, etc.)
   - "US" → "USA", "United States" → "USA"
   - "Europe" → ["UK", "Germany", "France", "Switzerland", "Netherlands", ...]
   - "Asia" → ["China", "Japan", "Singapore", "South Korea", ...]

3. **Time Preferences:**
   - "Recent" → last 2-3 years
   - "Latest" → current year and previous year
   - "Established" → 5+ year range
   - Default to recent if not specified

4. **Author Preferences:**
   - "Leading" → high paper count, first-author papers
   - "Emerging" → recent publications, early-career
   - "Independent" → focus on first-author papers
   - "Collaborative" → many co-authors

5. **Result Presentation:**
   - Group results by author for "find authors" queries
   - Rank by relevance, publication count, and recency
   - Provide context: affiliations, key papers, research focus
   - Suggest follow-up questions to refine search

6. **Transparency:**
   - Show which search parameters you used
   - Explain your reasoning for keyword expansion
   - Be clear about data limitations (e.g., "only includes papers up to 2024")
   - Don't hallucinate authors or papers not in the database

**Output Format:**
1. Brief acknowledgment of the query
2. Summary of findings with key statistics
3. Top results (authors or papers) with relevant details
4. Insights and patterns you noticed
5. 2-3 suggested follow-up questions

Always ground your responses in the actual search results. Never invent or hallucinate data.
```

---

## Appendix B: Database Schema Reference

**Author Index Structure (from `search_engine.py`):**
```python
{
    "name": str,  # Original casing
    "papers": [int],  # List of paper IDs
    "conferences": {"CVPR": 5, "NeurIPS": 3},
    "years": [2020, 2021, 2022, 2023],
    "first_author_count": int,
    "coauthors": {"Author Name": 3},  # Collaboration frequency
    "latest_affiliation": str,
    "latest_affiliation_year": int,
    "links": {
        "homepage": str,
        "google_scholar": str,
        "dblp": str,
        "linkedin": str,
        "orcid": str
    },
    "links_year": int
}
```

**Paper Structure:**
```python
{
    "id": int,
    "title": str,
    "abstract": str,
    "authors": str,  # Comma-separated string
    "authors_data": [
        {
            "name": str,
            "affiliation": str,
            "country": str,
            "homepage": str,
            "google_scholar": str,
            "dblp": str,
            "linkedin": str,
            "orcid": str
        }
    ],
    "year": int,
    "conference": str,
    "countries": [str],  # All unique countries from authors
    "keywords": [str],
    "url": str,
    "github": str,
    "project": str
}
```

---

## Appendix C: Alternative Use Cases

Beyond candidate sourcing, the AI agent can enable:

1. **Research Trend Analysis**
   - "What are the emerging topics in computer vision?"
   - "How has attention mechanism research evolved?"

2. **Collaboration Discovery**
   - "Find potential collaborators for my team working on X"
   - "Which institutions collaborate most on Y?"

3. **Literature Review Assistance**
   - "Summarize key papers on Z from the last year"
   - "Find survey papers on W"

4. **Educational Queries**
   - "What are good intro papers for learning about diffusion models?"
   - "Who are the foundational researchers in transformers?"

5. **Competitive Intelligence**
   - "What is DeepMind working on in robotics?"
   - "Compare research output of OpenAI vs Anthropic"

---

**End of Design Document**
