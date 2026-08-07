from django.db.models import F, Q
from django.views.generic import View, ListView, TemplateView, CreateView
from django.utils import timezone
from datetime import timedelta
from vendor.models import Category, Product, Coupon
from customer.models import Customer, Order, Wishlist, Cart, CartItem
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from decimal import Decimal
from django.contrib import messages
from django.urls import reverse_lazy


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

    template_name = "product/product_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        product = Product.objects.select_related("vendor", "category").get(id=self.kwargs["pk"])

        context["product"] = product

        context["related_products"] = Product.objects.filter(is_active=True, vendor__is_active=True, vendor__approval_status="APPROVED", category=product.category).exclude(id=product.id).select_related("vendor", "category")[:4]

        return context

class OrderHistoryView(LoginRequiredMixin, ListView):
    model = Order
    template_name = "Customer/order_history.html"
    context_object_name = "orders"
    paginate_by = 10

    def get_queryset(self):

        customer = Customer.objects.get(user=self.request.user)

        queryset = (
            Order.objects
            .filter(customer=customer)
            .prefetch_related(
                "items",
                "items__product",
            )
            .order_by("-ordered_at")
        )

        status = self.request.GET.get("status")

        if status:
            queryset = queryset.filter(
                order_status=status.upper()
            )

        date_range = self.request.GET.get("date_range")

        if date_range:

            today = timezone.now()

            queryset = queryset.filter(
                ordered_at__gte=today - timedelta(days=int(date_range))
            )

        return queryset

class WishlistView(LoginRequiredMixin, ListView):
    model = Wishlist
    template_name = "Customer/wishlist.html"
    context_object_name = "wishlist_items"
    paginate_by = 12

    def get_queryset(self):
        customer = get_object_or_404(
            Customer,
            user=self.request.user
        )

        return (
            Wishlist.objects
            .filter(customer=customer)
            .select_related(
                "product",
                "product__category",
                "product__vendor",
            )
            .order_by("-created_at")
        )

class CartView(LoginRequiredMixin, ListView):
    model = CartItem
    template_name = "cart/cart.html"
    context_object_name = "cart_items"

    SHIPPING_CHARGE = Decimal("150.00")
    FREE_SHIPPING_AMOUNT = Decimal("2000.00")
    TAX_PERCENT = Decimal("0")

    def dispatch(self, request, *args, **kwargs):
        self.customer = get_object_or_404(
            Customer,
            user=request.user
        )

        self.cart, created = Cart.objects.get_or_create(
            customer=self.customer
        )

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):

        # Update quantity
        if request.POST.get("item_id"):

            item = get_object_or_404(
                CartItem,
                id=request.POST.get("item_id"),
                cart=self.cart
            )

            quantity = max(
                1,
                int(request.POST.get("quantity", 1))
            )

            item.quantity = quantity
            item.save()

            messages.success(
                request,
                "Cart updated successfully."
            )

            return redirect("customer:cart")

        # Remove item
        if request.POST.get("remove_item"):

            item = get_object_or_404(
                CartItem,
                id=request.POST.get("remove_item"),
                cart=self.cart
            )

            item.delete()

            messages.success(
                request,
                "Item removed from cart."
            )

            return redirect("customer:cart")

        # Coupon (placeholder)
        if request.POST.get("promo_code"):

            code = request.POST.get("promo_code").strip().upper()

            if Coupon.objects.filter(
                code=code,
                is_active=True
            ).exists():

                request.session["promo_code"] = code

                messages.success(
                    request,
                    "Coupon applied successfully."
                )

            else:

                request.session.pop("promo_code", None)

                messages.error(
                    request,
                    "Invalid coupon code."
                )

            return redirect("customer:cart")

        return redirect("customer:cart")

    def get_queryset(self):

        return (
            CartItem.objects
            .filter(cart=self.cart)
            .select_related(
                "product",
                "product__vendor",
                "product__category"
            )
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        cart_items = context["cart_items"]

        subtotal = Decimal("0")

        total_items = 0

        for item in cart_items:
            subtotal += item.subtotal
            total_items += item.quantity

        shipping = (
            Decimal("0")
            if subtotal >= self.FREE_SHIPPING_AMOUNT or subtotal == 0
            else self.SHIPPING_CHARGE
        )

        tax = subtotal * self.TAX_PERCENT / Decimal("100")

        discount = Decimal("0")

        promo_code = request_code = self.request.session.get(
            "promo_code"
        )

        if request_code:

            try:

                coupon = Coupon.objects.get(
                    code=request_code,
                    is_active=True
                )

                if subtotal >= coupon.minimum_purchase:
                    discount = (
                        subtotal *
                        Decimal(coupon.discount) /
                        Decimal("100")
                    )

            except Coupon.DoesNotExist:
                pass

        total = subtotal + shipping + tax - discount

        context.update(
            {
                "cart": self.cart,
                "cart_item_count": total_items,
                "cart_subtotal": subtotal,
                "cart_shipping": shipping,
                "cart_tax": tax,
                "cart_discount": discount,
                "cart_total": total,
                "promo_code": promo_code,
            }
        )

        return context


class AddToCartView(LoginRequiredMixin, CreateView):
    model = CartItem
    fields = []

    def post(self, request, *args, **kwargs):
        customer = get_object_or_404(
            Customer,
            user=request.user
        )

        cart, _ = Cart.objects.get_or_create(
            customer=customer
        )

        product = get_object_or_404(
            Product,
            pk=self.kwargs["pk"],
            is_active=True
        )

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                "quantity": 1
            }
        )

        if not created:
            item.quantity += 1
            item.save(update_fields=["quantity"])

        messages.success(
            request,
            "Product added to cart."
        )

        return redirect(
            request.META.get(
                "HTTP_REFERER",
                reverse_lazy("customer:cart")
            )
        )

class CheckoutView(LoginRequiredMixin, TemplateView):

    template_name = "cart/checkout.html"

    SHIPPING_CHARGE = Decimal("150.00")
    FREE_SHIPPING_AMOUNT = Decimal("2000.00")
    TAX_PERCENT = Decimal("0")

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        customer = get_object_or_404(
            Customer,
            user=self.request.user
        )

        cart, created = Cart.objects.get_or_create(
            customer=customer
        )

        cart_items = (
            CartItem.objects
            .filter(cart=cart)
            .select_related(
                "product"
            )
        )

        subtotal = Decimal("0")
        total_items = 0

        for item in cart_items:
            subtotal += item.subtotal
            total_items += item.quantity

        shipping = (
            Decimal("0")
            if subtotal >= self.FREE_SHIPPING_AMOUNT or subtotal == 0
            else self.SHIPPING_CHARGE
        )

        tax = subtotal * self.TAX_PERCENT / Decimal("100")

        discount = Decimal("0")

        promo_code = self.request.session.get(
            "promo_code"
        )

        if promo_code:

            try:

                coupon = Coupon.objects.get(
                    code=promo_code,
                    is_active=True
                )

                if subtotal >= coupon.minimum_purchase:

                    discount = (
                        subtotal *
                        Decimal(coupon.discount) /
                        Decimal("100")
                    )

            except Coupon.DoesNotExist:
                pass

        total = subtotal + shipping + tax - discount

        context.update(
            {
                "cart": cart,
                "cart_items": cart_items,
                "cart_item_count": total_items,
                "cart_subtotal": subtotal,
                "cart_shipping": shipping,
                "cart_tax": tax,
                "cart_discount": discount,
                "cart_total": total,
                "promo_code": promo_code,
            }
        )

        return context



