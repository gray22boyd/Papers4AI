# AI Agent Implementation Guide
## Step-by-Step Technical Implementation for Papers4AI

**Companion to:** AI_AGENT_DESIGN.md
**Version:** 1.0
**Date:** March 3, 2026

---

## Quick Start (MVP in 1 Day)

This guide will help you implement a minimal viable AI agent for natural language candidate sourcing in approximately 8 hours of development time.

---

## Step 1: Environment Setup (30 minutes)

### 1.1 Install Dependencies

Add to `requirements.txt`:
```
anthropic>=0.18.0
python-dotenv>=1.0.0
redis>=5.0.0  # Optional: for caching
```

Install:
```bash
pip install anthropic python-dotenv
```

### 1.2 Get API Key

1. Go to https://console.anthropic.com/
2. Create an account
3. Generate an API key
4. Copy the key (starts with `sk-ant-`)

### 1.3 Configure Environment

Create `.env` file in project root:
```bash
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
AI_AGENT_ENABLED=true
AI_MAX_TOKENS=4096
AI_MODEL=claude-3-5-sonnet-20241022
```

Update `backend/config.py`:
```python
from dotenv import load_dotenv

load_dotenv()

# AI Agent Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AI_AGENT_ENABLED = os.getenv("AI_AGENT_ENABLED", "false").lower() == "true"
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", 4096))
AI_MODEL = os.getenv("AI_MODEL", "claude-3-5-sonnet-20241022")
```

---

## Step 2: Create AI Agent Module (2 hours)

### 2.1 Create `backend/ai_agent.py`

