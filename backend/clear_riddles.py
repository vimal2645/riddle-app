from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client.riddle_app

# Delete all riddles
result = db.riddles.delete_many({})
print(f"🗑️ Deleted {result.deleted_count} old riddles")

# Reset all users' seen riddles
result2 = db.users.update_many({}, {"$set": {"seen_riddles": []}})
print(f"🔄 Reset {result2.modified_count} users")

# Check
riddle_count = db.riddles.count_documents({})
print(f"📚 Riddles in database: {riddle_count}")

client.close()
print("✅ Database cleared! Ready for unlimited API riddles.")
