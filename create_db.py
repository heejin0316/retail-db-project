import argparse
import sqlite3
from pathlib import Path

def create_database(schema_path: Path, db_path: Path, reset: bool=False) -> None:
    """Create a SQLite database from a schema.sql file"""
    
    if not schema_path.exists():
        raise FileNotFoundError(f"schema file not found: {schema_path}")
    
    if reset and db_path.exists():
        db_path.unlink()
        print(f"[RESET] removed existing database: {db_path}")
        
    
    schema_sql = schema_path.read_text(encoding="utf-8")
    
    try:
        with sqlite3.connect(db_path) as conn:
            # SQLite는 연결할 때마다 foreign key 활성화가 필요함
            conn.execute("PRAGMA foreign_keys=ON;")    # 기본적으로 sqlite에서 외래키 검사를 항상 자동적으로 강제 안함.
            
            # schema.sql 안의 CREATE TABLE, CREATE INDEX 전체 실행
            conn.executescript(schema_sql)
            conn.commit()
            
            tables=conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                    AND name NOT LIKE 'sqlite_%'
                ORDER BY name;
                """
            ).fetchall()
            
            indexes = conn.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type='index'
                    AND name NOT LIKE 'sqlite_%'
                ORDER BY name;
                """
            ).fetchall()
            print(f"[OK] database created: {db_path}")
            print(f"[OK] tables({len(tables)}): {', '.join(name for (name,) in tables)}")
            print(f"[OK] indexes ({len(indexes)}): {','.join(name for (name,) in indexes)}")
            
    except sqlite3.Error as e:
        raise RuntimeError(f"SQLite error while creating database: {e}") from e
    
def main() -> None:
    parser = argparse.ArgumentParser(description="Create SQLite database from schema.sql")
    parser.add_argument("--schema", default="schema.sql", help="Path to schema.sql")
    parser.add_argument("--db", default="market.db", help="Output SQLite DB file")
    parser.add_argument("--reset", action="store_true", help="Delete existing DB file before creating")
    
    args = parser.parse_args()
    
    create_database(Path(args.schema), Path(args.db), args.reset)
    
if __name__ == "__main__":
    main()