import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from products.models import Product
from orders.models import Order, OrderItem

# 기존 DB 상태 기록
product = Product.objects.get(pk=1)
stock_before = product.stock
orders_before = Order.objects.count()
items_before = OrderItem.objects.count()

print("테스트 전 재고:", stock_before)
print("테스트 전 주문 수:", orders_before)
print("테스트 전 주문 상세 수:", items_before)

# 테스트용 API 클라이언트
client = APIClient(HTTP_HOST="localhost")

# 테스트용 API 클라이언트
client = APIClient(HTTP_HOST="localhost")

access_token = "docs: complete project README and validation results"

client.credentials(
    HTTP_AUTHORIZATION=f"Bearer {access_token}"
)

# 현재 재고보다 1개 더 많이 주문
payload = {
    "items": [
        {
            "product_id": 1,
            "quantity": stock_before + 1,
        }
    ]
}

response = client.post(
    "/api/orders/",
    payload,
    format="json",
)

# 테스트 후 DB 상태 확인
product.refresh_from_db()
stock_after = product.stock
orders_after = Order.objects.count()
items_after = OrderItem.objects.count()

print("\nHTTP 상태 코드:", response.status_code)
print("응답 내용:", response.data)
print("테스트 후 재고:", stock_after)
print("테스트 후 주문 수:", orders_after)
print("테스트 후 주문 상세 수:", items_after)

print("\n--- 검증 결과 ---")
print("재고 유지:", stock_before == stock_after)
print("주문 수 유지:", orders_before == orders_after)
print("주문 상세 수 유지:", items_before == items_after)