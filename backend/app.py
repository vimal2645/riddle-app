from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import jwt, JWTError
from datetime import datetime, timedelta
from pymongo import MongoClient
from bson import ObjectId
from deep_translator import GoogleTranslator
from groq import Groq
from dotenv import load_dotenv
import hashlib
import json
import re
import os
import random
from typing import Optional, List

# Load environment variables
load_dotenv()

# ==================== CONFIG ====================
MONGO_URL = os.getenv("MONGO_URL")
if not MONGO_URL:
    raise ValueError("❌ MONGO_URL environment variable not set!")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("❌ SECRET_KEY environment variable not set!")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("❌ GROQ_API_KEY environment variable not set!")

DATABASE_NAME = os.getenv("DATABASE_NAME", "riddleapp")

groq_client = Groq(api_key=GROQ_API_KEY)

# ==================== ACHIEVEMENT RANKS ====================
ACHIEVEMENT_RANKS = [
    {"points": 0, "rank": "🥉 Beginner", "title": "Riddle Newbie", "icon": "🥉"},
    {"points": 500, "rank": "🥈 Bronze Master", "title": "Bronze Solver", "icon": "🥈"},
    {"points": 1000, "rank": "🥇 Silver Expert", "title": "Silver Genius", "icon": "🥇"},
    {"points": 1500, "rank": "💎 Gold Champion", "title": "Gold Mastermind", "icon": "💎"},
    {"points": 2000, "rank": "👑 Platinum Legend", "title": "Platinum Wizard", "icon": "👑"},
]

def get_user_rank(points):
    """Get user's rank based on points"""
    rank_info = ACHIEVEMENT_RANKS[0]
    
    for achievement in ACHIEVEMENT_RANKS:
        if points >= achievement["points"]:
            rank_info = achievement
        else:
            break
    
    return rank_info

# ==================== DATABASE WITH CONNECTION POOLING ====================
try:
    client = MongoClient(
        MONGO_URL,
        maxPoolSize=50,
        minPoolSize=10,
        maxIdleTimeMS=30000,
        serverSelectionTimeoutMS=5000,
        retryWrites=True
    )
    # Test connection
    client.admin.command('ping')
    db = client[DATABASE_NAME]
    print("✅ MongoDB Atlas connected successfully")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    exit(1)

# ==================== AUTH SETUP ====================
security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain: str, hashed: str) -> bool:
    return hashlib.sha256(plain.encode()).hexdigest() == hashed