```python
"""
AI Agent for Natural Language Candidate Sourcing
Uses Claude API with function calling
"""
import anthropic
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class CandidateSourcingAgent:
    """AI agent for natural language paper and author search"""

    # System prompt for the agent
    SYSTEM_PROMPT = """You are an expert AI research recruiter assistant for Papers4AI, a platform with 237,735 academic papers from top AI/ML conferences (CVPR, NeurIPS, ICLR, ICML, ECCV, ICCV, AAAI, etc.).

Your role: Help users find authors and papers based on research interests, geographic location, and other criteria.

**Query Translation Guidelines:**

1. **Research Topics:**
   - Expand keywords with synonyms (e.g., "video generation" → "video generation OR video synthesis OR video diffusion")
   - Use phrase matching for exact concepts (e.g., "world models")
   - Consider both specific and general terms

2. **Geographic Constraints:**
   - Map to standard country names: USA, UK, China, Germany, etc.
   - "US"/"United States" → "USA"
   - "Europe" → ["UK", "Germany", "France", "Switzerland", "Netherlands", ...]

3. **Time Preferences:**
   - "Recent" → last 2-3 years (2022-2024)
   - "Latest" → current and previous year
   - Default to recent work if not specified

4. **Author Finding:**
   - Focus on first-author papers for independent researchers
   - Consider publication count and recency for ranking
   - Note affiliations and geographic location

5. **Result Presentation:**
   - Provide clear summaries with statistics
   - Highlight top researchers with key details
   - Suggest relevant follow-up questions

**IMPORTANT:**
- Only use data from function calls - never hallucinate authors or papers
- Show your search parameters for transparency
- Acknowledge data limitations (papers up to 2024)"""

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """Initialize the AI agent"""
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.tools = self._define_tools()

    def _define_tools(self) -> List[Dict]:
        """Define available tools for the AI agent"""
        return [
            {
                "name": "search_papers",
                "description": "Search academic papers by keywords, filters, and constraints. Returns papers matching the criteria with author details, affiliations, and publication info.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Boolean search query with keywords. Supports AND, OR, NOT operators and \"phrase matching\". Example: 'video generation OR video synthesis'"
                        },
                        "conferences": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Conference names to filter by. Examples: CVPR, NeurIPS, ICLR, ICML, ECCV"
                        },
                        "year_min": {
                            "type": "integer",
                            "description": "Minimum publication year (e.g., 2022)"
                        },
                        "year_max": {
                            "type": "integer",
                            "description": "Maximum publication year (e.g., 2024)"
                        },
                        "countries": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Countries to filter authors by. Examples: USA, UK, China, Germany, France"
                        },
                        "author": {
                            "type": "string",
                            "description": "Author name to search for (partial match works)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results to return (default: 20, max: 50)"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_author_profile",
                "description": "Get detailed profile for a specific author including all their papers, co-authors, affiliations, and publication statistics.",
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
                "description": "Get list of all available conferences in the database with paper counts.",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_available_countries",
                "description": "Get list of all countries with author/paper counts.",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def execute_tool(self, tool_name: str, tool_input: Dict, search_engine) -> Dict:
        """Execute a tool call and return results"""
        try:
            if tool_name == "search_papers":
                return search_engine.search(
                    query=tool_input.get("query", ""),
                    conferences=tool_input.get("conferences"),
                    year_min=tool_input.get("year_min"),
                    year_max=tool_input.get("year_max"),
                    countries=tool_input.get("countries"),
                    author=tool_input.get("author"),
                    limit=min(tool_input.get("limit", 20), 50)
                )
            elif tool_name == "get_author_profile":
                result = search_engine.get_author_profile(tool_input["author_name"])
                return result if result else {"error": "Author not found"}
            elif tool_name == "get_available_conferences":
                return {"conferences": search_engine.get_conferences()}
            elif tool_name == "get_available_countries":
                return {"countries": search_engine.get_countries()}
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"error": str(e)}

    def query(
        self,
        user_message: str,
        search_engine,
        conversation_history: Optional[List[Dict]] = None,
        max_tokens: int = 4096
    ) -> Dict:
        """
        Process natural language query and return results

        Args:
            user_message: User's natural language query
            search_engine: Instance of PaperSearchEngine
            conversation_history: Optional previous conversation messages
            max_tokens: Maximum tokens for response

        Returns:
            {
                "response": "AI-generated response",
                "search_params": {...},  # Search parameters used
                "tool_calls": [...],  # List of tools called
                "conversation_history": [...]  # Updated conversation
            }
        """
        # Initialize or use existing conversation history
        if conversation_history is None:
            conversation_history = []

        # Add user message
        conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Track tool calls and search params
        all_tool_calls = []
        search_params = {}

        try:
            # Initial API call
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=self.SYSTEM_PROMPT,
                tools=self.tools,
                messages=conversation_history
            )

            # Process tool calls in a loop
            while response.stop_reason == "tool_use":
                # Collect tool results
                tool_results = []

                for content_block in response.content:
                    if content_block.type == "tool_use":
                        tool_name = content_block.name
                        tool_input = content_block.input

                        logger.info(f"Executing tool: {tool_name} with input: {tool_input}")

                        # Execute the tool
                        result = self.execute_tool(tool_name, tool_input, search_engine)

                        # Track tool calls
                        all_tool_calls.append({
                            "tool": tool_name,
                            "input": tool_input,
                            "result_summary": {
                                "total": result.get("total", 0) if isinstance(result, dict) else len(result) if isinstance(result, list) else 0
                            }
                        })

                        # Capture search params if this was a search
                        if tool_name == "search_papers":
                            search_params = tool_input

                        # Add tool result
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": json.dumps(result)
                        })

                # Add assistant response and tool results to history
                conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })
                conversation_history.append({
                    "role": "user",
                    "content": tool_results
                })

                # Continue conversation
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=self.SYSTEM_PROMPT,
                    tools=self.tools,
                    messages=conversation_history
                )

            # Extract final text response
            assistant_message = ""
            for content_block in response.content:
                if hasattr(content_block, "text"):
                    assistant_message += content_block.text

            # Add final response to history
            conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            return {
                "response": assistant_message,
                "search_params": search_params,
                "tool_calls": all_tool_calls,
                "conversation_history": conversation_history,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"AI query failed: {e}")
            return {
                "error": str(e),
                "response": "I encountered an error processing your query. Please try rephrasing or contact support.",
                "conversation_history": conversation_history
            }


# Helper function to initialize agent
def create_agent(api_key: str, model: str = "claude-3-5-sonnet-20241022") -> CandidateSourcingAgent:
    """Factory function to create an AI agent instance"""
    return CandidateSourcingAgent(api_key=api_key, model=model)
```

