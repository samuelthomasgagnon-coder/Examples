
import sqlite3
import datetime
import os

class DBmanager: 
    def __init__(self):
        self.state = {}
        self.setup_database()

    def setup_database(self):
        s = self.state 
        if s is None:
            return
        images_dir = os.path.join(os.getcwd(), "server", "data", "images")
        db_path = os.path.join(os.getcwd(), "server", "data", "smile_metadata.db")
        if not os.path.exists(images_dir):
            os.makedirs(images_dir)
        s['DB_conn'] = sqlite3.connect(db_path)
        s['DB_cusor'] = s['DB_conn'].cursor()
        s['DB_cusor'].execute('''
            CREATE TABLE IF NOT EXISTS smiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                face_id INTEGER NOT NULL,
                capture_time TEXT NOT NULL
            )
        ''')
        s['DB_conn'].commit()
        s['DB_cusor'].execute("SELECT MAX(face_id) FROM smiles")
        s['next_face_id'] = s['DB_cusor'].fetchone()[0]

    def log_smilemeta_to_db(self, face_id):
        '''Logs a smile event 
        Only meta data is the Face and time'''
        timestamp = datetime.datetime.now().isoformat()
        s = self.state
        s['DB_cusor'].execute("INSERT INTO smiles (face_id, capture_time) VALUES (?, ?)", (face_id, timestamp))
        s['DB_conn'].commit()

    def cleanup_resources(self):
        """Clean up all resources before exit"""
        s = self.state
        DB_conn = s['DB_conn']
        # Close database connection
        if DB_conn:
            DB_conn.close()
            print("Database connection closed.")
