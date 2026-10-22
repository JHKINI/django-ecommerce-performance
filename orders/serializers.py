
from django.db import transaction
from django.db.models import F
from rest_framework import serializers

from orders.models import Order, OrderItem
from products.models import Product


class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source="product",
    )

    class Meta:
        model = OrderItem
        fields = ["product_id", "quantity", "price"]
        read_only_fields = ["price"]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "주문 수량은 1개 이상이어야 합니다."
            )
        return value


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ["id", "user", "created_at", "status", "items"]
        read_only_fields = ["user", "created_at", "status"]

    @transaction.atomic
    def create(self, validated_data):
        items_data = validated_data.pop("items")
        user = self.context["request"].user

        # 동일 상품이 여러 항목에 등장하면 수량을 합산해 검증한다.
        quantities = {}
        products = {}

        for item_data in items_data:
            product = item_data["product"]
            quantity = item_data["quantity"]

            product_id = product.pk
            quantities[product_id] = (
                quantities.get(product_id, 0) + quantity
            )
            products[product_id] = product

        # 상품 ID 순으로 처리해 여러 상품 주문 시 잠금 충돌 가능성을 줄인다.
        for product_id in sorted(quantities):
            quantity = quantities[product_id]

            updated = Product.objects.filter(
                pk=product_id,
                stock__gte=quantity,
            ).update(
                stock=F("stock") - quantity
            )

            if updated == 0:
                raise serializers.ValidationError({
                    "items": (
                        f"상품 ID {product_id}의 재고가 부족하거나 "
                        "상품을 찾을 수 없습니다."
                    )
                })

            # 주문 당시 가격을 DB에서 다시 읽는다.
            products[product_id] = Product.objects.get(pk=product_id)

        order = Order.objects.create(
            user=user,
            **validated_data,
        )

        for item_data in items_data:
            product = products[item_data["product"].pk]

            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item_data["quantity"],
                price=product.price,
            )

        return order
