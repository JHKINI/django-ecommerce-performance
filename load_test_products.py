
import csv
import os
from decimal import Decimal
from pathlib import Path

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings_test"

import django
django.setup()

from django.utils import timezone
from django.utils.dateparse import parse_datetime
from products.models import Product

CSV_PATH = Path(__file__).parent / "synthetic_products_100k.csv"
BATCH_SIZE = 2000

products = []

with CSV_PATH.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:
        created_at = parse_datetime(row["created_at"])

        if created_at and timezone.is_naive(created_at):
            created_at = timezone.make_aware(created_at)

        products.append(
            Product(
                name=row["name"],
                price=Decimal(row["price"]),
                stock=int(row["stock"]),
                created_at=created_at,
            )
        )

        if len(products) >= BATCH_SIZE:
            Product.objects.bulk_create(
                products,
                batch_size=BATCH_SIZE,
            )
            products.clear()

if products:
    Product.objects.bulk_create(
        products,
        batch_size=BATCH_SIZE,
    )

print("적재 완료")
print(f"테스트 DB 상품 수: {Product.objects.count():,}건")
