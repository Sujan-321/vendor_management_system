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

