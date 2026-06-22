import os
import sqlite3
import json
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database")
DB_PATH = os.path.join(DB_DIR, "crowd.db")

def init_db():
    """
    Initializes the SQLite database and creates the analysis table if it doesn't exist.
    """
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analysis_history (
            analysis_id TEXT PRIMARY KEY,
            timestamp TEXT NOT NULL,
            uploaded_image_names TEXT NOT NULL,
            count INTEGER NOT NULL,
            density REAL NOT NULL,
            crowd_level TEXT NOT NULL,
            reliability_score REAL NOT NULL,
            fusion_count REAL,
            per_image_details TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_analysis(
    analysis_id: str,
    uploaded_image_names: list[str],
    count: int,
    density: float,
    crowd_level: str,
    reliability_score: float,
    fusion_count: float = None,
    per_image_details: dict = None
):
    """
    Saves a new analysis run into the SQLite history database.
    """
    init_db()  # Ensure table exists
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    image_names_json = json.dumps(uploaded_image_names)
    details_json = json.dumps(per_image_details) if per_image_details else None
    
    cursor.execute("""
        INSERT INTO analysis_history (
            analysis_id, timestamp, uploaded_image_names, count, density, 
            crowd_level, reliability_score, fusion_count, per_image_details
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        analysis_id, timestamp, image_names_json, count, density,
        crowd_level, reliability_score, fusion_count, details_json
    ))
    
    conn.commit()
    conn.close()

def fetch_history() -> list[dict]:
    """
    Fetches all historical analysis runs sorted by timestamp descending.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM analysis_history ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    
    history = []
    for row in rows:
        history.append({
            "analysis_id": row["analysis_id"],
            "timestamp": row["timestamp"],
            "uploaded_image_names": json.loads(row["uploaded_image_names"]),
            "count": row["count"],
            "density": row["density"],
            "crowd_level": row["crowd_level"],
            "reliability_score": row["reliability_score"],
            "fusion_count": row["fusion_count"],
            "per_image_details": json.loads(row["per_image_details"]) if row["per_image_details"] else None
        })
        
    conn.close()
    return history

def delete_analysis(analysis_id: str) -> bool:
    """
    Deletes a specific analysis record from the database.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM analysis_history WHERE analysis_id = ?", (analysis_id,))
    rows_affected = cursor.rowcount
    
    conn.commit()
    conn.close()
    return rows_affected > 0

def get_latest_analysis() -> dict | None:
    """
    Retrieves the most recent analysis run from the database.
    """
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM analysis_history ORDER BY timestamp DESC LIMIT 1")
    row = cursor.fetchone()
    
    result = None
    if row:
        result = {
            "analysis_id": row["analysis_id"],
            "timestamp": row["timestamp"],
            "uploaded_image_names": json.loads(row["uploaded_image_names"]),
            "count": row["count"],
            "density": row["density"],
            "crowd_level": row["crowd_level"],
            "reliability_score": row["reliability_score"],
            "fusion_count": row["fusion_count"],
            "per_image_details": json.loads(row["per_image_details"]) if row["per_image_details"] else None
        }
        
    conn.close()
    return result
