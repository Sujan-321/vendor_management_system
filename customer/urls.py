from django.urls import path

from .views import (
    HomeView,
    ShopView,
    SearchResultView,
    ProductDetailView,
    OrderHistoryView,
    WishlistView,
)

app_name = "customer"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("shop/", ShopView.as_view(), name="shop"),
    path("search/", SearchResultView.as_view(), name="search_result"),
    path("product/<int:pk>/", ProductDetailView.as_view(), name="product_detail"),
    path("order_history/", OrderHistoryView.as_view(), name="order_history"),
    path("wishlist/", WishlistView.as_view(), name="wishlist"),
]