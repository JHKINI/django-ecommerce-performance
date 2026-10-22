import csv
import math
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests


# =========================
# 1. 실행 환경 설정
# =========================

BASE_URL = "http://127.0.0.1:8000"
ORDERS_URL = f"{BASE_URL}/api/orders/"

ACCESS_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzkyNjQ4ODY1LCJpYXQiOjE3OTI2NDg1NjUsImp0aSI6IjNmNWNlNmNmYmMxOTRiOTFhN2E2ODVhMmU5MDUxNGM2IiwidXNlcl9pZCI6IjEifQ.zG6q_wHlrL3_kFzItuUsj2PlFhpus6p02zFkeBiReSM"
PRODUCT_ID = 1

# 동시 요청 수별 비교
CONCURRENCY_LEVELS = [1, 5, 10, 20, 50]

# 각 동시 요청 조건에서 실행할 전체 요청 수
REQUESTS_PER_LEVEL = 100

# 요청 타임아웃(초)
REQUEST_TIMEOUT = 30

# 결과 파일
SUMMARY_CSV = "benchmark_summary.csv"
DETAIL_CSV = "benchmark_requests.csv"

# 스레드마다 별도 HTTP 세션 사용
thread_local = threading.local()


# =========================
# 2. HTTP 세션 준비
# =========================

def get_session():
    if not hasattr(thread_local, "session"):
        session = requests.Session()
        session.headers.update({
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json",
        })
        thread_local.session = session

    return thread_local.session


# =========================
# 3. 주문 API 요청 1회
# =========================

def submit_order():
    payload = {
        "items": [
            {
                "product_id": PRODUCT_ID,
                "quantity": 1,
            }
        ]
    }

    start = time.perf_counter()

    try:
        response = get_session().post(
            ORDERS_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

        elapsed = time.perf_counter() - start

        return {
            "status": response.status_code,
            "elapsed": elapsed,
            "error": "",
        }

    except requests.RequestException as exc:
        elapsed = time.perf_counter() - start

        return {
            "status": "NETWORK_ERROR",
            "elapsed": elapsed,
            "error": str(exc),
        }


# =========================
# 4. 응답시간 통계 계산
# =========================

def percentile(values, percent):
    sorted_values = sorted(values)

    if not sorted_values:
        return 0

    # Nearest-rank 방식
    index = max(0, math.ceil(percent / 100 * len(sorted_values)) - 1)
    return sorted_values[index]


# =========================
# 5. 동시 요청 조건별 벤치마크
# =========================

def run_benchmark(concurrency):
    print(f"\n동시 요청 수 {concurrency}: 측정 시작")

    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        results = list(
            executor.map(
                lambda _: submit_order(),
                range(REQUESTS_PER_LEVEL),
            )
        )

    total_time = time.perf_counter() - start

    latencies = [result["elapsed"] for result in results]

    successful = sum(
        isinstance(result["status"], int)
        and 200 <= result["status"] < 300
        for result in results
    )

    client_errors = sum(
        isinstance(result["status"], int)
        and 400 <= result["status"] < 500
        for result in results
    )

    server_errors = sum(
        isinstance(result["status"], int)
        and 500 <= result["status"] < 600
        for result in results
    )

    network_errors = sum(
        result["status"] == "NETWORK_ERROR"
        for result in results
    )

    completed_throughput = (
        len(results) / total_time if total_time > 0 else 0
    )

    successful_throughput = (
        successful / total_time if total_time > 0 else 0
    )

    summary = {
        "concurrency": concurrency,
        "total_requests": len(results),
        "successful": successful,
        "client_errors_4xx": client_errors,
        "server_errors_5xx": server_errors,
        "network_errors": network_errors,
        "total_time_sec": round(total_time, 4),
        "avg_latency_sec": round(statistics.mean(latencies), 4),
        "p95_latency_sec": round(percentile(latencies, 95), 4),
        "completed_requests_per_sec": round(completed_throughput, 2),
        "successful_requests_per_sec": round(successful_throughput, 2),
    }

    print(f"성공 요청: {successful}/{len(results)}")
    print(f"4xx 응답: {client_errors}")
    print(f"5xx 응답: {server_errors}")
    print(f"네트워크 오류: {network_errors}")
    print(f"전체 경과 시간: {total_time:.3f}초")
    print(f"평균 응답시간: {statistics.mean(latencies):.3f}초")
    print(f"p95 응답시간: {percentile(latencies, 95):.3f}초")
    print(f"완료 처리량: {completed_throughput:.2f} req/s")
    print(f"성공 처리량: {successful_throughput:.2f} req/s")

    # 요청별 결과 저장
    with open(DETAIL_CSV, "a", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "concurrency",
                "status",
                "elapsed_sec",
                "error",
            ],
        )

        for result in results:
            writer.writerow({
                "concurrency": concurrency,
                "status": result["status"],
                "elapsed_sec": round(result["elapsed"], 4),
                "error": result["error"],
            })

    return summary


# =========================
# 6. 전체 실행 및 CSV 저장
# =========================

def main():
    if ACCESS_TOKEN == "여기에_액세스_토큰_입력":
        raise ValueError("ACCESS_TOKEN에 실제 액세스 토큰을 입력하세요.")

    # 이전 실행 결과와 섞이지 않도록 파일 초기화
    with open(DETAIL_CSV, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "concurrency",
                "status",
                "elapsed_sec",
                "error",
            ],
        )
        writer.writeheader()

    summaries = []

    for concurrency in CONCURRENCY_LEVELS:
        summary = run_benchmark(concurrency)
        summaries.append(summary)

    with open(SUMMARY_CSV, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(summaries[0].keys()),
        )
        writer.writeheader()
        writer.writerows(summaries)

    print("\n========== 벤치마크 완료 ==========")
    print(f"조건별 요약: {Path(SUMMARY_CSV).resolve()}")
    print(f"요청별 상세: {Path(DETAIL_CSV).resolve()}")


if __name__ == "__main__":
    main()