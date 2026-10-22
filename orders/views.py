from rest_framework import generics, permissions
from .models import Order
from .serializers import OrderSerializer

class OrderCreateListView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # 현재 로그인한 사용자의 주문 내역만 조회
        return Order.objects.filter(user=self.request.user)