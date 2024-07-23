from pymongo import MongoClient
import bcrypt

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['hrms_db']
employees_collection = db['employees']
leave_requests_collection = db['leave_requests']
attendance_collection = db['attendance']

# Create a hashed password for the admin
admin_password = bcrypt.hashpw('vaibhav@2803'.encode('utf-8'), bcrypt.gensalt())

# Prepare the admin document
admin_document = {
    'name': 'Vaibhav Gunjal',
    'email': 'admin@example.com',
    'password': admin_password,
    'role': 'admin',
    'approved': True
}

# Print the document to be inserted
print("Inserting document:", admin_document)

# Insert the admin document into the employees collection
try:
    result = employees_collection.insert_one(admin_document)
    print("Document inserted with _id:", result.inserted_id)
except Exception as e:
    print("An error occurred:", e)
