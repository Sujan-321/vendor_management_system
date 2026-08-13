from django.shortcuts import render
from django.views.generic import TemplateView, ListView, CreateView, DetailView
from .models import Product, ProductImage, ProductSpecification
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .forms import ProductForm
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin


# Create your views here.
class HomeView(TemplateView):
    template_name = "Vendor/base.html"

class ProductListView(ListView):
    model = Product
    template_name = "Vendor/product/product_list.html"
    context_object_name = "products"
    paginate_by = 10

    def get_queryset(self):
        return Product.objects.filter(
            is_active__isnull = False
        ).order_by("-created_at")


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    template_name = "Vendor/product/product_create.html"
    form_class = ProductForm
    success_url = reverse_lazy("vendor:product_list")

    def form_valid(self, form):
        form.instance.vendor = self.request.user.vendor
        return super().form_valid(form)


class ProductDetailView(DetailView):
    model = Product
    template_name = "Vendor/product/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):
        query = super().get_queryset()   # it run the query : Products.objects.all()
        query = query.filter(
            vendor__user=self.request.user
        ).select_related(
            "vendor",
            "category"
        ).prefetch_related(
            "images",
            "specifications"
        )

        return query



    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.object.category

        return context

