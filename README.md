# Django 기반 이커머스 주문 API 성능 진단

Django REST Framework와 PostgreSQL을 활용한 이커머스 주문 API 프로젝트입니다. 주문 생성 과정에서 재고 정합성을 유지하도록 트랜잭션을 적용하고, 동시 요청에 따른 API 응답 시간과 데이터베이스 쿼리를 측정하여 성능 특성을 분석했습니다.

## 1. Project Overview

### 프로젝트 목적

- 이커머스 주문 API 구현 및 주문 처리 흐름 설계
- 트랜잭션과 조건부 UPDATE를 활용한 재고 정합성 관리
- 동시 요청에 따른 API 응답 시간 및 처리량 측정
- SQL 실행 시간과 PostgreSQL 실행 계획을 활용한 데이터베이스 분석

### 주요 기능

| 기능 | 설명 |
|---|---|
| 주문 생성 | 상품 및 수량을 전달받아 주문과 주문 상세 생성 |
| 재고 관리 | 재고 조건을 확인한 후 주문 수량만큼 차감 |
| 트랜잭션 처리 | 주문 처리 중 오류 발생 시 관련 DB 변경사항 롤백 |
| 성능 측정 | 동시 요청별 응답 시간, p95, 처리량 측정 |
| SQL 분석 | SQL 쿼리 수, 실행 시간, PostgreSQL 실행 계획 확인 |

## 2. Tech Stack

| 구분 | 기술 |
|---|---|
| Language | Python |
| Backend | Django, Django REST Framework |
| Database | PostgreSQL |
| Authentication | JWT, Simple JWT |
| Testing | Django REST Framework APIClient |
| Performance Testing | Python requests 기반 동시 요청 테스트 |
| Database Analysis | CaptureQueriesContext, EXPLAIN, EXPLAIN ANALYZE |
| Version Control | Git, GitHub |

## 3. Order Processing

주문 요청은 상품 조회, 재고 검증 및 차감, 주문 생성, 주문 상세 저장 순서로 처리됩니다.

```text
Client
  │
  ▼
POST /api/orders/
  │
  ▼
Request Validation
  │
  ▼
transaction.atomic
  │
  ├─ 상품별 주문 수량 집계
  │
  ├─ 조건부 재고 차감
  │    └─ stock >= quantity
  │
  ├─ 주문 생성
  │
  └─ 주문 상세 저장
       │
       ▼
   Transaction Commit
```

### 핵심 구현

**① 조건부 재고 차감**

```python
updated = Product.objects.filter(
    pk=product_id,
    stock__gte=quantity,
).update(
    stock=F("stock") - quantity
)
```

재고가 주문 수량 이상인 경우에만 UPDATE가 수행되도록 조건을 설정했습니다. 재고 확인과 차감을 하나의 SQL UPDATE로 처리하여 별도의 조회와 수정 사이에 발생할 수 있는 경쟁 조건을 줄였습니다.

**② 트랜잭션 적용**

```python
@transaction.atomic
def create(self, validated_data):
    # 재고 차감 및 주문 생성
    ...
```

주문 처리 과정을 하나의 트랜잭션으로 묶어 중간 단계에서 오류가 발생하면 앞서 수행한 재고 변경도 롤백되도록 구성했습니다.

**③ 다중 상품 주문 처리**

상품별 주문 수량을 집계하고 상품 ID 순서로 재고 차감을 수행하도록 구현했습니다. 동일 상품이 주문 항목에 중복 포함된 경우에도 필요한 수량을 합산하여 재고를 검증합니다.

## 4. Performance Testing

### 테스트 환경 및 방법

- 주문 API: `POST /api/orders/`
- 동시 요청 조건: 1, 5, 10, 20, 50
- 각 조건의 요청 수: 100건
- 총 요청 수: 500건
- 측정 항목: 성공 건수, 평균 응답 시간, p95 응답 시간, 처리량
- 결과 저장: `benchmark_summary.csv`, `benchmark_requests.csv`

### 측정 결과

