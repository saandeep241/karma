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
- **Token Rate Limiting** - Monthly token limits per user with admin management
- **Token Usage Tracking** - Detailed tracking of OpenAI API usage by user, agent, and model
- **Admin UI** - Manage token limits and usage for all users
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

# Token Rate Limiting (optional)
DEFAULT_MONTHLY_TOKEN_LIMIT=1000000  # Default: 1M tokens/month per user

# Admin Configuration (optional - for admin UI access)
ADMIN_USER_IDS=user_abc123,user_def456  # Comma-separated Clerk user IDs
ADMIN_EMAILS=admin@example.com  # Comma-separated email addresses
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
| `DEFAULT_MONTHLY_TOKEN_LIMIT` | Default monthly token limit per user | `1000000` | No |
| `ADMIN_USER_IDS` | Comma-separated admin user IDs | - | No |
| `ADMIN_EMAILS` | Comma-separated admin emails | - | No |

---

## 🔐 Authentication Setup (Clerk)

1. **Create a Clerk account** at https://clerk.com
2. **Create a new application** in the Clerk dashboard
3. **Get your API keys** from the "API Keys" section
4. **Add keys to `.env` files** (see Configuration above)
5. **Restart both servers**

When configured, users will see a "Sign In" button in the header.

---

## 📊 Token Rate Limiting

Karma includes built-in token usage tracking and monthly rate limiting to control OpenAI API costs.

### Features

- **Monthly Token Limits** - Set per-user monthly token limits (default: 1,000,000 tokens/month)
- **Automatic Tracking** - All OpenAI API calls are automatically tracked
- **Usage Statistics** - View token usage by agent, model, and time period
- **Admin Management** - Admin UI to manage limits and reset usage
- **Automatic Reset** - Monthly usage resets automatically at month boundary

### Configuration

#### Backend Environment Variables

```env
# Token Rate Limiting
DEFAULT_MONTHLY_TOKEN_LIMIT=1000000  # Default monthly limit per user (1M tokens)

# Admin Configuration (for admin UI access)
ADMIN_USER_IDS=user_abc123,user_def456  # Comma-separated Clerk user IDs
ADMIN_EMAILS=admin@example.com,admin2@example.com  # Comma-separated emails
```

### API Endpoints

#### User Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tokens/usage?days=30` | Get token usage statistics for authenticated user |
| GET | `/api/tokens/limit` | Get current monthly limit and usage |
| POST | `/api/tokens/reset` | Reset own monthly token usage |

#### Admin Endpoints (Admin Only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/check` | Check if current user is admin |
| GET | `/api/admin/users/token-limits` | Get all users' token limits and usage |
| POST | `/api/tokens/limit/{user_id}` | Update a user's monthly token limit |
| POST | `/api/tokens/reset/{user_id}` | Reset a user's monthly token usage |

### Usage Example

```bash
# Get your token usage (last 30 days)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-api.com/api/tokens/usage?days=30

# Get your current limit and usage
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://your-api.com/api/tokens/limit

# Admin: Get all users' limits
curl -H "Authorization: Bearer ADMIN_TOKEN" \
  https://your-api.com/api/admin/users/token-limits

# Admin: Update a user's limit
curl -X POST \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"new_limit": 2000000}' \
  https://your-api.com/api/tokens/limit/user_abc123
```

### Admin UI

When configured with admin user IDs or emails, admins will see an "Admin" link in the navigation. The admin UI provides:

- **User Management Table** - View all users' token usage
- **Limit Management** - Edit monthly limits per user
- **Usage Reset** - Reset monthly usage for any user
- **Usage Statistics** - View detailed usage by agent and model

### Rate Limit Behavior

- **Before API Call**: System checks if user has enough tokens remaining
- **If Limit Exceeded**: Returns `429 Too Many Requests` error
- **After Successful Call**: Token usage is automatically recorded
- **Monthly Reset**: Usage counter resets automatically when month changes (YYYY-MM)

### Token Cost Reference

For GPT-4o-mini (default model):
- **Input tokens**: $0.15 per 1M tokens (~6.67M tokens per $1)
- **Output tokens**: $0.60 per 1M tokens (~1.67M tokens per $1)
- **Default limit (1M tokens/month)**: ~$0.15-0.60 per month per user (depending on input/output ratio)

### Setting Up Admins

1. **Get your Clerk User ID**:
   - Log in to your app
   - Check browser console for user ID in API responses
   - Or check Clerk Dashboard → Users

2. **Set Admin Configuration**:
   ```bash
   # In backend/.env
   ADMIN_USER_IDS=user_38EGhipCHzcKBeK3escqcc9Hg9m
   # Or use email
   ADMIN_EMAILS=admin@example.com
   ```

3. **Restart Backend**:
   ```bash
   # The admin check happens on each request, so restart to pick up new config
   ```

4. **Access Admin UI**:
   - Log in as admin user
   - "Admin" link appears in navigation
   - Click to access token management UI

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

### Token Usage (Rate Limiting)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tokens/usage?days=30` | Get token usage statistics |
| GET | `/api/tokens/limit` | Get current monthly limit and usage |
| POST | `/api/tokens/reset` | Reset own monthly usage |
| GET | `/api/admin/check` | Check if user is admin |
| GET | `/api/admin/users/token-limits` | Get all users' limits (admin only) |
| POST | `/api/tokens/limit/{user_id}` | Update user limit (admin only) |
| POST | `/api/tokens/reset/{user_id}` | Reset user usage (admin only) |

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
