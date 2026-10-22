from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=255, db_index=True)  # 조회 최적화를 위한 인덱스 추가
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)  # 재고 관리 (동시성 제어 대상)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)  # 커서 페이징용

    def __str__(self):
        return self.name