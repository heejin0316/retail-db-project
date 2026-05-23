import argparse
import sqlite3
import time
from datetime import datetime
from pathlib import Path


EXPECTED_QUERY_COUNT = 5
MAX_PREVIEW_ROWS = 5


def split_queries(sql_text):
    queries = []
    current_title = None
    current_lines = []

    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("-- Query "):
            if current_lines:
                queries.append((current_title or f"Query {len(queries) + 1}", "\n".join(current_lines).strip()))
                current_lines = []
            current_title = stripped[3:].strip()
            continue

        current_lines.append(line)

    if current_lines and "\n".join(current_lines).strip():
        queries.append((current_title or f"Query {len(queries) + 1}", "\n".join(current_lines).strip()))

    return [(title, sql.rstrip().rstrip(";")) for title, sql in queries]


def execute_query(conn, sql):
    start = time.perf_counter()
    cursor = conn.execute(sql)
    columns = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    elapsed_ms = (time.perf_counter() - start) * 1000
    return columns, rows, elapsed_ms


def is_sorted_desc(values):
    return all(values[i] >= values[i + 1] for i in range(len(values) - 1))


def validate_result(query_index, columns, rows):
    messages = []
    passed = True

    if not rows:
        passed = False
        messages.append("결과가 비어 있음")

    if query_index == 1:
        required = {"store_id", "store_name", "product_id", "product_name", "total_quantity"}
        passed &= required.issubset(columns)
        if not required.issubset(columns):
            messages.append("필수 컬럼 누락")
        null_count = sum(1 for row in rows if row[1] is None or row[3] is None)
        if null_count:
            passed = False
            messages.append(f"매장명 또는 제품명 NULL {null_count}건")

    elif query_index == 2:
        required = {"campus_area", "product_id", "product_name", "total_quantity"}
        passed &= required.issubset(columns)
        if not required.issubset(columns):
            messages.append("필수 컬럼 누락")
        null_count = sum(1 for row in rows if row[0] is None or row[2] is None)
        if null_count:
            passed = False
            messages.append(f"캠퍼스 구역 또는 제품명 NULL {null_count}건")

    elif query_index == 3:
        amounts = [row[2] for row in rows]
        if len(rows) > 5:
            passed = False
            messages.append("결과가 5행을 초과함")
        if not is_sorted_desc(amounts):
            passed = False
            messages.append("판매 실적 내림차순 정렬 아님")

    elif query_index == 4:
        if len(rows) != 1:
            passed = False
            messages.append("COUNT 쿼리 결과가 1행이 아님")
        elif rows[0][0] is None or rows[0][0] < 0:
            passed = False
            messages.append("store_count가 0 이상 정수가 아님")

    elif query_index == 5:
        quantities = [row[2] for row in rows]
        if len(rows) > 5:
            passed = False
            messages.append("결과가 5행을 초과함")
        if not is_sorted_desc(quantities):
            passed = False
            messages.append("우유 판매량 내림차순 정렬 아님")

    if not messages:
        messages.append("기본 검증 통과")

    return passed, messages


def format_value(value):
    if value is None:
        return "NULL"
    return str(value)


def markdown_table(columns, rows):
    if not rows:
        return "_결과 없음_"

    preview_rows = rows[:MAX_PREVIEW_ROWS]
    header = "| " + " | ".join(columns) + " |"
    divider = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| " + " | ".join(format_value(value) for value in row) + " |"
        for row in preview_rows
    ]
    return "\n".join([header, divider, *body])


def write_results(output_path, db_path, sql_path, results):
    lines = [
        "# Query Test Results",
        "",
        f"- 실행 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- DB 파일: `{db_path}`",
        f"- SQL 파일: `{sql_path}`",
        f"- 전체 쿼리 수: {len(results)}",
        "",
    ]

    all_passed = all(result["passed"] for result in results)
    lines.extend([
        "## Summary",
        "",
        f"- 전체 검증 결과: {'PASS' if all_passed else 'FAIL'}",
        "",
        "| Query | 실행 결과 | 행 개수 | 실행 시간(ms) | 검증 메시지 |",
        "| --- | --- | ---: | ---: | --- |",
    ])

    for result in results:
        lines.append(
            f"| {result['title']} | {'PASS' if result['passed'] else 'FAIL'} | "
            f"{result['row_count']} | {result['elapsed_ms']:.3f} | "
            f"{'; '.join(result['messages'])} |"
        )

    for result in results:
        lines.extend([
            "",
            f"## {result['title']}",
            "",
            f"- 실행 결과: {'PASS' if result['passed'] else 'FAIL'}",
            f"- 행 개수: {result['row_count']}",
            f"- 실행 시간: {result['elapsed_ms']:.3f} ms",
            f"- 검증 메시지: {'; '.join(result['messages'])}",
            "",
            "### Result Preview",
            "",
            markdown_table(result["columns"], result["rows"]),
        ])

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run and validate sample SQL queries.")
    parser.add_argument("--db", default="market.db", help="SQLite database path")
    parser.add_argument("--sql", default="queries/sample_queries.sql", help="Sample query SQL path")
    parser.add_argument("--out", default="queries/query_results.md", help="Markdown result output path")
    args = parser.parse_args()

    db_path = Path(args.db)
    sql_path = Path(args.sql)
    output_path = Path(args.out)

    if not db_path.exists():
        raise FileNotFoundError(f"DB file not found: {db_path}")
    if not sql_path.exists():
        raise FileNotFoundError(f"SQL file not found: {sql_path}")

    queries = split_queries(sql_path.read_text(encoding="utf-8"))
    if len(queries) != EXPECTED_QUERY_COUNT:
        raise RuntimeError(f"expected {EXPECTED_QUERY_COUNT} queries, found {len(queries)}")

    results = []
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
        if fk_errors:
            raise RuntimeError(f"foreign key errors: {fk_errors}")

        for index, (title, sql) in enumerate(queries, 1):
            columns, rows, elapsed_ms = execute_query(conn, sql)
            passed, messages = validate_result(index, columns, rows)
            results.append(
                {
                    "title": title,
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "elapsed_ms": elapsed_ms,
                    "passed": passed,
                    "messages": messages,
                }
            )

    write_results(output_path, db_path, sql_path, results)

    for result in results:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"[{status}] {result['title']} rows={result['row_count']} time={result['elapsed_ms']:.3f}ms")
    print(f"[OK] results written: {output_path}")


if __name__ == "__main__":
    main()