---

## Step 3: Add API Endpoints (1 hour)

### 3.1 Update `backend/app.py`

Add imports at the top:
```python
from ai_agent import create_agent, CandidateSourcingAgent
from config import ANTHROPIC_API_KEY, AI_AGENT_ENABLED, AI_MODEL
```

Add after initialization:
```python
# Initialize AI agent if enabled
ai_agent = None
if AI_AGENT_ENABLED and ANTHROPIC_API_KEY:
    try:
        ai_agent = create_agent(ANTHROPIC_API_KEY, AI_MODEL)
        print(f"✓ AI Agent initialized with model: {AI_MODEL}")
    except Exception as e:
        print(f"✗ Failed to initialize AI agent: {e}")
else:
    print("✗ AI Agent disabled (ANTHROPIC_API_KEY not set)")
```

Add endpoint before `if __name__ == "__main__"`:
```python
@app.route("/api/ai/query", methods=["POST"])
@require_auth
@limiter.limit("20 per hour")
def ai_query():
    """
    Natural language search powered by AI agent

    Request:
        {
            "message": "find me authors with papers in video generation in the US",
            "max_results": 20
        }

    Response:
        {
            "response": "AI-generated response with insights",
            "search_params": {...},
            "tool_calls": [...],
            "timestamp": "2024-03-03T10:30:00"
        }
    """
    if not ai_agent:
        return jsonify({
            "error": "AI agent not enabled. Please configure ANTHROPIC_API_KEY in environment."
        }), 503

    try:
        data = request.get_json() or {}
        message = data.get("message", "").strip()

        if not message:
            return jsonify({"error": "Message is required"}), 400

        # Process query
        result = ai_agent.query(
            user_message=message,
            search_engine=search_engine,
            conversation_history=None,  # TODO: Add session-based history
            max_tokens=4096
        )

        if "error" in result:
            return jsonify(result), 500

        return jsonify(result)

    except Exception as e:
        logger.error(f"AI query endpoint error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/ai/status", methods=["GET"])
def ai_status():
    """Check if AI agent is available"""
    return jsonify({
        "enabled": ai_agent is not None,
        "model": AI_MODEL if ai_agent else None,
        "status": "ready" if ai_agent else "disabled"
    })
```

---

## Step 4: Test Backend (30 minutes)

### 4.1 Start the Server

```bash
# Activate virtual environment
source venv/bin/activate  # Mac/Linux
# .\venv\Scripts\activate  # Windows

# Start Flask app
python backend/app.py
```

### 4.2 Test with cURL

Check AI status:
```bash
curl http://localhost:5000/api/ai/status
```

Test query (replace TOKEN with your auth token):
```bash
curl -X POST http://localhost:5000/api/ai/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "message": "Find authors working on video generation in the USA"
  }'
```

### 4.3 Expected Response

```json
{
  "response": "I found 47 authors working on video generation in the USA with recent publications...",
  "search_params": {
    "query": "video generation OR video synthesis OR video diffusion",
    "countries": ["USA"],
    "year_min": 2022,
    "limit": 20
  },
  "tool_calls": [
    {
      "tool": "search_papers",
      "input": {...},
      "result_summary": {"total": 234}
    }
  ],
  "timestamp": "2024-03-03T10:30:00"
}
```

---

## Step 5: Add Basic Frontend (2 hours)

### 5.1 Add AI Chat UI to `frontend/index.html`

