import psycopg2
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ParkingDatabase:
    def __init__(self):
        self.conn_params = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'parking'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'agnes')
        }
        self.init_db()

    def get_connection(self):
        """Create a new database connection"""
        return psycopg2.connect(**self.conn_params)

    def init_db(self):
        """Initialize the database with required tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicles (
            id SERIAL PRIMARY KEY,
            plate_number VARCHAR(10) NOT NULL,
            entry_time TIMESTAMP NOT NULL,
            exit_time TIMESTAMP,
            payment_status INTEGER DEFAULT 0,
            payment_amount DECIMAL(10,2),
            payment_time TIMESTAMP
        )
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS unauthorized_exits (
            id SERIAL PRIMARY KEY,
            plate_number VARCHAR(10) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            gate_location VARCHAR(10) NOT NULL
        )
        ''')

        conn.commit()
        conn.close()

    def add_vehicle_entry(self, plate_number):
        """Record a new vehicle entry"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO vehicles (plate_number, entry_time)
        VALUES (%s, %s)
        ''', (plate_number, datetime.now()))
        conn.commit()
        conn.close()

    def get_unpaid_entry(self, plate_number):
        """Get the most recent unpaid entry for a vehicle"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT entry_time FROM vehicles
        WHERE plate_number = %s AND payment_status = 0
        ORDER BY entry_time DESC LIMIT 1
        ''', (plate_number,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def update_payment(self, plate_number, amount, payment_time=None):
        """Update payment status and amount for a vehicle (latest unpaid entry only)"""
        if payment_time is None:
            payment_time = datetime.now()
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        WITH unpaid AS (
            SELECT id FROM vehicles
            WHERE plate_number = %s AND payment_status = 0
            ORDER BY entry_time DESC
            LIMIT 1
        )
        UPDATE vehicles
        SET payment_status = 1,
            payment_amount = %s,
            payment_time = %s
        WHERE id IN (SELECT id FROM unpaid)
        ''', (plate_number, amount, payment_time))
        conn.commit()
        conn.close()

    def record_unauthorized_exit(self, plate_number, gate_location):
        """Record an unauthorized exit attempt"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        INSERT INTO unauthorized_exits (plate_number, timestamp, gate_location)
        VALUES (%s, %s, %s)
        ''', (plate_number, datetime.now(), gate_location))
        conn.commit()
        conn.close()

    def get_vehicle_history(self, plate_number=None, limit=100):
        """Get vehicle entry/exit history"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if plate_number:
            cursor.execute('''
            SELECT * FROM vehicles
            WHERE plate_number = %s
            ORDER BY entry_time DESC LIMIT %s
            ''', (plate_number, limit))
        else:
            cursor.execute('''
            SELECT * FROM vehicles
            ORDER BY entry_time DESC LIMIT %s
            ''', (limit,))
        results = cursor.fetchall()
        conn.close()
        return results

    def get_unauthorized_exits(self, limit=100):
        """Get unauthorized exit attempts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT * FROM unauthorized_exits
        ORDER BY timestamp DESC LIMIT %s
        ''', (limit,))
        results = cursor.fetchall()
        conn.close()
        return results

    def get_paid_entry_without_exit(self, plate_number):
        """Check if the vehicle has a paid entry without exit recorded"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        SELECT id FROM vehicles
        WHERE plate_number = %s AND payment_status = 1 AND exit_time IS NULL
        ORDER BY entry_time DESC LIMIT 1
        ''', (plate_number,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def update_exit_time(self, plate_number):
        """Update the exit time for the most recent paid entry"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
        WITH target AS (
            SELECT id FROM vehicles
            WHERE plate_number = %s AND payment_status = 1 AND exit_time IS NULL
            ORDER BY entry_time DESC
            LIMIT 1
        )
        UPDATE vehicles
        SET exit_time = %s
        WHERE id IN (SELECT id FROM target)
        ''', (plate_number, datetime.now()))
        conn.commit()
        conn.close()
