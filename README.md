# 🧩 Riddle App — AI-Powered Riddle Backend

> A production-style FastAPI backend powering an AI-generated riddle game with JWT authentication, multilingual support, and Groq LLM integration.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python) ![FastAPI](https://img.shields.io/badge/FastAPI-0.104-green?logo=fastapi) ![MongoDB](https://img.shields.io/badge/MongoDB-PyMongo-brightgreen?logo=mongodb) ![Groq](https://img.shields.io/badge/Groq-LLM-orange) ![Deployed](https://img.shields.io/badge/Deployed-Leapcell-purple)

## 🚀 Live Demo
- **Backend API**: [riddle-app-vimal26457915.leapcell.dev](https://riddle-app-vimal26457915-0xllqh47.leapcell.dev)
- **Frontend**: See [RIDDLE-FRONTEND](https://github.com/vimal2645/RIDDLE-FRONTEND) repo
- **Android App**: Bundled via Capacitor

## 🎯 What It Does
A full-stack AI riddle game where users:
1. Sign up / log in with JWT auth
2. Get AI-generated riddles via Groq LLM (categorized: logic, wordplay, math, etc.)
3. Submit answers, get feedback, and track scores
4. Switch languages using `deep-translator` (20+ languages supported)
5. Earn/spend coins, view leaderboards

## 🛠️ Tech Stack
| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI 0.104 |
| LLM | Groq API (Llama 3) |
| Database | MongoDB (PyMongo) |
| Auth | JWT (`python-jose`) |
| Translation | `deep-translator` |
| Deployment | Leapcell |
| Mobile | Capacitor (Android) |

## 📁 Project Structure
```
riddle-app/
├── backend/
│   ├── app.py              # Main FastAPI application
│   ├── clear_riddles.py    # DB maintenance script
│   ├── fix_repeating.py    # Riddle dedup logic
│   └── requirements.txt    # Python dependencies
└── frontend/               # React frontend (Capacitor-wrapped)
    └── src/
        ├── components/
        │   ├── Riddle.jsx      # Main game UI
        │   ├── Login.jsx       # Auth screen
        │   ├── Signup.jsx      # Registration
        │   └── Profile.jsx     # User profile
        └── api/axios.js        # API client
```

## ⚙️ Setup & Run

### Backend
```bash
cd backend
pip install -r requirements.txt
# Create .env with:
# MONGO_URI=your_mongodb_uri
# GROQ_API_KEY=your_groq_key
# SECRET_KEY=your_jwt_secret
uvicorn app:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm start
```

## 🔑 Key Features
- ✅ JWT-based authentication (register/login/token refresh)
- ✅ AI riddle generation via Groq (Llama 3)
- ✅ 10+ riddle categories
- ✅ Multilingual (20+ languages via deep-translator)
- ✅ Coin economy & scoring system
- ✅ Leaderboard
- ✅ Android APK via Capacitor
- ✅ Deployed on Leapcell

## 📜 API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | User registration |
| POST | `/auth/login` | JWT login |
| GET | `/riddle/new` | Get AI riddle |
| POST | `/riddle/answer` | Submit answer |
| GET | `/leaderboard` | Top scores |

---
Built with AI-assisted development (Antigravity) · [LinkedIn](https://linkedin.com/in/vimalprakash26)
