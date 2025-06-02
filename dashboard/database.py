import psycopg2
from datetime import datetime, timedelta
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

    def get_connection(self):
        """Create a new database connection"""
        return psycopg2.connect(**self.conn_params)

    def get_current_occupancy(self):
        """Get the current number of vehicles in the parking lot"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            # Count vehicles that have entered but not exited
            cursor.execute('''
                SELECT COUNT(*) FROM vehicles 
                WHERE exit_time IS NULL
            ''')
            occupancy = cursor.fetchone()[0]
            return occupancy
        finally:
            conn.close()

    def get_daily_revenue(self, date):
        """Get total revenue for a specific date"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT COALESCE(SUM(payment_amount), 0) 
                FROM vehicles 
                WHERE DATE(payment_time) = %s 
                AND payment_status = 1
            ''', (date,))
            revenue = cursor.fetchone()[0]
            return float(revenue) if revenue else 0
        finally:
            conn.close()

    def get_recent_activities(self, limit=5):
        """Get recent parking activities"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                (
                    SELECT 
                        plate_number,
                        'Vehicle Entry' as action,
                        entry_time as timestamp
                    FROM vehicles
                    WHERE entry_time IS NOT NULL
                )
                UNION ALL
                (
                    SELECT 
                        plate_number,
                        'Vehicle Exit' as action,
                        exit_time as timestamp
                    FROM vehicles
                    WHERE exit_time IS NOT NULL
                )
                UNION ALL
                (
                    SELECT 
                        plate_number,
                        'Payment Processed' as action,
                        payment_time as timestamp
                    FROM vehicles
                    WHERE payment_time IS NOT NULL
                )
                ORDER BY timestamp DESC
                LIMIT %s
            ''', (limit,))
            
            activities = []
            for row in cursor.fetchall():
                activities.append({
                    "plate_number": row[0],
                    "action": row[1],
                    "timestamp": row[2].isoformat() if row[2] else None
                })
            return activities
        finally:
            conn.close()

    def get_unauthorized_attempts(self, limit=5):
        """Get recent unauthorized exit attempts"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT plate_number, gate_location, timestamp
                FROM unauthorized_exits
                ORDER BY timestamp DESC
                LIMIT %s
            ''', (limit,))
            
            attempts = []
            for row in cursor.fetchall():
                attempts.append({
                    "plate_number": row[0],
                    "gate_location": row[1],
                    "timestamp": row[2].isoformat() if row[2] else None
                })
            return attempts
        finally:
            conn.close()

    def get_hourly_statistics(self, start_time, end_time):
        """Get hourly vehicle entry statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                WITH RECURSIVE hours AS (
                    SELECT date_trunc('hour', %s::timestamp) as hour
                    UNION ALL
                    SELECT hour + interval '1 hour'
                    FROM hours
                    WHERE hour < date_trunc('hour', %s::timestamp)
                )
                SELECT 
                    hours.hour,
                    COUNT(vehicles.id) as count
                FROM hours
                LEFT JOIN vehicles ON 
                    date_trunc('hour', vehicles.entry_time) = hours.hour
                GROUP BY hours.hour
                ORDER BY hours.hour
            ''', (start_time, end_time))
            
            results = cursor.fetchall()
            return {
                "labels": [row[0].strftime("%H:00") for row in results],
                "values": [row[1] for row in results]
            }
        finally:
            conn.close() 