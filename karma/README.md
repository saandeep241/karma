# Karma — Smart Task Suggestions

A web application that helps users make productive use of small time blocks by suggesting tasks from their todo lists based on available time, energy level, and emotional state.

## Features

- **Import Todo Lists**: Paste your tasks (one per line) to get started
- **Context-Aware Suggestions**: Tell the app your available time (5-60 min), energy level, and optionally your emotional state
- **AI-Powered Matching**: Uses OpenAI to analyze tasks and match them to your current context
- **Task Breakdown**: Accepted tasks are broken into actionable steps with the first step displayed immediately
- **Alternative Suggestions**: Don't like a suggestion? Request another one
- **Quick Win Tasks**: When no suitable tasks match, get generic productivity suggestions (exercise, hydration, social)

## Quick Start

### 1. Install Dependencies

```bash
cd karma
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file with your OpenAI API key:

```bash
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini  # optional, defaults to gpt-4o-mini
```

**Note**: The app works without an API key using fallback heuristics, but AI-powered features will be limited.

### 3. Run the Application

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload --port 8000
```

### 4. Open in Browser

Navigate to [http://localhost:8000](http://localhost:8000)

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main application UI |
| `/api/session/create` | POST | Create a new session |
| `/api/todo/import` | POST | Import todo list from text |
| `/api/context/set` | POST | Set user context (time, energy, emotion) |
| `/api/suggestion/get` | POST | Get a task suggestion |
| `/api/suggestion/alternative` | POST | Get an alternative suggestion |
| `/api/task/accept` | POST | Accept a task and get breakdown |
| `/api/task/steps/{session_id}` | GET | Get all steps for current task |
| `/api/options` | GET | Get available options for dropdowns |
| `/api/health` | GET | Health check |

## User Flow

1. **Import Tasks**: User pastes their todo list (one task per line)
2. **Set Context**: User selects available time, energy level, and optionally emotional state
3. **Get Suggestion**: System suggests a task matching the user's context
4. **Accept or Skip**: User can accept the suggestion or request another
5. **View Steps**: Accepted tasks are broken into steps, starting with the first step

## Project Structure

```
karma/
├── main.py              # FastAPI application and routes
├── models.py            # Pydantic data models
├── config.py            # Configuration settings
├── ai_service.py        # AI-powered task analysis and matching
├── session_store.py     # In-memory session storage
├── requirements.txt     # Python dependencies
├── templates/
│   └── index.html       # Frontend UI
└── static/              # Static assets
```

## Tech Stack

- **Backend**: FastAPI, Python 3.10+
- **AI**: OpenAI GPT-4o-mini
- **Frontend**: Vanilla JavaScript, CSS3
- **Styling**: Custom CSS with CSS variables, Outfit & JetBrains Mono fonts

## Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `OPENAI_API_KEY` | (none) | OpenAI API key for AI features |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use |

## License

MIT

