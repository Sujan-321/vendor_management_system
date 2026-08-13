from django.urls import path
from .views import ProductImageManageView, ProductImageDeleteView, HomeView, ProductUpdateView, ProductCreateView, ProductListView, ProductDetailView, ProductDeleteView

app_name = 'vendor'

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("product/list/", ProductListView.as_view(), name="product_list"),
    path("product/create/", ProductCreateView.as_view(), name="product_create"),
    path("product/detail/<int:pk>/", ProductDetailView.as_view(), name="product_detail"),
    path("product/delete/<int:pk>/", ProductDeleteView.as_view(), name="product_delete"),
    path("product/update/<int:pk>/", ProductUpdateView.as_view(), name="product_update"),
    path(
        "products/<int:pk>/images/",
        ProductImageManageView.as_view(),
        name="product_images",
    ),

    path(
        "product-images/<int:pk>/delete/",
        ProductImageDeleteView.as_view(),
        name="product_image_delete",
    ),
]