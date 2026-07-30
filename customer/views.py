from django.db.models import Q
from django.views.generic import ListView, TemplateView

from vendor.models import Product, Category


class HomeView(TemplateView):
    """
    Customer homepage.
    """
    template_name = "Customer/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["categories"] = Category.objects.filter(
            is_active=True
        )[:12]

        context["featured_products"] = Product.objects.filter(
            is_active=True,
            is_featured=True,
        ).select_related("category")[:8]

        # Fallback categories used when the database has no categories.
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
    """
    Display products in the customer shop.
    """

    model = Product
    template_name = "Customer/shop.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(
            is_active=True
        ).select_related("category")

        category = self.request.GET.get("category")
        deal = self.request.GET.get("deal")

        if category:
            queryset = queryset.filter(
                category__slug=category
            )

        if deal == "true":
            queryset = queryset.filter(
                discount_price__isnull=False
            )

        return queryset.order_by("-created_at")


class SearchResultView(ListView):
    """
    Search products by name, description, or category.
    """

    model = Product
    template_name = "Customer/search_result.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(
            is_active=True
        ).select_related("category")

        query = self.request.GET.get("q", "").strip()

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(description__icontains=query)
                | Q(category__name__icontains=query)
            )

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["query"] = self.request.GET.get("q", "").strip()

        return context