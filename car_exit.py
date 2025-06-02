import cv2
from ultralytics import YOLO
import pytesseract
import os
import time
import serial
import serial.tools.list_ports
from collections import Counter
import random
from database import ParkingDatabase  # ✅ Use DB instead of CSV

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Load trained YOLO model
model = YOLO(r'D:\PRACTICE\parking-management-system\best.pt')

# ===== Auto-detect Arduino Serial Port =====
def detect_arduino_port():
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if "Arduino" in port.description or "COM12" in port.description or "USB-SERIAL" in port.description:
            return port.device
    return None

arduino_port = detect_arduino_port()
if arduino_port:
    print(f"[CONNECTED] Arduino on {arduino_port}")
    arduino = serial.Serial(arduino_port, 9600, timeout=1)
    time.sleep(2)
else:
    print("[ERROR] Arduino not detected.")
    arduino = None

# ===== Simulated Ultrasonic Sensor =====
def mock_ultrasonic_distance():
    return random.randint(10, 40)

# ===== Constants =====
GATE_LOCATION = "Main Exit"

# ===== Database instance =====
db = ParkingDatabase()

# ===== Check DB if payment is done =====
def is_payment_complete(plate_number):
    entry_id = db.get_paid_entry_without_exit(plate_number)
    if entry_id:
        db.update_exit_time(plate_number)
        return True
    # Record unauthorized attempt when payment is not complete
    db.record_unauthorized_exit(plate_number, GATE_LOCATION)
    return False

# ===== Extract and Validate Plate from Image =====
def extract_plate_text(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    text = pytesseract.image_to_string(
        thresh, config='--psm 8 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    ).strip().replace(" ", "").upper()

    if "RA" in text:
        start = text.find("RA")
        candidate = text[start:start+7]
        if len(candidate) == 7:
            prefix, digits, suffix = candidate[:3], candidate[3:6], candidate[6]
            if prefix.isalpha() and digits.isdigit() and suffix.isalpha():
                return candidate
    return None

# ===== Main Camera Feed Loop =====
cap = cv2.VideoCapture(0)
plate_buffer = []

print("[EXIT SYSTEM] Ready. Press 'q' to quit.\n")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    distance = mock_ultrasonic_distance()
    print(f"[SENSOR] Distance: {distance} cm")

    if distance <= 50:
        results = model(frame)

        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                plate_img = frame[y1:y2, x1:x2]

                plate = extract_plate_text(plate_img)
                if plate:
                    print(f"[VALID] Plate Detected: {plate}")
                    plate_buffer.append(plate)

                    if len(plate_buffer) >= 3:
                        most_common = Counter(plate_buffer).most_common(1)[0][0]
                        plate_buffer.clear()

                        if is_payment_complete(most_common):
                            print(f"[ACCESS GRANTED] Payment complete for {most_common}")
                            if arduino:
                                arduino.write(b'1')
                                arduino.flush()
                                print("[GATE] Opening gate...")
                                time.sleep(15)
                                arduino.write(b'0')
                                arduino.flush()
                                print("[GATE] Closing gate...")
                        else:
                            print(f"[ACCESS DENIED] Payment NOT complete for {most_common}")
                            if arduino:
                                arduino.write(b'2')
                                arduino.flush()
                                print("[ALERT] Triggering buzzer...")

                cv2.imshow("Plate", plate_img)
                time.sleep(0.5)

    if distance <= 50:
        annotated_frame = results[0].plot()
        cv2.imshow("Exit Webcam Feed", annotated_frame)
    else:
        cv2.imshow("Exit Webcam Feed", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
if arduino:
    arduino.close()
cv2.destroyAllWindows()