Add after the search section (around line 800):

```html
<!-- AI Search Tab -->
<div id="ai-tab" class="tab-content" style="display: none;">
    <div class="ai-container">
        <div class="ai-header">
            <h2>AI Candidate Sourcing</h2>
            <p class="ai-subtitle">Ask me to find authors and papers using natural language</p>
        </div>

        <div class="ai-examples">
            <strong>Example queries:</strong>
            <div class="example-chips">
                <button class="example-chip" onclick="aiSendExample('Find authors working on video generation in the US')">
                    Find authors in video generation (US)
                </button>
                <button class="example-chip" onclick="aiSendExample('Show me CVPR 2024 papers on world models')">
                    CVPR 2024 world models papers
                </button>
                <button class="example-chip" onclick="aiSendExample('Who are top researchers in diffusion models from DeepMind?')">
                    DeepMind diffusion researchers
                </button>
            </div>
        </div>

        <div class="ai-messages" id="ai-messages">
            <!-- Messages will be inserted here -->
        </div>

        <div class="ai-input-section">
            <textarea
                id="ai-input"
                class="ai-input"
                placeholder="Ask me to find authors or papers... (e.g., 'Find authors working on transformers in Europe')"
                rows="2"
            ></textarea>
            <button id="ai-send-btn" class="ai-send-btn" onclick="aiSendMessage()">
                <span id="ai-send-text">Send</span>
                <span id="ai-loading" style="display: none;">Thinking...</span>
            </button>
        </div>
    </div>
</div>
```

### 5.2 Add CSS (in `<style>` section)

```css
/* AI Search Styles */
.ai-container {
    max-width: 900px;
    margin: 0 auto;
    padding: 2rem;
}

.ai-header {
    text-align: center;
    margin-bottom: 2rem;
}

.ai-subtitle {
    color: var(--text-secondary);
    font-size: 0.95rem;
}

.ai-examples {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 2rem;
}

.example-chips {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-top: 0.75rem;
}

.example-chip {
    background: var(--bg-hover);
    border: 1px solid var(--border);
    color: var(--text-primary);
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s;
}

.example-chip:hover {
    border-color: var(--accent);
    background: var(--accent-glow);
}

.ai-messages {
    min-height: 400px;
    max-height: 600px;
    overflow-y: auto;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}

.ai-message {
    margin-bottom: 1.5rem;
    animation: fadeIn 0.3s;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.ai-message-user {
    text-align: right;
}

.ai-message-assistant {
    text-align: left;
}

.ai-message-content {
    display: inline-block;
    max-width: 80%;
    padding: 1rem 1.25rem;
    border-radius: 12px;
    line-height: 1.6;
}

.ai-message-user .ai-message-content {
    background: var(--accent);
    color: white;
    border-bottom-right-radius: 4px;
}

.ai-message-assistant .ai-message-content {
    background: var(--bg-hover);
    color: var(--text-primary);
    border-bottom-left-radius: 4px;
}

.ai-timestamp {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-top: 0.25rem;
}

.ai-input-section {
    display: flex;
    gap: 1rem;
    align-items: flex-end;
}

.ai-input {
    flex: 1;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1rem;
    color: var(--text-primary);
    font-family: inherit;
    font-size: 0.95rem;
    resize: vertical;
    min-height: 60px;
}

.ai-input:focus {
    outline: none;
    border-color: var(--accent);
}

.ai-send-btn {
    background: var(--accent);
    color: white;
    border: none;
    border-radius: 12px;
    padding: 1rem 2rem;
    font-size: 0.95rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
}

.ai-send-btn:hover {
    background: var(--accent-hover);
    transform: translateY(-1px);
}

.ai-send-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.ai-search-params {
    background: var(--bg-hover);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.75rem;
    margin-top: 0.75rem;
    font-size: 0.85rem;
}

.ai-search-params strong {
    color: var(--accent);
}
```

### 5.3 Add JavaScript (before closing `</script>` tag)

