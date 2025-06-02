import serial
import time
import re
from datetime import datetime
from database import ParkingDatabase

def calculate_payment(entry_time, exit_time):
    duration = (exit_time - entry_time).total_seconds() / 60
    rate_per_minute = 5
    amount_due = max(0, int(duration * rate_per_minute))
    return duration, amount_due

def is_noise(line):
    noise_prefixes = [
        "====", "place your card", "❌", "⚠️",
        "[TIMEOUT]", "READY", "[RECEIVED", "[WRITING]", "DONE", "[UPDATED]"
    ]
    line_lower = line.lower()
    return any(line_lower.startswith(prefix.lower()) for prefix in noise_prefixes)

def main():
    db = ParkingDatabase()
    arduino_port = "COM13"
    baud_rate = 9600

    try:
        arduino = serial.Serial(arduino_port, baud_rate, timeout=2)
        print(f"✅ Connected to {arduino_port}")
    except serial.SerialException as e:
        print(f"[ERROR] Serial port error: {e}")
        return

    print("👋 Parking Management System Started")
    print("📡 Waiting for card scan...\n")

    try:
        while True:
            if arduino.in_waiting > 0:
                line = arduino.readline().decode('utf-8').strip()

                if is_noise(line):
                    continue

                if ',' in line:
                    try:
                        plate_raw, balance_raw = line.split(',')
                        plate = plate_raw.strip().replace('\x00', '')
                        balance_cleaned = re.sub(r'[^\d]', '', balance_raw)

                        if not balance_cleaned.isdigit():
                            continue

                        balance = int(balance_cleaned)
                        print(f"\n🚗 Plate: {plate} | 💰 Balance: {balance} RWF")

                        entry_time = db.get_unpaid_entry(plate)
                        if not entry_time:
                            print(f"⚠️ No unpaid entry found for {plate}")
                            arduino.write(b"NO_UNPAID_ENTRY\n")
                            continue

                        exit_time = datetime.now()
                        duration, amount_due = calculate_payment(entry_time, exit_time)
                        print(f"⏱️ Duration: {int(duration)} mins | 🧾 Amount Due: {amount_due} RWF")

                        new_balance = balance - amount_due
                        if new_balance < 0:
                            print("❌ Insufficient balance.")
                            arduino.write(b"I\n")
                            continue

                        while True:
                            ready_signal = arduino.readline().decode('utf-8').strip()
                            if ready_signal.upper() == "READY":
                                break

                        arduino.write(f"{new_balance}\n".encode())
                        print(f"✅ Payment success | 🔄 New Balance: {new_balance} RWF")

                        db.update_payment(plate, amount_due)

                    except Exception as e:
                        print(f"[ERROR] {e}")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n[EXIT] Program terminated.")

    finally:
        arduino.close()
        print("[INFO] Serial port closed")

if __name__ == "__main__":
    main()
