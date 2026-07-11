"""Quick script to explore the MongoDB database structure."""
from pymongo import MongoClient
import json

MONGO_URI = "mongodb+srv://biuser:bi7890@cluster0.sf6hgbj.mongodb.net/?appName=Cluster0"

client = MongoClient(MONGO_URI)

# List all databases
print("=== DATABASES ===")
for db_name in client.list_database_names():
    print(f"  📁 {db_name}")

# For each non-system database, list collections and sample documents
for db_name in client.list_database_names():
    if db_name in ('admin', 'local', 'config'):
        continue
    db = client[db_name]
    print(f"\n{'='*60}")
    print(f"DATABASE: {db_name}")
    print(f"{'='*60}")
    
    for coll_name in db.list_collection_names():
        coll = db[coll_name]
        count = coll.estimated_document_count()
        print(f"\n  📋 Collection: {coll_name} ({count:,} documents)")
        
        # Get one sample document
        sample = coll.find_one()
        if sample:
            # Convert ObjectId to string for display
            sample['_id'] = str(sample['_id'])
            print(f"     Sample document keys: {list(sample.keys())}")
            for key, val in sample.items():
                val_str = str(val)
                if len(val_str) > 100:
                    val_str = val_str[:100] + "..."
                print(f"       {key}: {val_str}  (type: {type(val).__name__})")

client.close()
print("\n✅ Done!")