```javascript
// AI Search Functionality
let aiConversationHistory = [];

async function aiSendMessage() {
    const input = document.getElementById('ai-input');
    const message = input.value.trim();

    if (!message) return;

    // Disable input
    const sendBtn = document.getElementById('ai-send-btn');
    sendBtn.disabled = true;
    document.getElementById('ai-send-text').style.display = 'none';
    document.getElementById('ai-loading').style.display = 'inline';

    // Clear input
    input.value = '';

    // Display user message
    aiDisplayMessage('user', message);

    try {
        const response = await fetch(`${API_BASE}/api/ai/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: JSON.stringify({
                message: message
            })
        });

        const data = await response.json();

        if (data.error) {
            aiDisplayMessage('assistant', `Error: ${data.error}`, true);
        } else {
            // Display assistant response
            aiDisplayMessage('assistant', data.response, false, data.search_params);
        }

    } catch (error) {
        console.error('AI query failed:', error);
        aiDisplayMessage('assistant', 'Sorry, I encountered an error. Please try again.', true);
    } finally {
        // Re-enable input
        sendBtn.disabled = false;
        document.getElementById('ai-send-text').style.display = 'inline';
        document.getElementById('ai-loading').style.display = 'none';
    }
}

function aiDisplayMessage(role, content, isError = false, searchParams = null) {
    const messagesDiv = document.getElementById('ai-messages');

    const messageEl = document.createElement('div');
    messageEl.className = `ai-message ai-message-${role}`;

    let messageHTML = `
        <div class="ai-message-content ${isError ? 'error' : ''}">
            ${escapeHtml(content).replace(/\n/g, '<br>')}
        </div>
        <div class="ai-timestamp">${new Date().toLocaleTimeString()}</div>
    `;

    // Add search params if available
    if (searchParams && Object.keys(searchParams).length > 0) {
        messageHTML += `
            <div class="ai-search-params">
                <strong>Search parameters used:</strong>
                ${JSON.stringify(searchParams, null, 2)}
            </div>
        `;
    }

    messageEl.innerHTML = messageHTML;
    messagesDiv.appendChild(messageEl);

    // Scroll to bottom
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function aiSendExample(exampleText) {
    document.getElementById('ai-input').value = exampleText;
    aiSendMessage();
}

function getAuthToken() {
    // Get token from localStorage or sessionStorage
    return localStorage.getItem('authToken') || '';
}

// Enter key to send
document.getElementById('ai-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        aiSendMessage();
    }
});
```

### 5.4 Add Tab Navigation

Add a tab button in the header section (around line 100):

```html
<div class="tab-navigation">
    <button class="tab-btn active" onclick="switchTab('search')">Search</button>
    <button class="tab-btn" onclick="switchTab('ai')">AI Assistant</button>
</div>
```

Add tab switching function:

```javascript
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.style.display = 'none';
    });

    // Remove active class from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    const selectedTab = document.getElementById(`${tabName}-tab`);
    if (selectedTab) {
        selectedTab.style.display = 'block';
    }

    // Mark button as active
    event.target.classList.add('active');
}
```

---

## Step 6: Testing & Validation (1 hour)

### 6.1 Test Queries

Try these queries in your UI:

1. **Basic author search:**
   ```
   Find authors working on video generation in the USA
   ```

2. **Conference + topic:**
   ```
   Show me CVPR 2024 papers on diffusion models
   ```

3. **Geographic + topic:**
   ```
   Who are the top researchers in transformers from Europe?
   ```

4. **Specific institution:**
   ```
   What is DeepMind working on in robotics?
   ```

5. **Comparative:**
   ```
   Compare research output of Stanford and MIT in computer vision
   ```

### 6.2 Validation Checklist

- [ ] AI status endpoint returns "enabled: true"
- [ ] Query endpoint requires authentication
- [ ] User message appears in chat
- [ ] AI response appears within 5 seconds
- [ ] Search parameters are shown
- [ ] Error handling works (try with invalid token)
- [ ] Rate limiting works (try 21+ queries)
- [ ] Mobile responsive

---

## Step 7: Monitor & Optimize (Ongoing)

### 7.1 Add Usage Tracking

Create `backend/ai_usage_tracker.py`:

```python
"""Track AI agent usage and costs"""
import json
from datetime import datetime
from pathlib import Path

