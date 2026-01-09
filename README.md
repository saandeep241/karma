# Karma - AI-Powered Task Suggestions

Make every moment count with AI-powered task suggestions for productive moments.

## Architecture

```
karma/
├── backend/          # FastAPI Python backend
│   ├── app/
│   │   ├── agents/   # AI agents (TaskAnalyzer, QuickWin, etc.)
│   │   ├── routes/   # API endpoints
│   │   ├── services/ # Business logic
│   │   ├── config.py # Configuration
│   │   ├── models.py # Pydantic models
│   │   └── main.py   # FastAPI app
│   ├── data/         # Persistent storage
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/         # React + TypeScript frontend
│   ├── src/
│   │   ├── api/      # API client
│   │   ├── components/
│   │   ├── pages/
│   │   └── types/    # TypeScript types
│   ├── Dockerfile
│   └── package.json
│
└── docker-compose.yml
```

## Quick Start

### Development Mode

1. **Start the Backend:**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   
   # Set environment variables
   export OPENAI_KARMA=true  # Enable AI mode
   export OPENAI_API_KEY=your-api-key  # Required for AI mode
   
   # Run the server
   uvicorn app.main:app --reload --port 8000
   ```

2. **Start the Frontend:**
   ```bash
   cd frontend
   nvm use 22  # or your Node.js 18+ version
   npm install
   npm run dev
   ```

3. **Open the app:** http://localhost:5173

### Docker Mode

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=your-api-key
export OPENAI_KARMA=true

# Run both services
docker-compose up --build
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | - |
| `OPENAI_KARMA` | Enable AI mode (`true`/`false`) | `false` |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4o-mini` |

## Features

- **Quick Wins**: Get AI-suggested micro-tasks for small time blocks
- **Task Analysis**: AI analyzes and categorizes your tasks
- **Task Breakdown**: Break complex tasks into actionable subtasks
- **Task Enrichment**: Get AI-researched tips and resources
- **Progress Tracking**: View stats and completion history
- **Dummy Mode**: Works without API key using demo data

## API Endpoints

### Health
- `GET /api/health` - Health check

### Tasks
- `GET /api/tasks/all` - Get all tasks
- `POST /api/tasks/add` - Add a single task
- `POST /api/tasks/import` - Import multiple tasks
- `PUT /api/tasks/{id}/status` - Update task status
- `POST /api/tasks/{id}/breakdown` - Generate subtasks
- `DELETE /api/tasks/all` - Delete all tasks

### Quick Wins
- `GET /api/quickwin/get` - Get a quick win suggestion
- `POST /api/quickwin/complete` - Save completed quick win

### Stats
- `GET /api/tasks/stats` - Get productivity statistics

## Tech Stack

**Backend:**
- FastAPI
- Pydantic
- OpenAI API
- Python 3.11+

**Frontend:**
- React 18
- TypeScript
- Vite
- TailwindCSS
- React Query
- React Router

## License

MIT

