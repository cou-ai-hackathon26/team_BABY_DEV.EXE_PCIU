
from database import db, check_database_connection
from datetime import datetime, timezone

if not check_database_connection():
    raise SystemExit(1)

collection = db["connection_test"]

# CREATE
result = collection.insert_one({
    "application": "CircularShield",
    "message": "Database connection test",
    "status": "success",
    "created_at": datetime.now(timezone.utc)
})

document_id = result.inserted_id

print("\nCREATE: Successful")
print("Document ID:", document_id)

# READ
document = collection.find_one({
    "_id": document_id
})

assert document is not None

print("\nREAD: Successful")
print(document)

# UPDATE
updated = collection.update_one(
    {"_id": document_id},
    {"$set": {"status": "updated"}}
)

assert updated.modified_count == 1

print("\nUPDATE: Successful")

# DELETE
deleted = collection.delete_one({
    "_id": document_id
})

assert deleted.deleted_count == 1

print("\nDELETE: Successful")

print("\nAll CRUD operations completed successfully!")