def create_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=30)
    return jwt.encode({"sub": user_id, "exp": expire}, SECRET_KEY, algorithm="HS256")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        user = db.users.find_one({"_id": user_id})
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return user
        
    except JWTError as e:
        print(f"❌ JWT Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# ==================== AI RIDDLE GENERATION WITH DIVERSITY ====================

RIDDLE_CATEGORIES = ["logic", "wordplay", "math", "nature", "objects", "general"]

# Common riddle answers to AVOID (prevent repetition)
COMMON_ANSWERS = [
    "clock", "shadow", "mirror", "time", "echo", "silence", "breath", "darkness",
    "light", "fire", "candle", "river", "cloud", "egg", "towel", "keyboard",
    "stamp", "bottle", "pencil", "coin"
]

# Diverse prompts for better variety
RIDDLE_PROMPTS = [
    "Create a tricky riddle about everyday objects that people use.",
    "Make a clever wordplay riddle with a surprising answer.",
    "Generate a logic riddle that requires thinking outside the box.",
    "Create a nature-themed riddle with a creative twist.",
    "Make a riddle about something found in a house, but unusual.",
    "Generate a riddle with a one-word answer that's NOT commonly used.",
    "Create a riddle about abstract concepts like emotions or ideas.",
    "Make a math-based riddle with a clever logical answer."
]

def create_riddle_hash(question: str, answer: str) -> str:
    """Create a unique hash for a riddle to detect duplicates"""
    combined = f"{question.lower().strip()}{answer.lower().strip()}"
    return hashlib.md5(combined.encode()).hexdigest()

def check_riddle_exists(answer: str, question: str = None) -> bool:
    """Check if riddle with same answer or question already exists"""
    # Check by answer
    existing = db.riddles.find_one({
        "answer": answer.lower().strip(),
        "language": "en"
    })
    
    if existing:
        return True
    
    # Check by question hash if provided
    if question:
        riddle_hash = create_riddle_hash(question, answer)
        existing = db.riddles.find_one({
            "riddle_hash": riddle_hash
        })
        if existing:
            return True
    
    return False

def generate_fresh_ai_riddle(category: str = "general", max_retries: int = 5):
    """Generate unique riddle using Groq with better diversity"""
    
    for attempt in range(max_retries):
        try:
            # Use random prompt for variety
            random_prompt = random.choice(RIDDLE_PROMPTS)
            category_prompt = f" Category: {category}." if category != "general" else ""
            
            # Get list of existing answers to avoid
            existing_answers = list(db.riddles.find(
                {"language": "en"},
                {"answer": 1}
            ).limit(100))
            
            existing_answers_list = [r["answer"] for r in existing_answers if "answer" in r]
            all_avoid = list(set(COMMON_ANSWERS + existing_answers_list))
            avoid_text = ", ".join(all_avoid[:20]) if all_avoid else "clock, shadow, mirror"
            
            response = groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{
                    "role": "user",
                    "content": f"""{random_prompt}

Generate ONE unique riddle in JSON format:
{{"question": "creative riddle", "answer": "one word", "difficulty": "easy"}}

{category_prompt}

IMPORTANT RULES:
- Answer must be ONE WORD only (lowercase)
- Answer MUST NOT be any of these: {avoid_text}
- Question must be creative and UNIQUE
- Use uncommon words as answers
- Think of unusual objects, concepts, or things
- Avoid cliché riddles

Examples of GOOD answers: umbrella, bridge, library, compass, recipe, alphabet, photograph
Examples of BAD answers: clock, shadow, time, mirror, echo

Only output JSON, nothing else."""
                }],
                temperature=1.8,
                max_tokens=250,
                top_p=0.95
            )
            
            text = response.choices[0].message.content.strip()
            text = text.replace('``````', '').strip()
            
            json_match = re.search(r'\{[^{}]*"question"[^{}]*"answer"[^{}]*\}', text, re.DOTALL)
            
            if json_match:
                riddle_data = json.loads(json_match.group())
                
                answer = riddle_data["answer"].lower().strip()
                question = riddle_data["question"].strip()
                
                # Validate answer is one word
                if len(answer.split()) > 1:
                    print(f"⚠️ Attempt {attempt + 1}: Answer is multiple words: {answer}")
                    continue
                
                # Check if answer is in avoid list
                if answer in COMMON_ANSWERS:
                    print(f"⚠️ Attempt {attempt + 1}: Common answer detected: {answer}")
                    continue
                
                # Check if riddle already exists
                if check_riddle_exists(answer, question):
                    print(f"⚠️ Attempt {attempt + 1}: Duplicate riddle detected: {answer}")
                    continue
                
                # SUCCESS - Create new unique riddle
                new_id = str(ObjectId())
                riddle_hash = create_riddle_hash(question, answer)
                
                riddle = {
                    "_id": new_id,
                    "question": question,
                    "answer": answer,
                    "riddle_hash": riddle_hash,
                    "category": category,
                    "difficulty": riddle_data.get("difficulty", "medium"),
                    "language": "en",
                    "hints": [],
                    "source": "groq",
                    "created_at": datetime.utcnow(),
                    "shares": 0,
                    "likes": 0
                }
                
                db.riddles.insert_one(riddle)
                print(f"✨ Generated UNIQUE riddle #{attempt + 1}: {answer} - {question[:50]}...")
                return riddle
                
        except Exception as e:
            print(f"❌ AI Error attempt {attempt + 1}: {e}")
            continue
    
    print(f"❌ Failed to generate unique riddle after {max_retries} attempts")
    return None

def translate_to_hindi(text: str) -> str:
    try:
        translator = GoogleTranslator(source='en', target='hi')
        return translator.translate(text)
    except:
        return text

