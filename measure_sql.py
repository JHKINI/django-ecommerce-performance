import os
import django

# 1. Django 설정 초기화
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

# 2. Django 설정 초기화 이후에 import
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient


# 3. API 인증 설정
client = APIClient(HTTP_HOST="localhost")

access_token = "docs: complete project README and validation results"

client.credentials(
    HTTP_AUTHORIZATION=f"Bearer {access_token}"
)


# 4. 주문 요청 데이터
payload = {
    "items": [
        {
            "product_id": 1,
            "quantity": 1,
        }
    ]
}


# 5. SQL 쿼리 측정
with CaptureQueriesContext(connection) as queries:
    response = client.post(
        "/api/orders/",
        payload,
        format="json",
    )


# 6. 결과 출력
print("HTTP 상태 코드:", response.status_code)
print("SQL 쿼리 수:", len(queries))

total_sql_time = sum(
    float(query["time"])
    for query in queries
)

print(f"SQL 실행 시간 합계: {total_sql_time:.6f}초")

for index, query in enumerate(queries, start=1):
    print(f"\n[{index}] 실행 시간: {query['time']}초")
    print(query["sql"])