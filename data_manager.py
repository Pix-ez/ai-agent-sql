# import sqlite3
# import json
# import os
# from typing import Dict, Any, List

# class DatabaseManager:
#     """Manages the creation, setup, and population of the school's SQLite database."""

#     def __init__(self, db_path: str = "school_management.db"):
#         """
#         Initializes the DatabaseManager.

#         Args:
#             db_path (str): The file path for the SQLite database.
#         """
#         self.db_path = db_path
#         # Delete the old DB file to ensure a fresh start each time
#         if os.path.exists(self.db_path):
#             os.remove(self.db_path)
#             print(f"Removed existing database at '{self.db_path}'.")

#     def setup_database_from_json(self, json_path: str):
#         """
#         The main public method to create and populate the database from a JSON file.

#         Args:
#             json_path (str): The path to the source JSON file.
#         """
#         if not os.path.exists(json_path):
#             print(f"Error: JSON file not found at '{json_path}'. Aborting.")
#             return

#         print(f"Database will be created at: {os.path.abspath(self.db_path)}")
        
#         conn = sqlite3.connect(self.db_path)
#         # Enable foreign key constraint enforcement
#         conn.execute("PRAGMA foreign_keys = ON;")
#         cursor = conn.cursor()
        
#         try:
#             # 1. Create all database tables with proper constraints
#             print("STEP 1: Creating database tables...")
#             self._create_tables(cursor)
#             print("Tables created successfully.\n")

#             # 2. Read the JSON file and populate the created tables
#             print(f"STEP 2: Populating database from '{json_path}'...")
#             self._populate_tables_from_json(cursor, json_path)
#             print("Data population complete.\n")

#             conn.commit()
#             print("Database setup successful. All changes have been committed.")

#         except sqlite3.Error as e:
#             print(f"An SQLite error occurred: {e}")
#             conn.rollback()
#         finally:
#             conn.close()

#     def _create_tables(self, cursor: sqlite3.Cursor):
#         """Defines and executes the SQL for creating all tables."""
        
