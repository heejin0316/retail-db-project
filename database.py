import os
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
LOCAL_DB_PATH = BASE_DIR / os.environ.get("LOCAL_DB_PATH", "market.db")


class CompatRow:
    def __init__(self, columns, values):
        self._columns = list(columns)
        self._values = list(values)
        self._by_name = dict(zip(self._columns, self._values))

    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._by_name[key]

    def __getattr__(self, key):
        try:
            return self._by_name[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def keys(self):
        return self._columns


class CompatCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.description = getattr(cursor, "description", None)
        self._columns = self._extract_columns()

    def _extract_columns(self):
        if not self.description:
            return []
        columns = []
        for item in self.description:
            columns.append(item[0] if isinstance(item, (tuple, list)) else item)
        return columns

    def _wrap_row(self, row):
        if row is None or not self._columns:
            return row
        if isinstance(row, CompatRow):
            return row
        if isinstance(row, dict):
            return CompatRow(self._columns, [row[column] for column in self._columns])
        return CompatRow(self._columns, row)

    def fetchone(self):
        return self._wrap_row(self._cursor.fetchone())

    def fetchall(self):
        return [self._wrap_row(row) for row in self._cursor.fetchall()]

    def __iter__(self):
        for row in self._cursor:
            yield self._wrap_row(row)

    def __getattr__(self, key):
        return getattr(self._cursor, key)


class CompatConnection:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, *args, **kwargs):
        return CompatCursor(self._conn.execute(*args, **kwargs))

    def executemany(self, *args, **kwargs):
        return self._conn.executemany(*args, **kwargs)

    def commit(self):
        return self._conn.commit()

    def rollback(self):
        return self._conn.rollback()

    def close(self):
        return self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()

    def __getattr__(self, key):
        return getattr(self._conn, key)


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
        conn = CompatConnection(conn)
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
