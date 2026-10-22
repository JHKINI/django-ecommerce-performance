import time
import statistics
import urllib.request

targets = {
    "기존 DB (12건)": "http://127.0.0.1:8000/api/products/",
    "테스트 DB (10만 건)": "http://127.0.0.1:8001/api/products/",
}

for label, url in targets.items():
    times = []
    size = 0
    status = None

    for i in range(11):
        start = time.perf_counter()
        with urllib.request.urlopen(url, timeout=120) as response:
            body = response.read()
            status = response.status
        elapsed = (time.perf_counter() - start) * 1000

        if i > 0:
            times.append(elapsed)

        size = len(body)

    print(f"\n[{label}]")
    print(f"HTTP 상태: {status}")
    print(f"평균 응답 시간: {statistics.mean(times):.2f} ms")
    print(f"최솟값: {min(times):.2f} ms")
    print(f"최댓값: {max(times):.2f} ms")
    print(f"응답 크기: {size:,} bytes ({size / 1024 / 1024:.2f} MiB)")
