
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import serializers

from orders.models import Order, OrderItem
from orders.serializers import OrderSerializer
from products.models import Product
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import close_old_connections, connections
from django.test import TransactionTestCase


class OrderProblemDiagnosisTests(TestCase):
    """현재 주문 처리 로직의 문제를 재현하는 테스트."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
            password="Testpass123!",
        )

        self.product = Product.objects.create(
            name="테스트 상품",
            price="10000.00",
            stock=5,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_order_is_rolled_back_when_item_creation_fails(self):
        """주문 상세 저장 실패 시 주문 본문도 롤백되어야 한다."""
        from types import SimpleNamespace

        serializer = OrderSerializer(
            data={
                "items": [
                    {
                        "product_id": self.product.id,
                        "quantity": 1,
                        "price": "10000.00",
                    }
                ]
            },
            context={"request": SimpleNamespace(user=self.user)},
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

        with patch(
            "orders.serializers.OrderItem.objects.create",
            side_effect=RuntimeError("주문 상세 저장 실패"),
        ):
            with self.assertRaises(RuntimeError):
                serializer.save()

        self.assertEqual(
            Order.objects.count(),
            0,
            "주문 상세 저장 실패 후 주문 데이터가 남아 있습니다.",
        )

    def test_client_cannot_set_arbitrary_order_price(self):
        """주문 가격은 클라이언트 입력이 아니라 서버 상품 가격을 따라야 한다."""
        response = self.client.post(
            "/api/orders/",
            {
                "items": [
                    {
                        "product_id": self.product.id,
                        "quantity": 1,
                        "price": "1.00",
                    }
                ]
            },
            format="json",
        )


        if response.status_code in (200, 201):
            item = OrderItem.objects.get()
            self.assertEqual(
                item.price,
                Decimal(str(self.product.price)),
                "클라이언트가 보낸 가격이 주문 가격으로 저장되었습니다.",
            )
        else:
            self.assertEqual(
                response.status_code,
                400,
                response.content.decode(),
            )

    def test_order_is_rejected_when_stock_is_insufficient(self):
        """재고보다 많은 수량의 주문은 거절되어야 한다."""
        response = self.client.post(
            "/api/orders/",
            {
                "items": [
                    {
                        "product_id": self.product.id,
                        "quantity": 6,
                        "price": "10000.00",
                    }
                ]
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            400,
            f"재고 부족 주문이 거절되지 않았습니다. 응답: {response.status_code}",
        )

        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

class OrderConcurrencyTests(TransactionTestCase):
    """재고 1개에 동시 주문 20건을 보내 재고 정합성을 검증한다."""

    reset_sequences = True

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="concurrent_user",
            password="Testpass123!",
        )

        self.product = Product.objects.create(
            name="동시 주문 테스트 상품",
            price="10000.00",
            stock=1,
        )

    def submit_order(self, barrier):
        close_old_connections()

        try:
            user = get_user_model().objects.get(pk=self.user.pk)
            product = Product.objects.get(pk=self.product.pk)

            barrier.wait(timeout=10)

            serializer = OrderSerializer(
                data={
                    "items": [
                        {
                            "product_id": product.pk,
                            "quantity": 1,
                        }
                    ]
                },
                context={
                    "request": type(
                        "Request",
                        (),
                        {"user": user},
                    )()
                },
            )

            if not serializer.is_valid():
                return False

            try:
                serializer.save()
                return True
            except serializers.ValidationError:
                return False

        finally:
            connections.close_all()

    def test_only_one_order_succeeds_when_stock_is_one(self):
        request_count = 20
        barrier = Barrier(request_count)

        with ThreadPoolExecutor(max_workers=request_count) as executor:
            results = list(
                executor.map(
                    lambda _: self.submit_order(barrier),
                    range(request_count),
                )
            )

        self.product.refresh_from_db()

        self.assertEqual(
            sum(results),
            1,
            f"성공 주문은 1건이어야 합니다. 실제 성공: {sum(results)}",
        )

        self.assertEqual(
            self.product.stock,
            0,
            f"최종 재고는 0이어야 합니다. 실제 재고: {self.product.stock}",
        )

        self.assertEqual(
            Order.objects.filter(user=self.user).count(),
            1,
        )
