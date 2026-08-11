from django.urls import path
from .views import (
    HomeView,
    ShopView,
    SearchResultView,
    ProductDetailView,
    OrderHistoryView,
    OrderDetailView,
    OrderCancelView,
    OrderListView,
    WishlistView,
    CartView,
    AddToCartView,
    CheckoutView,
    CreateOrderView,
    PaymentMethodView,
    EsewaPaymentView,
    EsewaSuccessView,
    EsewaFailureView,
)

app_name = "customer"

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("shop/", ShopView.as_view(), name="shop"),
    path("search/", SearchResultView.as_view(), name="search_result"),
    path("product/<int:pk>/", ProductDetailView.as_view(), name="product_detail"),
    path("order_history/", OrderHistoryView.as_view(), name="order_history"),
    path("order/detail/<int:pk>/", OrderDetailView.as_view(), name="order_detail"),
    path("orders/", OrderListView.as_view(), name="order_list"),
    path("order/cancel/<int:pk>/", OrderCancelView.as_view(), name="order_cancel"),
    path("wishlist/", WishlistView.as_view(), name="wishlist"),
    path("cart/", CartView.as_view(), name="cart"),
    path("cart/add/<int:pk>/", AddToCartView.as_view(), name="cart_add"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("checkout/create-order/", CreateOrderView.as_view(), name="create_order"),
    path("payment/<int:order_id>/", PaymentMethodView.as_view(), name="payment_method"),
    path("payment/<int:order_id>/esewa/", EsewaPaymentView.as_view(), name="esewa_payment"),
    path("payment/esewa/success/", EsewaSuccessView.as_view(), name="esewa_success"),
    path("payment/esewa/failure/", EsewaFailureView.as_view(), name="esewa_failure"),
]