def get_daily_challenge_riddle():
    """Get or create today's daily challenge"""
    today = datetime.utcnow().date()
    
    challenge = db.daily_challenges.find_one({
        "date": today.isoformat()
    })
    
    if challenge:
        return challenge
    
    riddle = generate_fresh_ai_riddle("logic")
    
    if riddle:
        challenge = {
            "_id": str(ObjectId()),
            "date": today.isoformat(),
            "riddle_id": riddle["_id"],
            "riddle": riddle,
            "participants": [],
            "created_at": datetime.utcnow()
        }
        db.daily_challenges.insert_one(challenge)
        return challenge
    
    return None

# ==================== MODELS ====================

class SignupRequest(BaseModel):
    username: str
    email: str
    password: str
    language: str = "en"

class LoginRequest(BaseModel):
    email: str
    password: str

class AnswerRequest(BaseModel):
    riddle_id: str
    answer: str

class DailyChallengeAnswer(BaseModel):
    answer: str

class ShareRiddleRequest(BaseModel):
    riddle_id: str

class MultiplayerRoomCreate(BaseModel):
    room_name: str
    max_players: int = 5

class MultiplayerJoin(BaseModel):
    room_id: str

# ==================== FASTAPI APP ====================

app = FastAPI(title="AI Riddle App", version="5.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== AUTH ROUTES ====================

@app.post("/signup")
def signup(data: SignupRequest):
    try:
        if db.users.find_one({"email": data.email}):
            print(f"⚠️ Signup failed: Email {data.email} already exists")
            raise HTTPException(status_code=400, detail="Email already exists")
        
        user_id = str(ObjectId())
        
        user_data = {
            "_id": user_id,
            "username": data.username,
            "email": data.email,
            "password": hash_password(data.password),
            "language": data.language,
            "solved": 0,
            "correct": 0,
            "streak": 0,
            "points": 0,
            "seen_riddles": [],
            "current_riddle_attempts": {},
            "daily_challenges_completed": [],
            "last_active": None,
            "created_at": datetime.utcnow()
        }
        
        db.users.insert_one(user_data)
        
        token = create_token(user_id)
        
        print(f"✅ Signup successful: {data.username} ({data.email})")
        
        return {
            "token": token,
            "user_id": user_id,
            "username": data.username,
            "message": "Account created successfully!"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Signup error: {e}")
        raise HTTPException(status_code=500, detail="Signup failed")

@app.post("/login")
def login(data: LoginRequest):
    try:
        user = db.users.find_one({"email": data.email})
        
        if not user:
            print(f"❌ Login failed: User {data.email} not found")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if not verify_password(data.password, user["password"]):
            print(f"❌ Login failed: Wrong password for {data.email}")
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        token = create_token(user["_id"])
        
        print(f"✅ Login successful: {user['username']} ({data.email})")
        
        return {
            "token": token,
            "user_id": user["_id"],
            "username": user["username"],
            "message": "Login successful!"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

# ==================== RIDDLE ROUTES (FIXED - NO REPEATS) ====================

@app.get("/riddle")
def get_random_riddle(
    language: str = "en", 
    category: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    """Get riddle with optional category filter - NO REPEATS"""
    
    user_id = user["_id"]
    
    # Get seen riddles and ensure they're all strings
    seen_riddles_raw = user.get("seen_riddles", [])
    seen_riddles = list(set([str(rid) for rid in seen_riddles_raw if rid]))
    
    print(f"\n{'='*60}")
    print(f"👤 USER: {user['username']}")
    print(f"📊 SEEN: {len(seen_riddles)} riddles")
    if category:
        print(f"🏷️  CATEGORY: {category}")
    print(f"{'='*60}")
    
    # Build query - CRITICAL: Exclude seen riddles
    query = {
        "language": language,
        "_id": {"$nin": seen_riddles}
    }
    
    if category and category in RIDDLE_CATEGORIES:
        query["category"] = category
    
    # Get unseen riddles
    unseen_riddles = list(db.riddles.find(query))
    
    print(f"✅ UNSEEN riddles available: {len(unseen_riddles)}")
    
    # If we have enough unseen riddles, use them
    if len(unseen_riddles) >= 3:
        riddle = random.choice(unseen_riddles)
        print(f"📖 Selected UNSEEN cached riddle: {riddle.get('answer', 'unknown')}")
    else:
        # Generate new riddle
        print(f"🤖 Generating NEW unique riddle...")
        en_riddle = generate_fresh_ai_riddle(category or "general")
        
        if not en_riddle:
            # If AI fails completely, use any available riddle
            print(f"⚠️ AI generation failed. Using available riddles...")
            
            if unseen_riddles:
                riddle = random.choice(unseen_riddles)
            else:
                # Last resort: get any riddle
                all_riddles = list(db.riddles.find({"language": language}))
                if all_riddles:
                    riddle = random.choice(all_riddles)
                    # Reset seen riddles for this user
                    db.users.update_one(
                        {"_id": user_id},
                        {"$set": {"seen_riddles": []}}
                    )
                    seen_riddles = []
                else:
                    raise HTTPException(status_code=503, detail="No riddles available. Try again in a moment.")
        else:
            if language == "hi":
                hindi_riddle = {
                    "_id": str(ObjectId()),
                    "question": translate_to_hindi(en_riddle["question"]),
                    "answer": translate_to_hindi(en_riddle["answer"]),
                    "riddle_hash": create_riddle_hash(
                        translate_to_hindi(en_riddle["question"]),
                        translate_to_hindi(en_riddle["answer"])
                    ),
                    "category": en_riddle["category"],
                    "difficulty": en_riddle["difficulty"],
                    "language": "hi",
                    "hints": [],
                    "source": "groq_translated",
                    "created_at": datetime.utcnow()
                }
                db.riddles.insert_one(hindi_riddle)
                riddle = hindi_riddle
            else:
                riddle = en_riddle
    
    riddle_id = str(riddle["_id"])
    
    # Mark as seen with proper string ID
    db.users.update_one(
        {"_id": user_id},
        {
            "$addToSet": {"seen_riddles": riddle_id},
            "$set": {f"current_riddle_attempts.{riddle_id}": 0}
        }
    )
    
    print(f"✅ DELIVERED: {riddle['question'][:50]}...")
    print(f"🆔 Answer: {riddle.get('answer', 'unknown')}")
    print(f"{'='*60}\n")
    
    return {
        "id": riddle_id,
        "question": riddle["question"],
        "category": riddle.get("category", "general"),
        "difficulty": riddle.get("difficulty", "medium"),
        "hints": riddle.get("hints", []),
        "shares": riddle.get("shares", 0),
        "attempts_left": 2
    }

@app.post("/check")
def check_answer(data: AnswerRequest, user: dict = Depends(get_current_user)):
    """Check answer - 2 attempts, then -5 points and BLOCK further attempts"""
    
    riddle = db.riddles.find_one({"_id": data.riddle_id})
    
    if not riddle:
        raise HTTPException(status_code=404, detail="Riddle not found")
    
    user_id = user["_id"]
    
    # Get current attempts
    attempts_data = user.get("current_riddle_attempts", {})
    current_attempts = attempts_data.get(data.riddle_id, 0)
    
    # CRITICAL: If already failed 2 times, BLOCK
    if current_attempts >= 2:
        raise HTTPException(
            status_code=400, 
            detail=f"Max attempts reached! Answer was: {riddle['answer']}"
        )
    
    user_answer = data.answer.strip().lower()
    correct_answer = riddle["answer"].strip().lower()
    
    print(f"\n🔍 CHECKING: '{user_answer}' vs '{correct_answer}'")
    print(f"   Attempt: {current_attempts + 1}/2")
    
    correct = (user_answer == correct_answer)
    
    if not correct and correct_answer in user_answer:
        word_count = len(user_answer.split())
        if word_count <= 5:
            correct = True
    
    # Increment attempts
    new_attempts = current_attempts + 1
    
    update_data = {
        "$inc": {"solved": 1},
        "$set": {f"current_riddle_attempts.{data.riddle_id}": new_attempts}
    }
    
    points_change = 0
    skip_to_next = False
    max_attempts_reached = False
    
    if correct:
        # ✅ CORRECT ANSWER
        update_data["$inc"]["correct"] = 1
        
        # Award points based on difficulty
        difficulty_points = {
            "easy": 10,
            "medium": 15,
            "hard": 20
        }
        points_change = difficulty_points.get(riddle.get("difficulty", "medium"), 10)
        
        # Bonus for first attempt
        if current_attempts == 0:
            points_change += 5
        
        update_data["$inc"]["points"] = points_change
        
        # Streak bonus
        last_active = user.get("last_active")
        today = datetime.utcnow().date()
        
        if last_active:
            last_date = last_active.date() if isinstance(last_active, datetime) else today
            days_diff = (today - last_date).days
            
            if days_diff == 1:
                update_data["$inc"]["streak"] = 1
            elif days_diff > 1:
                update_data["$set"]["streak"] = 1
        else:
            update_data["$set"]["streak"] = 1
        
        skip_to_next = True
        message = f"🎉 Correct! +{points_change} points"
        
    elif new_attempts >= 2:
        # ❌ FAILED AFTER 2 ATTEMPTS - DEDUCT 5 POINTS AND LOCK
        points_change = -5
        update_data["$inc"]["points"] = points_change
        skip_to_next = True
        max_attempts_reached = True
        message = f"❌ Wrong! -5 points. Answer was: {riddle['answer']}"
    
    else:
        # ❌ WRONG BUT STILL HAVE 1 ATTEMPT LEFT
        message = f"❌ Wrong! 1 attempt left. Try again!"
    
    update_data.setdefault("$set", {})["last_active"] = datetime.utcnow()
    
    db.users.update_one({"_id": user_id}, update_data)
    updated_user = db.users.find_one({"_id": user_id})
    
    # Get user's rank
    rank_info = get_user_rank(updated_user.get("points", 0))
    
    return {
        "correct": correct,
        "answer": riddle["answer"] if new_attempts >= 2 else None,
        "message": message,
        "points_change": points_change,
        "attempts_left": 2 - new_attempts,
        "skip_to_next": skip_to_next,
        "max_attempts_reached": max_attempts_reached,
        "stats": {
            "solved": updated_user["solved"],
            "correct": updated_user["correct"],
            "streak": updated_user["streak"],
            "points": updated_user.get("points", 0)
        },
        "rank": rank_info
    }

# ==================== ACHIEVEMENTS ====================

@app.get("/achievements")
def get_achievements(user: dict = Depends(get_current_user)):
    """Get user's achievements and next milestone"""
    
    points = user.get("points", 0)
    current_rank = get_user_rank(points)
    
    # Find next milestone
    next_rank = None
    for achievement in ACHIEVEMENT_RANKS:
        if points < achievement["points"]:
            next_rank = achievement
            break
    
    # Calculate all unlocked achievements
    unlocked = []
    for achievement in ACHIEVEMENT_RANKS:
        if points >= achievement["points"]:
            unlocked.append(achievement)
    
    return {
        "current_rank": current_rank,
        "next_rank": next_rank,
        "points_to_next": next_rank["points"] - points if next_rank else 0,
        "unlocked_achievements": unlocked,
        "total_achievements": len(ACHIEVEMENT_RANKS),
        "progress_percent": round((len(unlocked) / len(ACHIEVEMENT_RANKS)) * 100, 1)
    }

# ==================== LEADERBOARD ====================

@app.get("/leaderboard")
def get_leaderboard(limit: int = 10):
    """Get top players by points"""
    
    top_players = list(db.users.find(
        {},
        {
            "username": 1,
            "points": 1,
            "correct": 1,
            "solved": 1,
            "streak": 1
        }
    ).sort("points", -1).limit(limit))
    
    leaderboard = []
    for rank, player in enumerate(top_players, 1):
        accuracy = round((player.get("correct", 0) / player.get("solved", 1)) * 100, 1) if player.get("solved", 0) > 0 else 0
        rank_info = get_user_rank(player.get("points", 0))
        
        leaderboard.append({
            "rank": rank,
            "username": player["username"],
            "points": player.get("points", 0),
            "correct": player.get("correct", 0),
            "streak": player.get("streak", 0),
            "accuracy": accuracy,
            "rank_title": rank_info["rank"],
            "rank_icon": rank_info["icon"]
        })
    
    return {"leaderboard": leaderboard}

# ==================== DAILY CHALLENGE ====================

@app.get("/daily-challenge")
def get_daily_challenge(user: dict = Depends(get_current_user)):
    """Get today's daily challenge"""
    
    challenge = get_daily_challenge_riddle()
    
    if not challenge:
        raise HTTPException(status_code=503, detail="Daily challenge not available")
    
    user_id = user["_id"]
    today = datetime.utcnow().date().isoformat()
    
    completed = today in user.get("daily_challenges_completed", [])
    
    return {
        "challenge_id": challenge["_id"],
        "date": challenge["date"],
        "riddle": {
            "id": challenge["riddle"]["_id"],
            "question": challenge["riddle"]["question"],
            "difficulty": challenge["riddle"]["difficulty"],
            "category": challenge["riddle"]["category"]
        },
        "participants": len(challenge.get("participants", [])),
        "completed": completed
    }

@app.post("/daily-challenge/answer")
def answer_daily_challenge(data: DailyChallengeAnswer, user: dict = Depends(get_current_user)):
    """Submit answer for daily challenge"""
    
    today = datetime.utcnow().date().isoformat()
    challenge = db.daily_challenges.find_one({"date": today})
    
    if not challenge:
        raise HTTPException(status_code=404, detail="No challenge today")
    
    if today in user.get("daily_challenges_completed", []):
        raise HTTPException(status_code=400, detail="Already completed today's challenge")
    
    riddle = challenge["riddle"]
    user_answer = data.answer.strip().lower()
    correct_answer = riddle["answer"].strip().lower()
    
    correct = (user_answer == correct_answer)
    
    if correct:
        bonus_points = 50
        
        db.users.update_one(
            {"_id": user["_id"]},
            {
                "$inc": {"points": bonus_points, "correct": 1, "solved": 1},
                "$addToSet": {"daily_challenges_completed": today}
            }
        )
        
        db.daily_challenges.update_one(
            {"_id": challenge["_id"]},
            {"$addToSet": {"participants": user["username"]}}
        )
        
        return {
            "correct": True,
            "message": f"🎉 Daily Challenge Complete! +{bonus_points} points",
            "bonus_points": bonus_points
        }
    else:
        db.users.update_one(
            {"_id": user["_id"]},
            {"$inc": {"solved": 1}}
        )
        
        return {
            "correct": False,
            "message": f"❌ Wrong! Answer: {riddle['answer']}",
            "answer": riddle["answer"]
        }

# ==================== CATEGORIES ====================

@app.get("/categories")
def get_categories():
    """Get available riddle categories"""
    
    category_counts = {}
    
    for category in RIDDLE_CATEGORIES:
        count = db.riddles.count_documents({"category": category, "language": "en"})
        category_counts[category] = count
    
    return {
        "categories": [
            {"name": cat, "count": category_counts.get(cat, 0)}
            for cat in RIDDLE_CATEGORIES
        ]
    }

# ==================== SHARE RIDDLES ====================

@app.post("/share")
def share_riddle(data: ShareRiddleRequest, user: dict = Depends(get_current_user)):
    """Share a riddle"""
    
    riddle = db.riddles.find_one({"_id": data.riddle_id})
    
    if not riddle:
        raise HTTPException(status_code=404, detail="Riddle not found")
    
    db.riddles.update_one(
        {"_id": data.riddle_id},
        {"$inc": {"shares": 1}}
    )
    
    share_url = f"https://riddleapp.com/riddle/{data.riddle_id}"
    
    return {
        "message": "Riddle shared!",
        "share_url": share_url,
        "riddle": {
            "question": riddle["question"],
            "category": riddle.get("category", "general")
        }
    }

@app.get("/riddle/shared/{riddle_id}")
def get_shared_riddle(riddle_id: str):
    """Get a shared riddle"""
    
    riddle = db.riddles.find_one({"_id": riddle_id})
    
    if not riddle:
        raise HTTPException(status_code=404, detail="Riddle not found")
    
    return {
        "id": str(riddle["_id"]),
        "question": riddle["question"],
        "category": riddle.get("category", "general"),
        "difficulty": riddle.get("difficulty", "medium"),
        "shares": riddle.get("shares", 0)
    }

# ==================== MULTIPLAYER ROOMS ====================

@app.post("/multiplayer/create")
def create_multiplayer_room(data: MultiplayerRoomCreate, user: dict = Depends(get_current_user)):
    """Create a multiplayer room"""
    
    room_id = str(ObjectId())
    
    room = {
        "_id": room_id,
        "name": data.room_name,
        "host": user["username"],
        "host_id": user["_id"],
        "players": [{
            "user_id": user["_id"],
            "username": user["username"],
            "score": 0,
            "answered": []
        }],
        "max_players": data.max_players,
        "current_riddle": None,
        "status": "waiting",
        "created_at": datetime.utcnow()
    }
    
    db.multiplayer_rooms.insert_one(room)
    
    return {
        "room_id": room_id,
        "room_name": data.room_name,
        "message": "Room created! Share room ID with friends."
    }

@app.post("/multiplayer/join")
def join_multiplayer_room(data: MultiplayerJoin, user: dict = Depends(get_current_user)):
    """Join a multiplayer room"""
    
    room = db.multiplayer_rooms.find_one({"_id": data.room_id})
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    if len(room["players"]) >= room["max_players"]:
        raise HTTPException(status_code=400, detail="Room is full")
    
    player_ids = [p["user_id"] for p in room["players"]]
    if user["_id"] in player_ids:
        raise HTTPException(status_code=400, detail="Already in room")
    
    db.multiplayer_rooms.update_one(
        {"_id": data.room_id},
        {"$push": {
            "players": {
                "user_id": user["_id"],
                "username": user["username"],
                "score": 0,
                "answered": []
            }
        }}
    )
    
    return {
        "message": f"Joined room: {room['name']}",
        "room_id": data.room_id,
        "players": len(room["players"]) + 1
    }

@app.get("/multiplayer/room/{room_id}")
def get_multiplayer_room(room_id: str, user: dict = Depends(get_current_user)):
    """Get multiplayer room details"""
    
    room = db.multiplayer_rooms.find_one({"_id": room_id})
    
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    return {
        "room_id": room["_id"],
        "name": room["name"],
        "host": room["host"],
        "players": room["players"],
        "status": room["status"],
        "current_riddle": room.get("current_riddle")
    }

@app.get("/multiplayer/rooms")
def get_active_rooms():
    """Get list of active multiplayer rooms"""
    
    rooms = list(db.multiplayer_rooms.find(
        {"status": {"$in": ["waiting", "active"]}},
        {"name": 1, "host": 1, "players": 1, "max_players": 1}
    ).limit(20))
    
    return {
        "rooms": [
            {
                "room_id": room["_id"],
                "name": room["name"],
                "host": room["host"],
                "players": len(room["players"]),
                "max_players": room["max_players"]
            }
            for room in rooms
        ]
    }

# ==================== PROFILE & STATS ====================

@app.get("/profile")
def get_profile(user: dict = Depends(get_current_user)):
    solved = user.get("solved", 0)
    correct = user.get("correct", 0)
    accuracy = round((correct / solved * 100), 1) if solved > 0 else 0
    seen_count = len(user.get("seen_riddles", []))
    points = user.get("points", 0)
    
    users_with_higher_points = db.users.count_documents({
        "points": {"$gt": points}
    })
    rank = users_with_higher_points + 1
    
    # Get user's achievement rank
    rank_info = get_user_rank(points)
    
    return {
        "username": user["username"],
        "email": user["email"],
        "language": user.get("language", "en"),
        "total_solved": solved,
        "correct_answers": correct,
        "accuracy": accuracy,
        "current_streak": user.get("streak", 0),
        "points": points,
        "rank": rank,
        "unique_riddles_seen": seen_count,
        "daily_challenges_completed": len(user.get("daily_challenges_completed", [])),
        "achievement_rank": rank_info["rank"],
        "achievement_title": rank_info["title"],
        "achievement_icon": rank_info["icon"]
    }

@app.post("/reset-history")
def reset_history(user: dict = Depends(get_current_user)):
    db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"seen_riddles": [], "current_riddle_attempts": {}}}
    )
    return {"message": "History reset!"}

@app.get("/")
def root():
    riddle_count = db.riddles.count_documents({"language": "en"})
    unique_answers = db.riddles.distinct("answer", {"language": "en"})
    
    return {
        "message": "🧩 AI Riddle App",
        "status": "running",
        "version": "5.1",
        "database": "MongoDB Atlas",
        "total_riddles": riddle_count,
        "unique_answers": len(unique_answers),
        "rules": {
            "attempts": "2 per riddle",
            "correct": "+10 to +20 points (+5 bonus first try)",
            "wrong": "-5 points after 2 attempts",
            "daily_challenge": "+50 bonus points",
            "ranks": "500, 1000, 1500, 2000+"
        }
    }

@app.get("/test")
def test():
    en_count = db.riddles.count_documents({"language": "en"})
    hi_count = db.riddles.count_documents({"language": "hi"})
    total_users = db.users.count_documents({})
    active_rooms = db.multiplayer_rooms.count_documents({"status": {"$in": ["waiting", "active"]}})
    
    # Get unique answers count
    unique_answers = len(db.riddles.distinct("answer", {"language": "en"}))
    
    return {
        "status": "✅ All Features Active!",
        "database": "MongoDB Atlas",
        "english_riddles": en_count,
        "unique_english_answers": unique_answers,
        "hindi_riddles": hi_count,
        "users": total_users,
        "active_multiplayer_rooms": active_rooms,
        "achievement_ranks": len(ACHIEVEMENT_RANKS),
        "connection_pool": "50 max connections",
        "ai_diversity": "Enhanced with duplicate detection"
    }

# ==================== STARTUP ====================

def startup_db():
    """Initialize database on startup"""
    
    try:
        # Fix all users
        db.users.update_many(
            {"seen_riddles": {"$exists": False}},
            {"$set": {"seen_riddles": [], "points": 0, "daily_challenges_completed": [], "current_riddle_attempts": {}}}
        )
        
        db.users.update_many(
            {"points": {"$exists": False}},
            {"$set": {"points": 0}}
        )
        
        db.users.update_many(
            {"daily_challenges_completed": {"$exists": False}},
            {"$set": {"daily_challenges_completed": []}}
        )
        
        db.users.update_many(
            {"current_riddle_attempts": {"$exists": False}},
            {"$set": {"current_riddle_attempts": {}}}
        )
        
        # Add riddle_hash to existing riddles (migration)
        riddles_without_hash = db.riddles.find({"riddle_hash": {"$exists": False}})
        for riddle in riddles_without_hash:
            riddle_hash = create_riddle_hash(riddle.get("question", ""), riddle.get("answer", ""))
            db.riddles.update_one(
                {"_id": riddle["_id"]},
                {"$set": {"riddle_hash": riddle_hash}}
            )
        
        # Create indexes
        db.users.create_index([("email", 1)], unique=True)
        db.users.create_index([("points", -1)])
        db.users.create_index([("seen_riddles", 1)])
        db.riddles.create_index([("answer", 1)])
        db.riddles.create_index([("riddle_hash", 1)], unique=True)
        db.riddles.create_index([("category", 1)])
        db.riddles.create_index([("language", 1)])
        db.daily_challenges.create_index([("date", 1)])
        print("✅ Database indexes created")
    except Exception as e:
        print(f"⚠️ Index warning: {e}")
    
    en_count = db.riddles.count_documents({"language": "en"})
    hi_count = db.riddles.count_documents({"language": "hi"})
    total_users = db.users.count_documents({})
    unique_answers = len(db.riddles.distinct("answer", {"language": "en"}))
    
    print("=" * 60)
    print("🧩 AI RIDDLE APP - READY FOR DEPLOYMENT")
    print("=" * 60)
    print(f"☁️  Database: MongoDB Atlas")
    print(f"📚 Riddles: {en_count} EN / {hi_count} HI")
    print(f"🎯 Unique Answers: {unique_answers}")
    print(f"👥 Users: {total_users}")
    print(f"🎲 AI Temperature: 1.8 (High Diversity)")
    print(f"🚫 Duplicate Detection: ENABLED")
    print(f"🔒 Max 2 Attempts: ENFORCED")
    print(f"✅ Correct: +10 to +20 points (+5 first try bonus)")
    print(f"❌ Wrong (2 attempts): -5 points + AUTO SKIP")
    print(f"🏆 Ranks: 500, 1000, 1500, 2000+")
    print("=" * 60)

startup_db()
