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
                queries.append(
                    (current_title or f"Query {len(queries) + 1}", "\n".join(current_lines).strip())
                )
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
        if not required.issubset(columns):
            passed = False
            messages.append("필수 컬럼 누락")

    elif query_index == 2:
        required = {"campus_area", "product_id", "product_name", "total_quantity"}
        if not required.issubset(columns):
            passed = False
            messages.append("필수 컬럼 누락")

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


def run_sample_queries(conn, sql_path):
    queries = split_queries(Path(sql_path).read_text(encoding="utf-8"))
    if len(queries) != EXPECTED_QUERY_COUNT:
        raise RuntimeError(f"expected {EXPECTED_QUERY_COUNT} queries, found {len(queries)}")

    results = []
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
    return results


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


def results_to_markdown(results, db_label, sql_path):
    lines = [
        "# Query Test Results",
        "",
        f"- 실행 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- DB: `{db_label}`",
        f"- SQL 파일: `{sql_path}`",
        f"- 전체 쿼리 수: {len(results)}",
        "",
    ]

    all_passed = all(result["passed"] for result in results)
    lines.extend(
        [
            "## Summary",
            "",
            f"- 전체 검증 결과: {'PASS' if all_passed else 'FAIL'}",
            "",
            "| Query | 실행 결과 | 행 개수 | 실행 시간(ms) | 검증 메시지 |",
            "| --- | --- | ---: | ---: | --- |",
        ]
    )

    for result in results:
        lines.append(
            f"| {result['title']} | {'PASS' if result['passed'] else 'FAIL'} | "
            f"{result['row_count']} | {result['elapsed_ms']:.3f} | "
            f"{'; '.join(result['messages'])} |"
        )

    for result in results:
        lines.extend(
            [
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
            ]
        )

    return "\n".join(lines) + "\n"

