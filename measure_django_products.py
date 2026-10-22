
import os
import time
import statistics

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings_test"

import django
django.setup()

from django.test import Client
from django.db import connection
from django.test.utils import CaptureQueriesContext

client = Client(HTTP_HOST="127.0.0.1")

total_times = []
sql_times = []
response_size = 0

# 첫 요청은 워밍업
for i in range(4):
    start = time.perf_counter()

    with CaptureQueriesContext(connection) as queries:
        response = client.get("/api/products/")

    elapsed_ms = (time.perf_counter() - start) * 1000
    sql_ms = sum(float(q["time"]) * 1000 for q in queries.captured_queries)

    if response.status_code != 200:
        print("HTTP 상태:", response.status_code)
        print(response.content[:500])
        raise SystemExit("API 요청 실패")

    response_size = len(response.content)

    if i > 0:
        total_times.append(elapsed_ms)
        sql_times.append(sql_ms)

print("측정 방식: Django 테스트 클라이언트 (HTTP 네트워크 제외)")
print("측정 횟수:", len(total_times))
print(f"평균 Django 요청 시간: {statistics.mean(total_times):.2f} ms")
print(f"평균 SQL 시간 합계: {statistics.mean(sql_times):.2f} ms")
print(f"평균 응답 크기: {response_size:,} bytes")
print(f"응답 크기: {response_size / 1024 / 1024:.2f} MiB")
