from django.urls import path
from .views import OrderCreateListView

urlpatterns = [
    path('', OrderCreateListView.as_view(), name='order-list-create'),
]