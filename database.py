import os
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
LOCAL_DB_PATH = BASE_DIR / os.environ.get("LOCAL_DB_PATH", "market.db")


def using_remote_database():
    return bool(os.environ.get("TURSO_DATABASE_URL"))


def get_connection(create_local=False):
    if os.environ.get("VERCEL") and not using_remote_database():
        raise RuntimeError(
            "Vercel 배포 환경에서는 TURSO_DATABASE_URL과 TURSO_AUTH_TOKEN을 설정해야 합니다."
        )

    if using_remote_database():
        if not os.environ.get("TURSO_AUTH_TOKEN"):
            raise RuntimeError("TURSO_AUTH_TOKEN 환경변수가 설정되어 있지 않습니다.")
        try:
            import libsql
        except ImportError as exc:
            raise RuntimeError(
                "Turso DB를 사용하려면 `pip install libsql`을 먼저 실행해야 합니다."
            ) from exc

        conn = libsql.connect(
            database=os.environ["TURSO_DATABASE_URL"],
            auth_token=os.environ.get("TURSO_AUTH_TOKEN"),
        )
    else:
        if not LOCAL_DB_PATH.exists() and not create_local:
            raise FileNotFoundError(
                "market.db 파일이 없습니다. 먼저 `python seed_data.py --reset --db market.db`를 실행하세요."
            )
        conn = sqlite3.connect(LOCAL_DB_PATH)
        conn.execute("PRAGMA journal_mode = MEMORY")
        conn.execute("PRAGMA temp_store = MEMORY")

    if hasattr(conn, "row_factory"):
        conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def split_sql_script(sql_text):
    statements = []
    current = []

    for line in sql_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(current).strip().rstrip(";").strip()
            if statement:
                statements.append(statement)
            current = []

    tail = "\n".join(current).strip()
    if tail:
        statements.append(tail.rstrip(";"))
    return statements


def execute_schema(conn, schema_path):
    sql_text = Path(schema_path).read_text(encoding="utf-8")
    for statement in split_sql_script(sql_text):
        if statement.upper().startswith("PRAGMA"):
            continue
        conn.execute(statement)
