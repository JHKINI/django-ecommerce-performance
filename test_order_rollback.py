import os
import django
from unittest.mock import patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from rest_framework.test import APIClient
from products.models import Product
from orders.models import Order, OrderItem

# 1. 테스트 전 DB 상태 기록
product = Product.objects.get(pk=1)

stock_before = product.stock
orders_before = Order.objects.count()
items_before = OrderItem.objects.count()

print("=== 테스트 전 ===")
print("재고:", stock_before)
print("주문 수:", orders_before)
print("주문 상세 수:", items_before)

# 2. API 인증
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

# 3. 주문 생성 단계에서 테스트용 오류 발생
try:
    with patch(
        "orders.serializers.Order.objects.create",
        side_effect=RuntimeError("테스트용 오류"),
    ):
        response = client.post(
            "/api/orders/",
            payload,
            format="json",
        )
        print("HTTP 상태 코드:", response.status_code)

except RuntimeError as exc:
    print("예상된 테스트 오류:", exc)

# 4. 테스트 후 DB 상태 재조회
product.refresh_from_db()

stock_after = product.stock
orders_after = Order.objects.count()
items_after = OrderItem.objects.count()

print("\n=== 테스트 후 ===")
print("재고:", stock_after)
print("주문 수:", orders_after)
print("주문 상세 수:", items_after)

# 5. 검증 결과
print("\n=== 검증 결과 ===")
print("재고 롤백:", stock_before == stock_after)
print("주문 수 유지:", orders_before == orders_after)
print("주문 상세 수 유지:", items_before == items_after)
