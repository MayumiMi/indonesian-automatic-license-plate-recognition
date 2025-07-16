import subprocess
import re
from mysql.connector import connect, Error
from datetime import datetime  # Added for timestamp handling

# === Database Configuration ===
DB_CONFIG = {
    'host': 'localhost',
    'user': 'plate_api',
    'password': 'api#sh1',
    'database': 'automatic_gate'
}

# === Reusable Logging Function (UPDATED for logs table) ===
def write_log(level, source, message, user_id=None):
    try:
        db_connection = connect(**DB_CONFIG)
        cursor = db_connection.cursor()
        
        # Updated INSERT statement for logs table
        cursor.execute("""
            INSERT INTO logs (timestamp, level, source, message, user_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (datetime.now(), level, source, message, user_id))
        
        db_connection.commit()
        cursor.close()
        db_connection.close()
    except Error as e:
        print(f"❌ Failed to write log: {e}")

# === Step 1: Run OCR and Capture Output ===
process = subprocess.run(
    ["python3", "main.py"],
    capture_output=True,
    text=True
)

all_output = process.stdout.strip().split('\n')
plate_line = next((line for line in all_output if line.startswith("PLATE_RESULT:")), None)

if plate_line:
    recognized_plate = plate_line.replace("PLATE_RESULT:", "").strip()
    print(f"OCR Detected Plate: {recognized_plate}")
else:
    print("❌ ERROR: No plate result found.")
    write_log('ERROR', 'GateAccess', 'No plate result found from OCR.', None)
    exit(1)

cleaned_plate = recognized_plate.replace('_', '').replace(' ', '').upper()
plate_pattern = re.compile(r'^[A-Z]{1,2}\d{1,4}[A-Z]{1,3}$')

# === Step 2: Validate Plate Format ===
if not plate_pattern.match(cleaned_plate):
    error_message = f"Invalid plate format: {cleaned_plate}"
    print(f"❌ {error_message}")
    write_log('DENIED', 'GateAccess', error_message, None)
    exit(1)

# === Step 3: Load Allowed Plates from Database ===
allowed_plates = []

try:
    db_connection = connect(**DB_CONFIG)
    cursor = db_connection.cursor()
    cursor.execute("SELECT plate_number FROM allowed_plates")
    allowed_plates = [plate[0].replace('_', '').replace(' ', '').upper() for plate in cursor.fetchall()]
    cursor.close()
    db_connection.close()
except Error as err:
    print(f"❌ ERROR: Failed to load plates: {err}")
    write_log('ERROR', 'Database', f'Failed to load allowed plates: {err}', None)
    exit(1)

if not allowed_plates:
    print("❌ ERROR: No allowed plates found.")
    write_log('ERROR', 'Database', 'Allowed plates table is empty.', None)
    exit(1)

# === Step 4: Hamming Distance Check ===
def hamming_distance(s1, s2):
    if len(s1) != len(s2):
        return float('inf')
    return sum(a != b for a, b in zip(s1, s2))

matched = False
max_allowed_distance = 1
matched_plate = None
log_message = ""

for db_plate in allowed_plates:
    distance = hamming_distance(cleaned_plate, db_plate)
    print(f"Checking against {db_plate}: Hamming distance = {distance}")
    if distance <= max_allowed_distance:
        matched = True
        matched_plate = db_plate
        log_message = f"Access granted: {cleaned_plate} matches {db_plate} (distance {distance})"
        print(f"✅ {log_message}")
        write_log('GRANTED', 'GateAccess', log_message, None)
        break

if not matched:
    log_message = f"Access denied: {cleaned_plate} did not match any allowed plate."
    print(f"❌ {log_message}")
    write_log('DENIED', 'GateAccess', log_message, None)