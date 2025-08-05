import subprocess
import re
from mysql.connector import connect, Error
import time
from gpiozero import AngularServo

# === Database Configuration ===
DB_CONFIG = {
    'host': 'localhost',
    'user': 'plate_api',
    'password': 'api#sh1',
    'database': 'automatic_gate'
}

# === GPIO Setup ===
SERVO_PIN = 14
servo = AngularServo(SERVO_PIN, min_angle=0, max_angle=180,
                     min_pulse_width=0.5/1000, max_pulse_width=2.5/1000)

# === Servo Control Functions ===


def set_servo_angle(angle):
    """Set servo to specified angle and wait for movement to complete"""
    servo.angle = angle
    time.sleep(1)  # Allow time for servo to move


def open_gate():
    """Open the gate by setting servo to open position"""
    print("🔓 Opening gate...")
    set_servo_angle(90)
    print("✅ Gate fully open")


def close_gate():
    """Close the gate by setting servo to closed position"""
    print("🔒 Closing gate...")
    set_servo_angle(0)
    print("✅ Gate fully closed")

# === Reusable Logging Function ===


def write_log(level, source, message, user_id=None):
    try:
        db_connection = connect(**DB_CONFIG)
        cursor = db_connection.cursor()
        cursor.execute("""
            INSERT INTO logs (level, source, message, user_id)
            VALUES (%s, %s, %s, %s)
        """, (level, source, message, user_id))
        db_connection.commit()
        cursor.close()
        db_connection.close()
    except Error as e:
        print(f"❌ Failed to write log: {e}")

# === Main Processing ===


def process_gate_access():
    try:
        # === Step 1: Run OCR and Capture Output ===
        process = subprocess.run(
            ["python3", "main.py"],
            capture_output=True,
            text=True
        )

        all_output = process.stdout.strip().split('\n')
        plate_line = next(
            (line for line in all_output if line.startswith("PLATE_RESULT:")), None)

        if plate_line:
            recognized_plate = plate_line.replace("PLATE_RESULT:", "").strip()
            print(f"📸 OCR Detected Plate: {recognized_plate}")
        else:
            print("❌ ERROR: No plate result found.")
            write_log('ERROR', 'GateAccess',
                      'No plate result found from OCR.', None)
            return

        cleaned_plate = recognized_plate.replace(
            '_', '').replace(' ', '').upper()
        plate_pattern = re.compile(r'^[A-Z]{1,2}\d{1,4}[A-Z]{1,3}$')

        # === Step 2: Validate Plate Format ===
        if not plate_pattern.match(cleaned_plate):
            error_message = f"Invalid plate format: {cleaned_plate}"
            print(f"❌ {error_message}")
            write_log('DENIED', 'GateAccess', error_message, None)
            return

        # === Step 3: Load Allowed Plates from Database ===
        allowed_plates = []

        try:
            db_connection = connect(**DB_CONFIG)
            cursor = db_connection.cursor()
            cursor.execute(
                "SELECT plate_number, owner_name, is_active FROM plates")
            allowed_plates = [
                {
                    "plate": plate[0].replace('_', '').replace(' ', '').upper(),
                    "owner": plate[1],
                    "active": plate[2]
                }
                for plate in cursor.fetchall()
            ]
        except Error as err:
            print(f"❌ ERROR: Failed to load plates: {err}")
            write_log('ERROR', 'Database',
                      f'Failed to load allowed plates: {err}', None)
            return

        if not allowed_plates:
            print("❌ ERROR: No allowed plates found.")
            write_log('ERROR', 'Database',
                      'Allowed plates table is empty.', None)
            return

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
            # Skip inactive plates
            if not db_plate["active"]:
                continue

            distance = hamming_distance(cleaned_plate, db_plate["plate"])
            print(
                f"🔍 Checking against {db_plate['plate']} ({db_plate['owner']}): Distance = {distance}")

            if distance <= max_allowed_distance:
                matched = True
                matched_plate = db_plate
                log_message = f"Access granted: {cleaned_plate} matches {db_plate['plate']} (distance {distance})"
                print(f"✅ {log_message}")
                write_log('GRANTED', 'GateAccess', log_message, None)
                break

        # === Step 5: Gate Control ===
        if matched:
            try:
                open_gate()
                # servo.value = None  # Stop jitter

                # Keep gate open for 5 seconds
                print("⏳ Gate open for 5 seconds...")
                time.sleep(5)

                close_gate()
                # servo.value = None  # Also stop jitter

                # Log successful operation
                write_log('INFO', 'GateControl',
                          f'Gate cycle completed for {matched_plate["plate"]}', None)

            except Exception as e:
                error_msg = f"Gate control failed: {str(e)}"
                print(f"❌ {error_msg}")
                write_log('ERROR', 'GateControl', error_msg, None)
        else:
            log_message = f"Access denied: {cleaned_plate} did not match any active plate."
            print(f"❌ {log_message}")
            write_log('DENIED', 'GateAccess', log_message, None)

    except Exception as e:
        print(f"🛑 Critical error in main process: {str(e)}")
        write_log('CRITICAL', 'GateSystem', f'System failure: {str(e)}', None)

    finally:
        # === Step 6: Clean Up ===
        try:
            if 'cursor' in locals():
                cursor.close()
            if 'db_connection' in locals():
                db_connection.close()
        except:
            pass


# === Run the system ===
if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 Starting Automatic Gate Access System")
    print("="*50 + "\n")

    process_gate_access()

    print("\n" + "="*50)
    print("🏁 System Operation Completed")
    print("="*50 + "\n")
