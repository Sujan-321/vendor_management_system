from django.urls import path
from .views import (
    ShopInformationUpdateView,
    ProductImageManageView,
    ProductImageDeleteView,
    HomeView,
    ProductUpdateView,
    ProductCreateView,
    ProductListView,
    ProductDetailView,
    ProductDeleteView,
    VendorOrderListView,
    VendorOrderDetailView,
    VendorOrderStatusView,
    VendorStockManagementView,
    VendorDashboardView,
)

app_name = 'vendor'

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("dashboard/", VendorDashboardView.as_view(), name="dashboard"),
    path("product/list/", ProductListView.as_view(), name="product_list"),
    path("product/create/", ProductCreateView.as_view(), name="product_create"),
    path("product/detail/<int:pk>/", ProductDetailView.as_view(), name="product_detail"),
    path("product/delete/<int:pk>/", ProductDeleteView.as_view(), name="product_delete"),
    path("product/update/<int:pk>/", ProductUpdateView.as_view(), name="product_update"),
    path("products/<int:pk>/images/", ProductImageManageView.as_view(), name="product_images"),
    path("product-images/<int:pk>/delete/", ProductImageDeleteView.as_view(), name="product_image_delete"),
    path("shop-information/", ShopInformationUpdateView.as_view(), name="shop_information"),
     # Orders
    path("orders/", VendorOrderListView.as_view(), name="order_list"),
    path("orders/<int:pk>/", VendorOrderDetailView.as_view(), name="order_detail"),
    path("orders/<int:pk>/status/", VendorOrderStatusView.as_view(), name="order_status"),

    # stock
    path("stock/", VendorStockManagementView.as_view(), name="vendor_stock_management"),
]