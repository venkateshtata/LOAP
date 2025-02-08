import sqlite3
import random
from datetime import datetime, timedelta

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect("real_estate.db")
cursor = conn.cursor()

# Drop tables if they already exist (forces recreation)
cursor.execute("DROP TABLE IF EXISTS Conversation")
cursor.execute("DROP TABLE IF EXISTS Property")
cursor.execute("DROP TABLE IF EXISTS Contractor")
cursor.execute("DROP TABLE IF EXISTS Role_map")

# Create Property table
cursor.execute('''
CREATE TABLE Property (
    property_id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT NOT NULL,
    shortcode TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL,
    status_detail TEXT NOT NULL
)
''')

# Create Contractor table
cursor.execute('''
CREATE TABLE Contractor (
    contractor_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    area TEXT NOT NULL,
    phone_number TEXT NOT NULL
)
''')

# Create Conversation table
cursor.execute('''
CREATE TABLE Conversation (
    conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL,
    contractor_id INTEGER NOT NULL,
    chat TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    phone_number TEXT NOT NULL,
    FOREIGN KEY (property_id) REFERENCES Property(property_id),
    FOREIGN KEY (contractor_id) REFERENCES Contractor(contractor_id)
)
''')

# Create Role_map table
cursor.execute('''
CREATE TABLE Role_map (
    phone_number TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    property_id INTEGER NOT NULL
)
''')

# Insert sample data for Property table
properties = [
    ("123 Main St", "P001", "Sunset Villa", "Available", "Ready to move"),
    ("456 Oak St", "P002", "Maple Residency", "Sold", "Under renovation"),
    ("789 Pine St", "P003", "Pine Crest", "Available", "Newly constructed"),
    ("321 Elm St", "P004", "Elm Heights", "Under Contract", "Pending approval"),
    ("654 Cedar St", "P005", "Cedar Homes", "Available", "Furnished"),
]

cursor.executemany('''
INSERT INTO Property (address, shortcode, name, status, status_detail)
VALUES (?, ?, ?, ?, ?)''', properties)

# Insert sample data for Contractor table
contractors = [
    ("John Doe", "789 Contractor Ave", "Downtown", "1234567890"),
    ("Jane Smith", "456 Builder Rd", "Uptown", "9876543210"),
    ("Mike Johnson", "321 Fixer St", "Suburb", "5678901234"),
    ("Sarah Lee", "654 Renovate Blvd", "Midtown", "4321098765"),
    ("David Kim", "147 Construct Ln", "Old Town", "6789012345"),
]

cursor.executemany('''
INSERT INTO Contractor (name, address, area, phone_number)
VALUES (?, ?, ?, ?)''', contractors)

# Insert sample data for Conversation table
conversations = []
for i in range(1, 11):
    property_id = random.randint(1, 5)
    contractor_id = random.randint(1, 5)
    chat = f"Discussion about property {property_id} with contractor {contractor_id}."
    timestamp = (datetime.now() - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d %H:%M:%S")
    phone_number = random.choice(["1234567890", "9876543210", "5678901234", "4321098765", "6789012345"])
    conversations.append((property_id, contractor_id, chat, timestamp, phone_number))

cursor.executemany('''
INSERT INTO Conversation (property_id, contractor_id, chat, timestamp, phone_number)
VALUES (?, ?, ?, ?, ?)''', conversations)

# Insert sample data for Role_map table
roles = [
    ("1234567890", "Admin", 1),
    ("9876543210", "User", 2),
    ("5678901234", "Manager", 3),
    ("4321098765", "User", 4),
    ("6789012345", "Admin", 5),
]

cursor.executemany('''
INSERT INTO Role_map (phone_number, role, property_id)
VALUES (?, ?, ?)''', roles)

# Commit and verify if tables were created
conn.commit()

# Print table verification
print("\nTables in the database:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for table in tables:
    print(table[0])

# Close the connection
conn.close()

print("\nDatabase populated successfully!")
