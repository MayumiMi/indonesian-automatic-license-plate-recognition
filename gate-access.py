import subprocess
from rapidfuzz import fuzz
import mysql.connector

# === Step 1: Run OCR (main.py) and Capture Output ===
process = subprocess.run(
    ["python3", "main.py"],  # Adjust full path if needed
    capture_output=True,
    text=True
)

# === Step 2: Parse Only the Plate Result Line ===
all_output = process.stdout.strip().split('\n')

# Look for line that starts with PLATE_RESULT:
plate_line = next((line for line in all_output if line.startswith("PLATE_RESULT:")), None)

if plate_line:
    recognized_plate = plate_line.replace("PLATE_RESULT:", "").strip()
    print(f"OCR Detected Plate: {recognized_plate}")
else:
    print("ERROR: No plate result found from OCR script output.")
    exit(1)

# === Step 3: Clean OCR Plate Result for Fuzzy Matching ===
cleaned_plate = recognized_plate.replace('_', '').replace(' ', '').upper()

# === Step 4: Load Allowed Plates from MySQL Database ===
allowed_plates = []

try:
    db_connection = mysql.connector.connect(
        host="localhost",            # MySQL host
        user="plate_api",            # MySQL username
        password="api#sh1",           # MySQL password
        database="automatic_gate"    # MySQL database name
    )

    cursor = db_connection.cursor()
    cursor.execute("SELECT plate_number FROM allowed_plates")

    for (plate_number,) in cursor.fetchall():
        cleaned_db_plate = plate_number.replace('_', '').replace(' ', '').upper()
        allowed_plates.append(cleaned_db_plate)

    cursor.close()
    db_connection.close()

except mysql.connector.Error as err:
    print(f"ERROR: Could not connect or query MySQL: {err}")
    exit(1)

# If no plates in database
if not allowed_plates:
    print("ERROR: No allowed plates found in database.")
    exit(1)

# === Step 5: Fuzzy Matching ===
threshold = 85  # Similarity threshold, adjust as needed
matched = False

for db_plate in allowed_plates:
    similarity = fuzz.ratio(cleaned_plate, db_plate)
    print(f"Checking against {db_plate}: Similarity = {similarity}%")
    if similarity >= threshold:
        print(f"✅ Access Granted: {cleaned_plate} matches {db_plate} ({similarity}% similarity)")
        matched = True
        break

if not matched:
    print(f"❌ Access Denied: Plate {cleaned_plate} not found in database with similarity >= {threshold}%.")
