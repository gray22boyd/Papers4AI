# Academic Paper Search Engine

A searchable database of academic papers from major ML/AI conferences, powered by data from [Paper Copilot](https://github.com/papercopilot/paperlists).

## Features

- **Full-text search** across paper titles and abstracts
- **Filter by conference** (CVPR, NeurIPS, ICLR, ICML, etc.)
- **Filter by year range**
- **Relevance-ranked results** with keyword scoring
- **Clean, responsive UI** - no frameworks, pure vanilla JavaScript

## Tech Stack

- **Backend**: Python Flask REST API
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Data**: JSON/CSV from Paper Copilot paperlists

## Project Structure

```
ML4PAPER/
├── backend/
│   ├── app.py              # Flask application
│   ├── search_engine.py    # Search logic
│   └── config.py           # Configuration
├── frontend/
│   └── index.html          # Single-page application
├── scripts/
│   └── aggregate_papers.py # Data collection script
├── data/
│   ├── papers.json         # Aggregated papers
│   └── papers.csv          # CSV export
├── requirements.txt
└── README.md
```

## Quick Start

### 1. Clone this repository
```bash
git clone <your-repo-url>
cd ML4PAPER
```

### 2. Clone Paper Copilot data (in parent directory)
```bash
git clone https://github.com/papercopilot/paperlists.git ../paperlists
```

### 3. Set up Python environment
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
```

### 4. Aggregate paper data
```bash
python scripts/aggregate_papers.py
```

### 5. Run the backend
```bash
python backend/app.py
```

### 6. Open the frontend
Open `frontend/index.html` in your browser, or serve it:
```bash
python -m http.server 8080 --directory frontend
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/search` | POST | Search papers by query and filters |
| `/api/stats` | GET | Get database statistics |
| `/api/conferences` | GET | List all conferences |
| `/api/paper/<id>` | GET | Get single paper details |

## Data Source

Paper data is sourced from [papercopilot/paperlists](https://github.com/papercopilot/paperlists), which contains processed and cleaned metadata from major AI/ML conferences.

## License

MIT License