USAGE_LOG = Path(__file__).parent.parent / "data" / "ai_usage.jsonl"

def log_usage(user_id: str, query: str, response_data: dict):
    """Log AI query for analytics"""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "query": query,
        "tool_calls": len(response_data.get("tool_calls", [])),
        "response_length": len(response_data.get("response", "")),
        # Estimate cost (rough approximation)
        "estimated_cost_usd": estimate_cost(response_data)
    }

    with open(USAGE_LOG, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

def estimate_cost(response_data: dict) -> float:
    """Estimate API cost for this query"""
    # Claude 3.5 Sonnet: $3 per 1M input tokens, $15 per 1M output tokens
    # Rough estimate: 500 input + 800 output tokens per query
    input_tokens = 500
    output_tokens = len(response_data.get("response", "")) * 0.75  # ~0.75 tokens per char
    cost = (input_tokens / 1_000_000 * 3) + (output_tokens / 1_000_000 * 15)
    return round(cost, 6)
```

Add to `app.py` in the `ai_query()` endpoint:

```python
from ai_usage_tracker import log_usage

# After successful query
log_usage(
    user_id=request.current_user.get("id"),
    query=message,
    response_data=result
)
```

### 7.2 Create Analytics Dashboard

Create `scripts/analyze_ai_usage.py`:

```python
"""Analyze AI usage patterns and costs"""
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

USAGE_LOG = Path(__file__).parent.parent / "data" / "ai_usage.jsonl"

def analyze_usage():
    """Generate usage report"""
    if not USAGE_LOG.exists():
        print("No usage data found")
        return

    total_queries = 0
    total_cost = 0.0
    queries_by_user = defaultdict(int)
    queries_by_hour = defaultdict(int)

    with open(USAGE_LOG) as f:
        for line in f:
            entry = json.loads(line)
            total_queries += 1
            total_cost += entry.get("estimated_cost_usd", 0)
            queries_by_user[entry["user_id"]] += 1

            # Extract hour for usage pattern
            timestamp = datetime.fromisoformat(entry["timestamp"])
            hour = timestamp.hour
            queries_by_hour[hour] += 1

    print("\n=== AI Usage Report ===")
    print(f"Total Queries: {total_queries}")
    print(f"Total Cost: ${total_cost:.2f}")
    print(f"Avg Cost per Query: ${total_cost/total_queries:.4f}" if total_queries > 0 else "N/A")
    print(f"\nTop Users:")
    for user_id, count in sorted(queries_by_user.items(), key=lambda x: -x[1])[:5]:
        print(f"  {user_id}: {count} queries")

    print(f"\nPeak Usage Hours:")
    for hour, count in sorted(queries_by_hour.items(), key=lambda x: -x[1])[:5]:
        print(f"  {hour:02d}:00 - {count} queries")

if __name__ == "__main__":
    analyze_usage()
```

Run with:
```bash
python scripts/analyze_ai_usage.py
```

---

## Step 8: Production Deployment

### 8.1 Environment Variables

Set on your hosting platform (Railway, Heroku, etc.):

```bash
ANTHROPIC_API_KEY=sk-ant-api03-xxxxx
AI_AGENT_ENABLED=true
AI_MODEL=claude-3-5-sonnet-20241022
AI_MAX_TOKENS=4096
```

### 8.2 Rate Limiting

Update `app.py` rate limits for production:

```python
@app.route("/api/ai/query", methods=["POST"])
@require_auth
@limiter.limit("10 per hour")  # Tighter limit for production
def ai_query():
    # ... existing code
```

### 8.3 Monitoring

Add error tracking (Sentry):

```python
import sentry_sdk

if os.getenv("SENTRY_DSN"):
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        traces_sample_rate=0.1
    )