| 동시 요청 수 | 성공 건수 | 평균 응답 시간 | p95 응답 시간 | 처리량 |
|---:|---:|---:|---:|---:|
| 1 | 100/100 | 129ms | 219ms | 7.74 req/s |
| 5 | 100/100 | 203ms | 317ms | 23.71 req/s |
| 10 | 100/100 | 318ms | 455ms | 30.07 req/s |
| 20 | 100/100 | 600ms | 1,144ms | 29.16 req/s |
| 50 | 100/100 | 865ms | 1,559ms | 28.06 req/s |

※ 측정 당시 기록된 결과입니다. 실행 환경과 서버 상태에 따라 수치는 달라질 수 있습니다.

### 결과 분석

- 모든 조건에서 100건의 요청이 성공했으며, 기록된 HTTP 4xx·5xx 및 네트워크 오류는 없었습니다.
- 동시 요청 수가 증가하면서 평균 응답 시간과 p95 응답 시간이 증가했습니다.
- 동시 요청 10개 이후 처리량은 약 28~30 req/s 수준에서 정체되는 양상을 보였습니다.
- 처리량 정체와 응답 지연 증가를 관찰했지만, 현재 측정만으로 데이터베이스나 애플리케이션 중 어느 부분이 원인인지 확정하지는 않았습니다.

## 5. SQL Query Analysis

### 측정 결과

| 항목 | 결과 |
|---|---:|
| HTTP 상태 코드 | 201 |
| 기록된 SQL 쿼리 수 | 9개 |
| SQL 실행 시간 합계 | 약 26ms |
| 주문 생성 메서드 시간 | 약 13ms |

SQL 쿼리 측정은 Django의 `CaptureQueriesContext`를 사용해 API 처리 중 기록된 SQL과 실행 시간을 수집하는 방식으로 진행했습니다.

주요 쿼리는 사용자 조회, 상품 조회, 조건부 재고 UPDATE, 주문 INSERT, 주문 상세 INSERT 등으로 구성됩니다.

※ SQL 실행 시간 합계와 주문 생성 메서드 시간은 서로 다른 측정 범위입니다. 개별 SQL 실행 시간의 합계가 API 전체 요청 시간과 같지는 않습니다.

### PostgreSQL 실행 계획

`EXPLAIN ANALYZE`를 통해 상품 ID 조회 쿼리의 실행 계획을 확인했습니다.

```sql
EXPLAIN ANALYZE
SELECT id, name, price, stock, created_at
FROM products_product
WHERE id = 1;
```

확인 결과:

- 상품 테이블 데이터: 12건
- 실행 계획: `Seq Scan`
- 실제 실행 시간: 약 0.110ms
- 기본키 인덱스: 존재 확인

재고 차감 쿼리에서도 `Seq Scan`이 선택되는 것을 확인했습니다. 소규모 테이블에서는 순차 스캔이 비용 측면에서 유리할 수 있으므로, 이를 인덱스 누락이나 성능 문제로 단정하지 않았습니다.

현재 데이터 규모에서는 인덱스 추가의 효과를 입증할 근거가 부족하므로, 실행 계획과 실제 측정 결과를 바탕으로 판단하는 것을 우선했습니다.

## 6. Data Integrity Testing

### 재고 부족 주문 검증

재고가 96개인 상품에 97개를 주문하는 요청을 보내 검증했습니다.

| 검증 항목 | 테스트 전 | 테스트 후 |
|---|---:|---:|
| 재고 | 96 | 96 |
| 주문 수 | 504 | 504 |
| 주문 상세 수 | 504 | 504 |
| HTTP 상태 코드 | - | 400 |

재고 부족 요청이 거부되고 재고와 주문 데이터 건수가 유지되는 것을 확인했습니다.

### 트랜잭션 롤백 검증

주문 생성 단계에서 테스트용 예외를 발생시켜 롤백 동작을 확인했습니다.

| 검증 항목 | 테스트 전 | 테스트 후 |
|---|---:|---:|
| 재고 | 96 | 96 |
| 주문 수 | 504 | 504 |
| 주문 상세 수 | 504 | 504 |

