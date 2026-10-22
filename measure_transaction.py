import os
import time
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from orders.serializers import OrderSerializer


# 기존 create 메서드를 보관
original_create = OrderSerializer.create

# 측정 결과 저장
transaction_times = []


def measured_create(self, validated_data):
    start = time.perf_counter()

    try:
        # 기존 주문 생성 로직 그대로 실행
        return original_create(self, validated_data)
    finally:
        elapsed = time.perf_counter() - start
        transaction_times.append(elapsed)


# 측정 중에만 메서드를 감싸서 시간 기록
OrderSerializer.create = measured_create

try:
    client = APIClient(HTTP_HOST="localhost")

    access_token = "docs: complete project README and validation results"

    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {access_token}"
    )

    payload = {
        "items": [
            {
                "product_id": 1,
                "quantity": 1,
            }
        ]
    }

    with CaptureQueriesContext(connection) as queries:
        request_start = time.perf_counter()

        response = client.post(
            "/api/orders/",
            payload,
            format="json",
        )

        request_elapsed = time.perf_counter() - request_start

    print("HTTP 상태 코드:", response.status_code)
    print(f"API 요청 소요 시간: {request_elapsed:.6f}초")
    print("SQL 쿼리 수:", len(queries))

    sql_time = sum(float(query["time"]) for query in queries)
    print(f"SQL 실행 시간 합계: {sql_time:.6f}초")

    if transaction_times:
        print(
            "주문 생성 메서드 소요 시간:",
            f"{transaction_times[0]:.6f}초",
        )
    else:
        print("주문 생성 메서드가 호출되지 않았습니다.")

finally:
    # 측정 후 원래 메서드로 복구
    OrderSerializer.create = original_create