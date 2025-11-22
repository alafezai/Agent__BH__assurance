# 🧠AgentBH – GenAI Conversational Agent for BH Assurance

**agentBH** is a secure, on-premise conversational agent powered by **Generative AI (GenAI)**, designed specifically for **BH Assurance**.

It provides:

- ✅ Natural and contextual answers about insurance products (branches, coverage, terms…)
- 🔍 Secure access to client data (contracts, claims, payments…)
- 💬 Instant personalized quote generation via an internal API
- 🔒 Full data privacy: AI runs **100% locally** with no external data sharing
- 📊 Complete traceability and observability (via Langfuse)

---

## 🏗️ Technical Architecture

The system follows a modular microservices-oriented architecture:

```

agentBH/
├── frontend/       # Next.js UI (React, TypeScript, Tailwind)
├── backend/        # FastAPI backend (business logic + APIs)
├── ai-engine/      # Local LLM + RAG engine
├── vector-db/      # Vector database (Chroma / Qdrant)
├── postgres/       # Relational DB (contracts, clients, claims)
├── redis/          # Conversation history / session cache
├── rabbitmq/       # Async tasks (quotes, heavy processing)
└── monitoring/     # Langfuse observability layer

````

---

## 🧰 Tech Stack

### Frontend
- Next.js (React + TypeScript)
- TailwindCSS

### Backend
- FastAPI (Python)
- PostgreSQL
- Redis
- RabbitMQ

### AI Layer
- Local open-source LLM (Mistral, Llama 3…) via **Ollama** or **vLLM**
- RAG using:
  - Sentence Transformers
  - Chroma or Qdrant vector DB

### Security
- JWT authentication
- RBAC access control
- TLS + encrypted data at rest
- Backend-mediated DB access (LLM cannot query DB directly)

### Monitoring
- Langfuse: prompt logging, traces, performance indicators, user feedback

### Deployment
- Docker & Docker Compose  
- Kubernetes-ready architecture (optional)

---

## 🚀 Getting Started

### Prerequisites
- Docker + Docker Compose
- Node.js ≥ 18
- Python ≥ 3.10
- Access to BH Assurance internal APIs
- `.env` file properly configured

### 1. Clone the repository
```bash
git clone https://github.com/your-username/agentBH.git
cd agentBH
````

### 2. Configure environment variables

Create a `.env` file at the project root. Example:

```env
# Backend
DATABASE_URL=postgresql://user:password@postgres:5432/bh_assurance
JWT_SECRET=your_strong_secret_key
API_QUOTE_URL=https://api.bh-assurance.local/quote

# Services
REDIS_URL=redis://redis:6379/0
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/

# Monitoring
LANGFUSE_PUBLIC_KEY=your_public_key
LANGFUSE_SECRET_KEY=your_secret_key
LANGFUSE_HOST=https://cloud.langfuse.com
```

⚠️ Do **NOT** commit `.env` to Git.

### 3. Start the application

```bash
docker-compose up --build
```

This launches:

* Frontend → [http://localhost:3000](http://localhost:3000)
* Backend → [http://localhost:8000](http://localhost:8000)
* PostgreSQL, Redis, RabbitMQ, Vector DB
* Langfuse monitoring tools

### 4. Access the UI

Open: [http://localhost:3000](http://localhost:3000)

---

## 🧪 Testing

**Backend**

```bash
cd backend
pytest
```

**Frontend**

```bash
cd frontend
npm run test
```

---

## 🔐 Security & Compliance

* All client data is accessed only through secure APIs.
* The LLM never accesses the database directly (backend-controlled RBAC).
* RAG is restricted to BH Assurance internal documents only.
* Full audit logs and structured traces (via Langfuse).
* No external AI providers involved → guaranteed data sovereignty.

---

## 📅 Development Methodology

**Method:** Kanban (continuous flow)

**Key Priorities**

* Security & authorization
* Conversation engine
* Quote generation
* User experience

**Iterative Development**

* Backend → AI Engine → Frontend integration
* Continuous testing & rapid user feedback
* Monitoring-driven model tuning (Langfuse)

---

## 📬 Contact

Developed by: Ala Fezai
Project: Digital Transformation Initiative – BH Assurance (2025)

💡 100% on-premise GenAI — no data ever leaves the BH Assurance infrastructure.




## Preview Agent

![Accueil](./docs/Images/1.png)
![Chat Interface](./docs/Images/2.png)
![Dashboard](./docs/Images/3.png)

![Dashboard](./docs/Images/5.png)



