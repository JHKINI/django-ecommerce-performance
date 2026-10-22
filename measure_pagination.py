
import statistics
import time

import requests

URL = "http://127.0.0.1:8001/api/products/?page_size=50"
WARMUP = 2
REPEATS = 10

# 준비 요청
for _ in range(WARMUP):
    response = requests.get(URL, timeout=30)
    response.raise_for_status()

times_ms = []
sizes_bytes = []
product_counts = []

for _ in range(REPEATS):
    start = time.perf_counter()
    response = requests.get(URL, timeout=30)
    elapsed_ms = (time.perf_counter() - start) * 1000

    response.raise_for_status()
    data = response.json()

    times_ms.append(elapsed_ms)
    sizes_bytes.append(len(response.content))
    product_counts.append(len(data["results"]))

print("측정 횟수:", REPEATS)
print("전체 상품 수:", data["count"])
print("페이지당 상품 수:", product_counts[0])
print("평균 응답 시간:", round(statistics.mean(times_ms), 2), "ms")
print("중앙값 응답 시간:", round(statistics.median(times_ms), 2), "ms")
print("최소 응답 시간:", round(min(times_ms), 2), "ms")
print("최대 응답 시간:", round(max(times_ms), 2), "ms")
print("평균 응답 크기:", round(statistics.mean(sizes_bytes) / 1024, 2), "KB")

# 페이지 1과 페이지 2의 데이터 무결성 확인
page1 = requests.get(
    "http://127.0.0.1:8001/api/products/?page=1&page_size=50",
    timeout=30,
)
page2 = requests.get(
    "http://127.0.0.1:8001/api/products/?page=2&page_size=50",
    timeout=30,
)

page1.raise_for_status()
page2.raise_for_status()

data1 = page1.json()
data2 = page2.json()

ids1 = [item["id"] for item in data1["results"]]
ids2 = [item["id"] for item in data2["results"]]

print("\n--- 페이지 데이터 검증 ---")
print("페이지 1 상품 수:", len(ids1))
print("페이지 2 상품 수:", len(ids2))
print("페이지 간 ID 중복:", len(set(ids1) & set(ids2)))
print("페이지 1 다음 페이지 존재:", data1["next"] is not None)
print("페이지 2 이전 페이지 존재:", data2["previous"] is not None)
print("전체 상품 수:", data1["count"])
