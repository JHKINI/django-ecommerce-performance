
import os
import time
import statistics

os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings_test"

import django
django.setup()

from products.models import Product
from products.serializers import ProductSerializer
from rest_framework.renderers import JSONRenderer

# 1. ORM 조회 시간
query_times = []
objects = None

for _ in range(4):
    start = time.perf_counter()
    objects = list(Product.objects.all().order_by("-created_at"))
    elapsed = (time.perf_counter() - start) * 1000
    query_times.append(elapsed)

# 2. Serializer 처리 시간
serializer_times = []
serialized_data = None

for _ in range(4):
    start = time.perf_counter()
    serialized_data = ProductSerializer(objects, many=True).data
    elapsed = (time.perf_counter() - start) * 1000
    serializer_times.append(elapsed)

# 3. JSON 렌더링 시간
render_times = []
json_bytes = None

for _ in range(4):
    start = time.perf_counter()
    json_bytes = JSONRenderer().render(serialized_data)
    elapsed = (time.perf_counter() - start) * 1000
    render_times.append(elapsed)

print(f"상품 수: {len(objects):,}건")
print(f"ORM 조회 평균: {statistics.mean(query_times[1:]):.2f} ms")
print(f"Serializer 평균: {statistics.mean(serializer_times[1:]):.2f} ms")
print(f"JSON 렌더링 평균: {statistics.mean(render_times[1:]):.2f} ms")
print(f"JSON 크기: {len(json_bytes):,} bytes")
