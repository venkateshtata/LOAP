import sqlite3
import random

# Connect to SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect("real_estate.db")
cursor = conn.cursor()

# Create Property table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Property (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT NOT NULL,
    shortcode TEXT NOT NULL,
    name TEXT NOT NULL
)
''')

# Create Contractor table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Contractor (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    area TEXT NOT NULL,
    phone_number TEXT NOT NULL
)
''')

# Create Property_Contractor linking table
cursor.execute('''
CREATE TABLE IF NOT EXISTS Property_Contractor (
    property_id INTEGER,
    contractor_id INTEGER,
    PRIMARY KEY (property_id, contractor_id),
    FOREIGN KEY (property_id) REFERENCES Property(id),
    FOREIGN KEY (contractor_id) REFERENCES Contractor(id)
)
''')

# Populate Property table with 10 records
properties = [
    ("123 Main St", "P1", "Sunset Villas"),
    ("456 Oak Ave", "P2", "Lakeview Homes"),
    ("789 Pine Rd", "P3", "Hillside Residency"),
    ("101 Maple St", "P4", "Urban Heights"),
    ("202 Cedar Ln", "P5", "Greenwood Estates"),
    ("303 Birch Blvd", "P6", "Summit Towers"),
    ("404 Spruce Dr", "P7", "Riverside Condos"),
    ("505 Aspen Ct", "P8", "Mountain View Lofts"),
    ("606 Cherry Way", "P9", "Grand Oaks"),
    ("707 Walnut Pl", "P10", "Golden Meadows")
]
cursor.executemany("INSERT INTO Property (address, shortcode, name) VALUES (?, ?, ?)", properties)

# Populate Contractor table with 10 records
contractors = [
    ("John Doe", "123 Contract Ln", "Metro Area", "555-1234"),
    ("Jane Smith", "456 Builder Rd", "Uptown", "555-5678"),
    ("Mike Johnson", "789 Developer Ave", "Downtown", "555-9101"),
    ("Emily Davis", "101 Renovation St", "Suburban", "555-1122"),
    ("Chris Wilson", "202 Construction Blvd", "Industrial", "555-3344"),
    ("Laura Brown", "303 Repair Dr", "Coastal", "555-5566"),
    ("Tom Harris", "404 Remodel Ln", "Mountain", "555-7788"),
    ("Emma White", "505 Rebuild Ct", "Rural", "555-9900"),
    ("David Green", "606 Framework Pl", "City Center", "555-2233"),
    ("Sophia Black", "707 Masonry Way", "Historic District", "555-4455")
]
cursor.executemany("INSERT INTO Contractor (name, address, area, phone_number) VALUES (?, ?, ?, ?)", contractors)

# Link properties with contractors randomly
property_ids = [i+1 for i in range(10)]
contractor_ids = [i+1 for i in range(10)]
links = [(random.choice(property_ids), random.choice(contractor_ids)) for _ in range(10)]
cursor.executemany("INSERT INTO Property_Contractor (property_id, contractor_id) VALUES (?, ?)", links)

# Commit changes and close connection
conn.commit()

# Function to fetch all properties
def get_properties():
    print("Fetching all properties...")
    cursor.execute("SELECT * FROM Property")
    return cursor.fetchall()

# Function to fetch all contractors
def get_contractors():
    cursor.execute("SELECT * FROM Contractor")
    return cursor.fetchall()

# Function to link a property with a contractor
def link_property_contractor(property_id, contractor_id):
    cursor.execute('''
    INSERT INTO Property_Contractor (property_id, contractor_id)
    VALUES (?, ?)
    ''', (property_id, contractor_id))
    conn.commit()

# Example Usage
print("Properties:", get_properties())
print("Contractors:", get_contractors())

conn.close()

print("SQLite tables populated and accessed successfully.")
