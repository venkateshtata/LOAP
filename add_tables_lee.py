import sqlite3

# Define database path
DB_PATH = "real_estate.db"

# Connect to the SQLite database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create "Flyp_contact" table
cursor.execute("""
CREATE TABLE IF NOT EXISTS "Flyp_contact" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL,
    fly_person_name TEXT NOT NULL,
    meeting_link TEXT NOT NULL,
    FOREIGN KEY (property_id) REFERENCES Property(property_id)
);
""")

# Insert 5 mock records
mock_data = [
    (1, "Alice Johnson", "https://calendly.com/alice-johnson"),
    (2, "Bob Smith", "https://calendly.com/bob-smith"),
    (3, "Charlie Davis", "https://calendly.com/charlie-davis"),
    (4, "Diana Ross", "https://calendly.com/diana-ross"),
    (5, "Edward Green", "https://calendly.com/edward-green")
]

cursor.executemany("""
INSERT INTO "Flyp_contact" (property_id, fly_person_name, meeting_link)
VALUES (?, ?, ?);
""", mock_data)

# Commit the changes
conn.commit()

# Fetch and display records to verify insertion
cursor.execute("SELECT * FROM 'Flyp_contact'")
records = cursor.fetchall()

print("Flyp_contact table records:")
for record in records:
    print(record)


cursor.execute("SELECT * FROM Flyp_contact")
# Close the connection
conn.close()


