from django.urls import path
from .views import HomeView, ProductCreateView, ProductListView, ProductDetailView, ProductDeleteView

app_name = 'vendor'

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("product/list/", ProductListView.as_view(), name="product_list"),
    path("product/create/", ProductCreateView.as_view(), name="product_create"),
    path("product/detail/<int:pk>/", ProductDetailView.as_view(), name="product_detail"),
    path("product/delete/<int:pk>/", ProductDeleteView.as_view(), name="product_delete"),
]