재고 차감 이후 주문 생성 단계에서 오류가 발생하도록 구성했으며, 테스트 후 재고와 주문 데이터 건수가 동일하게 유지되는 것을 확인했습니다.

이 검증은 의도적인 예외 상황에서 트랜잭션 롤백이 동작하는지 확인하기 위한 테스트입니다. 모든 종류의 동시성 문제를 검증한 것은 아닙니다.

## 7. Project Structure

```text
django-ecommerce/
├── config/
│   └── settings.py
├── products/
│   └── models.py
├── orders/
│   ├── models.py
│   └── serializers.py
├── benchmark_orders.py
├── measure_sql.py
├── measure_transaction.py
├── test_insufficient_stock.py
├── test_order_rollback.py
├── benchmark_summary.csv
├── benchmark_requests.csv
└── README.md
```

※ 실제 프로젝트 구조에 맞춰 파일 및 디렉터리 구성을 확인한 후 업데이트합니다.

## 8. How to Run

### 1. 가상환경 활성화

```bash
conda activate order
```

### 2. 패키지 설치

프로젝트에 `requirements.txt`가 있다면 다음 명령어로 설치합니다.

```bash
pip install -r requirements.txt
```

### 3. 환경 설정

`config/settings.py`에서 PostgreSQL 연결 설정을 확인합니다. 데이터베이스 이름, 사용자 정보, 비밀번호 및 호스트는 실행 환경에 맞게 설정해야 합니다.

인증이 필요한 API 테스트에서는 유효한 JWT 액세스 토큰을 사용합니다. 실제 토큰과 비밀번호는 GitHub에 업로드하지 않습니다.

### 4. 개발 서버 실행

```bash
python manage.py runserver
```

기본 개발 서버 주소: `http://127.0.0.1:8000/`

### 5. 테스트 실행

```bash
python test_insufficient_stock.py
python test_order_rollback.py
```

벤치마크 스크립트는 실제 주문 데이터를 생성하고 재고를 차감할 수 있으므로, 실행 전 테스트 데이터와 재고 상태를 확인해야 합니다.

## 9. Limitations & Future Improvements

현재 프로젝트는 주문 API 구현, 기준 성능 측정, SQL 분석 및 주요 데이터 정합성 검증을 완료한 상태입니다.

현재 확인된 한계와 후속 개선 방향은 다음과 같습니다.

- **데이터 규모:** 상품 데이터가 12건인 환경에서 실행 계획을 확인했으므로 대규모 데이터 환경의 성능을 대표하지 않습니다.
- **병목 원인 분석:** 동시 요청 증가에 따른 응답 지연을 확인했으나, DB 잠금 대기나 서버 자원 사용량을 별도로 측정하지 않았습니다.
- **성능 개선 검증:** 아직 특정 최적화 기법의 적용 전후를 비교하여 개선 효과를 입증하지 않았습니다.
- **테스트 확장:** 다중 사용자 동시 주문과 다양한 실패 조건에 대한 자동화 테스트를 추가할 수 있습니다.

향후 데이터 규모와 테스트 조건을 확장하고, 병목 원인을 구체적으로 측정한 뒤 개선 전후 결과를 비교하는 방향으로 발전시킬 수 있습니다.

## 10. Key Takeaways

- Django REST Framework를 활용한 주문 API 구현
- PostgreSQL 트랜잭션과 조건부 UPDATE를 활용한 재고 정합성 관리
- 동시 요청 조건별 응답 시간 및 처리량 측정
- SQL 쿼리 수와 실행 계획을 활용한 DB 분석
- 실패 시나리오를 통한 데이터 정합성 및 트랜잭션 롤백 검증
- 측정 결과와 한계를 구분하여 성능 분석 결과를 문서화

이 프로젝트를 통해 주문 처리 로직 구현뿐 아니라, 측정 결과를 근거로 시스템의 동작 특성과 추가 검증이 필요한 부분을 분석하는 경험을 쌓았습니다.
