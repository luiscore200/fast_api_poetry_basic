import sqlite3
from typing import Optional, List, Dict, Any

class SQLiteProvider:
    _instance: Optional["SQLiteProvider"] = None

    def __new__(cls, db_path: str = "articles.db"):
        if cls._instance is None:
            cls._instance = super(SQLiteProvider, cls).__new__(cls)
            cls._instance.db_path = db_path
            cls._instance._create_tables()
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _create_tables(self):
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tittle TEXT NOT NULL,
                    content TEXT NOT NULL
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS article_tags (
                    article_id INTEGER,
                    tag_id INTEGER,
                    PRIMARY KEY (article_id, tag_id),
                    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS article_categories (
                    article_id INTEGER,
                    category_id INTEGER,
                    PRIMARY KEY (article_id, category_id),
                    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
                );
            """)
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error al crear/verificar tablas de SQLite: {e}")
            conn.rollback()
        finally:
            conn.close()

    def execute_query(self, query: str, params: Optional[tuple] = None) -> None:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error ejecutando query: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def fetch_one(self, query: str, params: Optional[tuple] = None) -> Optional[tuple]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchone()
        except sqlite3.Error as e:
            print(f"Error en fetch_one: {e}")
            raise
        finally:
            conn.close()

    def fetch_all(self, query: str, params: Optional[tuple] = None) -> List[tuple]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error en fetch_all: {e}")
            raise
        finally:
            conn.close()

    def insert(self, table: str, data: Dict[str, Any]) -> int:
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        values = tuple(data.values())
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders});"
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error en insert: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    def update(self, table: str, updates: Dict[str, Any], where: Dict[str, Any]) -> None:
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])
        values = list(updates.values()) + list(where.values())
        query = f"UPDATE {table} SET {set_clause} WHERE {where_clause}"
        self.execute_query(query, tuple(values))

    def delete(self, table: str, where: Dict[str, Any]) -> None:
        where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])
        values = tuple(where.values())
        query = f"DELETE FROM {table} WHERE {where_clause}"
        self.execute_query(query, values)

    def find(self, table: str, where: Optional[Dict[str, Any]] = None) -> List[tuple]:
        if where:
            where_clause = ' AND '.join([f"{k} = ?" for k in where.keys()])
            values = tuple(where.values())
            query = f"SELECT * FROM {table} WHERE {where_clause}"
            return self.fetch_all(query, values)
        else:
            query = f"SELECT * FROM {table}"
            return self.fetch_all(query)
