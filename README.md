# Karma - AI-Powered Task Suggestions

Make every moment count with AI-powered task suggestions for productive moments.

![Karma App](https://img.shields.io/badge/version-5.0.0-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## 🌟 Features

- **Quick Wins** - AI-suggested micro-tasks for small time blocks (5-60 min)
- **Smart Task Analysis** - AI categorizes tasks by priority, energy, and time
- **Task Breakdown** - Break complex tasks into actionable subtasks with time estimates
- **Task Enrichment** - Get AI-researched tips, steps, and resources
- **Progress Tracking** - View stats and completion history
- **User Context** - Considers your available time and energy level
- **Clerk Authentication** - Secure user authentication (optional)
- **SQLite Database** - Persistent task storage
- **Dummy Mode** - Works without API keys using demo data

---

## 📁 Project Structure

```
karma/
├── backend/                 # FastAPI Python backend
│   ├── app/
│   │   ├── agents/          # AI agents
│   │   │   ├── base_agent.py
│   │   │   ├── task_analyzer.py
│   │   │   ├── task_suggester.py
│   │   │   ├── task_enricher.py
│   │   │   ├── quickwin_agent.py
│   │   │   ├── breakdown_agent.py
│   │   │   └── orchestrator.py
│   │   ├── database/        # SQLite + SQLAlchemy
│   │   │   ├── models.py
│   │   │   ├── connection.py
│   │   │   └── repository.py
│   │   ├── routes/          # API endpoints
│   │   │   ├── tasks.py
│   │   │   ├── suggestions.py
│   │   │   └── sessions.py
│   │   ├── services/        # Business logic
│   │   ├── auth.py          # Clerk authentication
│   │   ├── config.py        # Configuration
│   │   ├── models.py        # Pydantic models
│   │   └── main.py          # FastAPI app
│   ├── data/                # SQLite database
│   ├── venv/                # Python virtual environment
│   └── requirements.txt
│
├── frontend/                # React + TypeScript frontend
│   ├── src/
│   │   ├── api/             # API client
│   │   ├── components/      # React components
│   │   ├── pages/           # Page components
│   │   └── types/           # TypeScript types
│   ├── package.json
│   └── vite.config.ts
│
├── docker-compose.yml
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** (recommend using `nvm`)
- **OpenAI API Key** (optional - for AI features)
- **Clerk Account** (optional - for authentication)

### 1. Clone the Repository

```bash
git clone https://github.com/saandeep241/karma.git
cd karma
```

### 2. Start the Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python -m uvicorn app.main:app --reload --port 8000
```

The backend will be available at: **http://localhost:8000**

### 3. Start the Frontend

```bash
cd frontend

# Use Node.js 18+ (if using nvm)
nvm use 22

# Install dependencies
npm install

# Run the dev server
npm run dev
```

The frontend will be available at: **http://localhost:5173**

---

## ⚙️ Configuration

### Environment Variables

Create `.env` files to configure the app:

#### Backend (`backend/.env`)

```env
# AI Configuration (optional)
OPENAI_API_KEY=sk-your-openai-api-key
OPENAI_KARMA=true          # Set to "true" to enable AI, "false" for dummy mode
OPENAI_MODEL=gpt-4o-mini   # OpenAI model to use

# Authentication (optional)
CLERK_SECRET_KEY=sk_test_your-clerk-secret-key
CLERK_PUBLISHABLE_KEY=pk_test_your-clerk-publishable-key
```

#### Frontend (`frontend/.env`)

```env
# Authentication (optional)
VITE_CLERK_PUBLISHABLE_KEY=pk_test_your-clerk-publishable-key
```

### Configuration Options

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `OPENAI_API_KEY` | Your OpenAI API key | - | No (dummy mode works without) |
| `OPENAI_KARMA` | Enable AI mode | `false` | No |
| `OPENAI_MODEL` | OpenAI model | `gpt-4o-mini` | No |
| `CLERK_SECRET_KEY` | Clerk secret key | - | No (auth disabled without) |
| `CLERK_PUBLISHABLE_KEY` | Clerk publishable key | - | No |
| `VITE_CLERK_PUBLISHABLE_KEY` | Clerk key for frontend | - | No |

---

## 🔐 Authentication Setup (Clerk)

1. **Create a Clerk account** at https://clerk.com
2. **Create a new application** in the Clerk dashboard
3. **Get your API keys** from the "API Keys" section
4. **Add keys to `.env` files** (see Configuration above)
5. **Restart both servers**

When configured, users will see a "Sign In" button in the header.

---

## 🐳 Docker Mode

```bash
# Build and run both services
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

Services:
- Frontend: http://localhost:5173
- Backend: http://localhost:8000

---

## 📡 API Endpoints

### Health & Info
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API info |
| GET | `/api/health` | Health check with status |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks/all` | Get all tasks |
| POST | `/api/task/add` | Add a single task |
| POST | `/api/tasks/add` | Add a single task (alias) |
| POST | `/api/todo/import` | Import multiple tasks |
| GET | `/api/tasks/{id}` | Get task by ID |
| PUT | `/api/tasks/{id}/status` | Update task status |
| POST | `/api/tasks/{id}/breakdown` | Generate subtasks |
| POST | `/api/tasks/{id}/reresearch` | Re-research task |
| DELETE | `/api/tasks/all` | Delete all tasks |

### Quick Wins
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/quickwin/get` | Get a quick win suggestion |
| POST | `/api/quickwin` | Generate quick win |
| POST | `/api/quickwin/complete` | Save quick win as task |

### Stats
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks/stats` | Get productivity statistics |

---

## 🤖 AI Agents

Karma uses a multi-agent architecture:

| Agent | Purpose |
|-------|---------|
| **TaskAnalyzer** | Analyzes task properties (priority, category, time, energy) |
| **TaskSuggester** | Matches tasks to user context |
| **TaskEnricher** | Adds research, tips, and resources |
| **QuickWin** | Generates micro-tasks for quick productivity |
| **Breakdown** | Creates step-by-step plans with time estimates |
| **Orchestrator** | Coordinates all agents |

---

## 🛠 Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Database ORM
- **SQLite** - Lightweight database
- **Pydantic** - Data validation
- **OpenAI API** - AI capabilities
- **Clerk** - Authentication

### Frontend
- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Fast build tool
- **TailwindCSS** - Styling
- **React Query** - Server state management
- **React Router** - Navigation
- **Clerk React** - Authentication UI

---

## 🧪 Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Linting

```bash
# Backend
cd backend
mypy app/

# Frontend
cd frontend
npm run lint
```

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

Made with ❤️ by [Saandeep](https://github.com/saandeep241)