#         # Core entity tables
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS students (
#                 id TEXT PRIMARY KEY,
#                 name TEXT NOT NULL,
#                 grade INTEGER,
#                 class TEXT,
#                 region TEXT
#             )
#         ''')

#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS classes (
#                 id TEXT PRIMARY KEY,
#                 grade INTEGER,
#                 class TEXT,
#                 teacher TEXT,
#                 UNIQUE(grade, class)
#             )
#         ''')

#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS admins (
#                 id TEXT PRIMARY KEY,
#                 name TEXT NOT NULL
#             )
#         ''')

#         # Activity tables
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS assignments (
#                 id TEXT PRIMARY KEY,
#                 title TEXT NOT NULL,
#                 due_date DATE,
#                 grade INTEGER,
#                 class TEXT
#             )
#         ''')

#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS exams (
#                 id TEXT PRIMARY KEY,
#                 subject TEXT NOT NULL,
#                 date DATE,
#                 grade INTEGER,
#                 class TEXT
#             )
#         ''')

#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS quizzes (
#                 id TEXT PRIMARY KEY,
#                 title TEXT NOT NULL,
#                 scheduled_date DATE,
#                 grade INTEGER,
#                 class TEXT
#             )
#         ''')

#         # Linking / Relational tables
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS submissions (
#                 student_id TEXT,
#                 assignment_id TEXT,
#                 submitted BOOLEAN,
#                 submission_date DATE,
#                 score INTEGER,
#                 PRIMARY KEY (student_id, assignment_id),
#                 FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
#                 FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE
#             )
#         ''')

#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS admin_access (
#                 admin_id TEXT,
#                 grade INTEGER,
#                 class TEXT,
#                 region TEXT,
#                 PRIMARY KEY (admin_id, grade, class, region),
#                 FOREIGN KEY (admin_id) REFERENCES admins(id) ON DELETE CASCADE
#             )
#         ''')

#     def _populate_tables_from_json(self, cursor: sqlite3.Cursor, json_path: str):
#         """Reads the JSON file and inserts data into the appropriate tables."""
#         with open(json_path, 'r') as f:
#             data = json.load(f)

#         # A mapping from JSON keys to table names and column orders
#         # This makes the population logic clean and easy to extend
#         simple_mappings = {
#             "students": ("students", ["id", "name", "grade", "class", "region"]),
#             "classes": ("classes", ["id", "grade", "class", "teacher"]),
#             "exams": ("exams", ["id", "subject", "date", "grade", "class"]),
#             "assignments": ("assignments", ["id", "title", "due_date", "grade", "class"]),
#             "quizzes": ("quizzes", ["id", "title", "scheduled_date", "grade", "class"]),
#             "submissions": ("submissions", ["student_id", "assignment_id", "submitted", "submission_date", "score"]),
#         }

#         # Handle simple, direct-mapping tables first
#         for key, (table, columns) in simple_mappings.items():
#             if key in data:
#                 records = data[key]
#                 if not records: continue
                
#                 print(f"  - Populating '{table}' table...")
#                 placeholders = ", ".join(["?"] * len(columns))
#                 sql = f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                
#                 # Convert list of dicts to list of tuples
#                 tuple_data = [[record.get(col) for col in columns] for record in records]
#                 cursor.executemany(sql, tuple_data)

#         # Handle the complex 'admins' case separately
#         if "admins" in data and data["admins"]:
#             print("  - Populating 'admins' and 'admin_access' tables...")
            
#             # 1. Populate the main 'admins' table
#             admin_info = [(admin['id'], admin['name']) for admin in data['admins']]
#             cursor.executemany("INSERT OR REPLACE INTO admins (id, name) VALUES (?, ?)", admin_info)

#             # 2. Expand admin scopes into the 'admin_access' table
#             access_rows = []
#             for admin in data['admins']:
#                 for grade in admin.get("grades", []):
#                     for class_name in admin.get("classes", []):
#                         access_rows.append((admin['id'], grade, class_name, admin.get("region")))
            
#             cursor.executemany(
#                 "INSERT OR REPLACE INTO admin_access (admin_id, grade, class, region) VALUES (?, ?, ?, ?)",
#                 access_rows
#             )


import sqlite3
import json
import os
from typing import List, Optional

class DatabaseManager:
    """
    Manages the creation, setup, and description of the school's SQLite database
    based on a direct mapping from a JSON file.
    """

    def __init__(self, db_path: str = "school_management_v2.db"):
        """Initializes the DatabaseManager."""
        self.db_path = db_path

    def setup_database_from_json(self, json_path: str, overwrite: bool = True):
        """
        The main public method to create and populate the database from a JSON file.

        Args:
            json_path (str): The path to the source JSON file.
            overwrite (bool): If True, deletes the existing database file to start fresh.
        """
        if overwrite and os.path.exists(self.db_path):
            os.remove(self.db_path)
            print(f"Removed existing database at '{self.db_path}'.")

        if not os.path.exists(json_path):
            print(f"Error: JSON file not found at '{json_path}'. Aborting.")
            return

        print(f"Database will be created at: {os.path.abspath(self.db_path)}")
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;") # Enforce foreign key constraints
        cursor = conn.cursor()

        try:
            print("\nSTEP 1: Creating database tables based on JSON structure...")
            self._create_tables(cursor)
            print("Tables created successfully.")

            print(f"\nSTEP 2: Populating database from '{json_path}'...")
            self._populate_tables_from_json(cursor, json_path)
            print("Data population complete.")

            conn.commit()
            print("\nDatabase setup successful. All changes have been committed.")

        except Exception as e:
            print(f"An error occurred during database setup: {e}")
            conn.rollback()
        finally:
            conn.close()

    def _create_tables(self, cursor: sqlite3.Cursor):
        """Defines and executes the SQL for creating all tables."""

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                grade INTEGER,
                class TEXT,
                region TEXT
            )
        ''')
        
        # Simplified admins table directly mapping to the new JSON structure
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                grade INTEGER,    -- Renamed from 'grades' for clarity
                class TEXT,     -- Renamed from 'classes' for clarity
                region TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS classes (
                id TEXT PRIMARY KEY,
                grade INTEGER,
                class TEXT,
                teacher TEXT,
                UNIQUE(grade, class)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exams (
                id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                date DATE,
                grade INTEGER,
                class TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                due_date DATE,
                grade INTEGER,
                class TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quizzes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                scheduled_date DATE,
                grade INTEGER,
                class TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS submissions (
                student_id TEXT,
                assignment_id TEXT,
                submitted BOOLEAN,
                submission_date DATE,
                score INTEGER,
                PRIMARY KEY (student_id, assignment_id),
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
                FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE
            )
        ''')

    def _populate_tables_from_json(self, cursor: sqlite3.Cursor, json_path: str):
        """Reads the JSON file and inserts data using a unified mapping."""
        with open(json_path, 'r') as f:
            data = json.load(f)

        # A unified mapping from JSON keys to table names and column orders.
        # This makes the population logic clean and easy to extend.
        mappings = {
            "students": ("students", ["id", "name", "grade", "class", "region"]),
            # The 'admins' key now maps directly to the 'admins' table
            "admins": ("admins", ["id", "name", "grades", "classes", "region"]),
            "classes": ("classes", ["id", "grade", "class", "teacher"]),
            "exams": ("exams", ["id", "subject", "date", "grade", "class"]),
            "assignments": ("assignments", ["id", "title", "due_date", "grade", "class"]),
            "quizzes": ("quizzes", ["id", "title", "scheduled_date", "grade", "class"]),
            "submissions": ("submissions", ["student_id", "assignment_id", "submitted", "submission_date", "score"]),
        }

        for json_key, (table_name, json_columns) in mappings.items():
            if json_key in data and data[json_key]:
                print(f"  - Populating '{table_name}' table...")
                records = data[json_key]

                # Map JSON columns to database columns (handling 'grades' -> 'grade')
                db_columns = [col.replace('grades', 'grade').replace('classes', 'class') for col in json_columns]
                
                placeholders = ", ".join(["?"] * len(db_columns))
                sql = f"INSERT OR REPLACE INTO {table_name} ({', '.join(db_columns)}) VALUES ({placeholders})"
                
                # Create a list of tuples with data in the correct order
                tuple_data = [[record.get(col) for col in json_columns] for record in records]
                cursor.executemany(sql, tuple_data)


    def get_schema_representation(self, custom_rules: Optional[List[str]] = None) -> str:
        """
        Inspects the database and generates a formatted string of its schema,
        relationships, and custom rules, suitable for an LLM prompt.
        """
        if not os.path.exists(self.db_path):
            return "Error: Database file not found."

        output = ["Database Schema:", ""]
        all_foreign_keys = []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = sorted([row[0] for row in cursor.fetchall()])

            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [row[1] for row in cursor.fetchall()]
                output.append(f"{table}: {', '.join(columns)}")

                cursor.execute(f"PRAGMA foreign_key_list({table})")
                f_keys = cursor.fetchall()
                for key in f_keys:
                    all_foreign_keys.append(f"- {table}.{key[3]} → {key[2]}.{key[4]}")

        if all_foreign_keys:
            output.append("\nKey relationships:")
            output.extend(sorted(all_foreign_keys))

        if custom_rules:
            output.append("")
            output.extend(custom_rules)

        return "\n".join(output)