from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
client = MongoClient(MONGO_URL)
db = client.riddle_app

print("🔧 Fixing repeating riddles issue...\n")

# Fix all users
for user in db.users.find():
    seen = user.get("seen_riddles", [])
    
    # Convert all to strings and remove duplicates
    seen_clean = list(set([str(rid) for rid in seen if rid]))
    
    db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "seen_riddles": seen_clean,
                "current_riddle_attempts": {}
            }
        }
    )
    
    print(f"✅ Fixed user {user.get('username', 'Unknown')}: {len(seen_clean)} riddles seen")

print("\n✅ All fixes applied! Restart your backend.")
client.close()
