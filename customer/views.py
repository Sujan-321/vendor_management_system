from django.db.models import F, Q
from django.views.generic import ListView, TemplateView

from vendor.models import Category, Product


class HomeView(TemplateView):

    template_name = "Customer/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["categories"] = Category.objects.filter(is_active=True)[:12]

        context["featured_products"] = Product.objects.filter(is_active=True, vendor__is_active=True, vendor__approval_status="APPROVED", is_featured=True).select_related("vendor", "category")[:8]

        context["default_categories"] = {
            "Electronics": "bi-phone",
            "Fashion": "bi-bag",
            "Groceries": "bi-cart",
            "Beauty": "bi-heart",
            "Home & Living": "bi-house",
            "Sports": "bi-trophy",
        }

        return context


class ShopView(ListView):

    model = Product
    template_name = "Customer/shop.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True, vendor__is_active=True, vendor__approval_status="APPROVED").select_related("vendor", "category")

        category = self.request.GET.get("category")
        deal = self.request.GET.get("deal")

        if category:
            queryset = queryset.filter(category__slug=category)

        if deal == "true":
            queryset = queryset.filter(discount_price__isnull=False, discount_price__lt=F("price"))

        return queryset


class SearchResultView(ListView):

    model = Product
    template_name = "Customer/search_result.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True, vendor__is_active=True, vendor__approval_status="APPROVED").select_related("vendor", "category")

        query = self.request.GET.get("q", "").strip()

        if query:
            queryset = queryset.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(category__name__icontains=query) | Q(vendor__shop_name__icontains=query))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["query"] = self.request.GET.get("q", "").strip()
        return context


class ProductDetailView(TemplateView):

    template_name = "Customer/product/product_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        product = Product.objects.select_related("vendor", "category").get(id=self.kwargs["pk"])

        context["product"] = product

        context["related_products"] = Product.objects.filter(is_active=True, vendor__is_active=True, vendor__approval_status="APPROVED", category=product.category).exclude(id=product.id).select_related("vendor", "category")[:4]

        return context