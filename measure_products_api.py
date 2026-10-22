import time
import statistics
import urllib.request

url = "http://127.0.0.1:8000/api/products/"
times = []
last_size = 0

for i in range(11):
    start = time.perf_counter()
    with urllib.request.urlopen(url) as response:
        body = response.read()
        status = response.status
    elapsed = (time.perf_counter() - start) * 1000

    if i > 0:  # 첫 요청은 워밍업으로 제외
        times.append(elapsed)
    last_size = len(body)

print(f"HTTP 상태: {status}")
print(f"측정 횟수: {len(times)}회 (첫 요청 제외)")
print(f"평균 응답 시간: {statistics.mean(times):.2f} ms")
print(f"최솟값: {min(times):.2f} ms")
print(f"최댓값: {max(times):.2f} ms")
print(f"응답 크기: {last_size:,} bytes")
