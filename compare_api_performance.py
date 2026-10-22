import statistics
import time

import requests

URLS = {
    "페이지네이션 적용": "http://127.0.0.1:8001/api/products/?page_size=50",
    "페이지네이션 미적용": "http://127.0.0.1:8003/api/products/",
}

REPEATS = 5

for label, url in URLS.items():
    print(f"\n--- {label} ---")

    # 준비 요청 1회
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    times = []
    sizes = []

    for _ in range(REPEATS):
        start = time.perf_counter()
        response = requests.get(url, timeout=60)
        elapsed = (time.perf_counter() - start) * 1000
        response.raise_for_status()

        times.append(elapsed)
        sizes.append(len(response.content))

    print("측정 횟수:", REPEATS)
    print("평균 응답 시간:", round(statistics.mean(times), 2), "ms")
    print("중앙값 응답 시간:", round(statistics.median(times), 2), "ms")
    print("평균 응답 크기:", round(statistics.mean(sizes) / 1024, 2), "KB")