```

---

## Troubleshooting

### Issue: "AI agent not enabled"

**Solution:**
1. Check `.env` file has `ANTHROPIC_API_KEY`
2. Verify API key starts with `sk-ant-`
3. Check console logs on server startup
4. Try: `curl http://localhost:5000/api/ai/status`

### Issue: "Unauthorized" error

**Solution:**
1. You need to be logged in
2. Get auth token from login response
3. Include in header: `Authorization: Bearer <token>`

### Issue: Slow responses (>10 seconds)

**Possible causes:**
1. Large result sets (>100 papers)
2. Multiple tool calls
3. Network latency

**Solutions:**
- Reduce `limit` parameter
- Add streaming support
- Implement caching

### Issue: High API costs

**Solutions:**
1. Enable prompt caching in Claude API
2. Add query result caching (Redis)
3. Reduce max_tokens
4. Optimize system prompt length

---

## Next Steps

### Immediate Enhancements (Week 2)

1. **Conversation History**
   - Store conversation in session/database
   - Allow follow-up questions
   - "Refine this search" button

2. **Result Export**
   - Export candidates to CSV
   - Include AI insights in export
   - Email results

3. **Better UI**
   - Markdown rendering in responses
   - Syntax highlighting for code
   - Collapsible search params

### Advanced Features (Month 2)

1. **Query Templates**
   - Save common queries
   - Share templates with team
   - Parametrized templates

2. **Batch Processing**
   - Upload list of topics
   - Bulk author extraction
   - Scheduled reports

3. **Learning & Improvement**
   - Track which results users click
   - A/B test different prompts
   - Fine-tune ranking based on feedback

---

## Cost Optimization Tips

### 1. Implement Caching

```python
import redis
import hashlib

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_cached_query(query: str) -> Optional[dict]:
    """Check if query result is cached"""
    cache_key = hashlib.md5(query.encode()).hexdigest()
    cached = redis_client.get(f"ai_query:{cache_key}")
    if cached:
        return json.loads(cached)
    return None

def cache_query(query: str, result: dict, ttl: int = 3600):
    """Cache query result for 1 hour"""
    cache_key = hashlib.md5(query.encode()).hexdigest()
    redis_client.setex(
        f"ai_query:{cache_key}",
        ttl,
        json.dumps(result)
    )
```

### 2. Use Prompt Caching (Claude)

```python
# Add caching to system prompt
response = self.client.messages.create(
    model=self.model,
    max_tokens=max_tokens,
    system=[{
        "type": "text",
        "text": self.SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"}  # Cache system prompt
    }],
    tools=self.tools,
    messages=conversation_history
)
```

This reduces costs by 90% for repeated system prompts!

### 3. Tiered Access

```python
# Free tier: 10 queries/month
# Pro tier: 100 queries/month
# Enterprise: unlimited

def check_query_quota(user_id: str) -> bool:
    """Check if user has remaining queries"""
    user = get_user(user_id)
    tier = user.get("tier", "free")

    if tier == "enterprise":
        return True

    monthly_queries = count_monthly_queries(user_id)

    limits = {"free": 10, "pro": 100}
    return monthly_queries < limits.get(tier, 0)
```

---

## Summary

You now have a fully functional AI agent for candidate sourcing!

**What you built:**
- Natural language query processing
- Function-calling AI agent with Claude
- Search parameter extraction
- Chat-based UI
- Usage tracking and cost monitoring

**Total development time:** ~8 hours
**Monthly cost:** $50-200 (depending on usage)
**User experience:** Ask questions in plain English, get expert-level search results

**Next steps:**
1. Test with real users
2. Gather feedback
3. Iterate on prompts
4. Add advanced features

Good luck!
