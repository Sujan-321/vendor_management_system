from decimal import Decimal
from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Count, Q, Prefetch, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import (
    View,
    TemplateView,
    ListView,
    CreateView,
    DetailView,
    DeleteView,
    UpdateView,
)

from .models import Product, ProductImage, ProductSpecification, Vendor, Category
from .forms import ProductForm, ProductImageForm, ShopInformationForm

from customer.models import Order, OrderItem


LOW_STOCK_THRESHOLD = 30


# ============================================================
# COMMON VENDOR MIXINS
# ============================================================

class VendorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Allows access only to authenticated users who have
    a Vendor profile.
    """

    def test_func(self):
        return hasattr(self.request.user, "vendor")

    def get_vendor(self):
        return self.request.user.vendor


class ApprovedVendorRequiredMixin(VendorRequiredMixin):
    """
    Allows access only to vendors who are:
        1. Active
        2. Approved
    """

    def dispatch(self, request, *args, **kwargs):

        if not hasattr(request.user, "vendor"):
            return redirect("accounts:login")

        vendor = request.user.vendor

        if not vendor.is_active:
            return redirect("accounts:login")

        if vendor.approval_status != "APPROVED":
            return redirect("vendor:vendor_profile")

        return super().dispatch(request, *args, **kwargs)


class VendorProductQuerysetMixin(VendorRequiredMixin):
    """
    Common queryset logic for products belonging to
    the currently logged-in vendor.
    """

    def get_vendor_product_queryset(self):
        return (
            Product.objects
            .filter(vendor=self.get_vendor())
        )

    def get_queryset(self):
        return (
            self.get_vendor_product_queryset()
            .select_related(
                "vendor",
                "category",
            )
        )


class VendorProductObjectMixin(VendorRequiredMixin):
    """
    Common helper for retrieving a product belonging
    to the logged-in vendor.
    """

    def get_product(self, pk):
        return get_object_or_404(
            Product.objects.select_related(
                "vendor",
                "category",
            ),
            pk=pk,
            vendor=self.get_vendor(),
        )


class VendorOrderQuerysetMixin(VendorRequiredMixin):
    """
    Common queryset logic for orders containing at least
    one product belonging to the logged-in vendor.
    """

    def get_vendor_order_queryset(self):
        return (
            Order.objects
            .filter(
                items__product__vendor=self.get_vendor()
            )
            .distinct()
        )

    def get_queryset(self):
        return (
            self.get_vendor_order_queryset()
            .select_related(
                "customer",
                "shipping_address",
                "payment",
            )
        )


class VendorOrderContextMixin:
    """
    Adds template-friendly fields to an Order.

    This prevents the same customer/status/payment/shipping
    conversion code from being repeated in multiple views.
    """

    def prepare_order_context(self, order):

        # ----------------------------------------------------
        # Customer
        # ----------------------------------------------------

        if order.customer:
            order.customer_name = order.customer.full_name

            if order.customer.user:
                order.customer_email = order.customer.user.email
            else:
                order.customer_email = ""

            order.customer_phone = order.customer.phone_number

        else:
            order.customer_name = "Guest Customer"
            order.customer_email = ""
            order.customer_phone = ""

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        order.status = order.order_status.lower()

        # ----------------------------------------------------
        # Date
        # ----------------------------------------------------

        order.created_at = order.ordered_at

        # ----------------------------------------------------
        # Payment status
        # ----------------------------------------------------

        order.is_paid = (
            order.payment_status == "PAID"
        )

        # ----------------------------------------------------
        # Shipping
        # ----------------------------------------------------

        order.shipping = order.shipping_charge

        # ----------------------------------------------------
        # Tax
        # ----------------------------------------------------

        # Your current Order model does not contain tax.
        order.tax = Decimal("0.00")

        # ----------------------------------------------------
        # Payment information
        # ----------------------------------------------------

        if hasattr(order, "payment") and order.payment:

            order.payment_method = (
                order.payment.get_payment_method_display()
            )

            order.transaction_id = (
                order.payment.transaction_id
            )

        else:

            order.payment_method = "Not Available"
            order.transaction_id = "Not Available"

        return order


# ============================================================
# HOME
# ============================================================

class HomeView(TemplateView):
    template_name = "Vendor/base.html"

# class ProductListView(VendorProductQuerysetMixin, ListView):
#     model = Product
#     template_name = "Vendor/product/product_list.html"
#     context_object_name = "products"
#     paginate_by = 10

#     def get_queryset(self):

#         queryset = (
#             self.get_vendor_product_queryset()
#             .filter(
#                 is_active=True
#             )
#             .select_related("category")
#             .order_by("-created_at")
#         )

#         query = self.request.GET.get("q", "").strip()

#         if query:
#             queryset = queryset.filter(
#                 Q(name__icontains=query)
#                 | Q(sku__icontains=query)
#             )

#         return queryset

#     def get_context_data(self, **kwargs):

#         context = super().get_context_data(**kwargs)

#         categories = (
#             self.get_vendor_product_queryset()
#             .filter(
#                 category__isnull=False
#             )
#             .values_list(
#                 "category",
#                 flat=True
#             )
#             .distinct()
#         )

#         from .models import Category

#         context["categories"] = (
#             Category.objects
#             .filter(id__in=categories)
#             .order_by("name")
#         )

#         return context



class ProductListView(VendorProductQuerysetMixin, ListView):
    model = Product
    template_name = "Vendor/product/product_list.html"
    context_object_name = "products"
    paginate_by = 10

    def get_queryset(self):

        # -----------------------------------------------------
        # Start with ONLY this vendor's products
        # -----------------------------------------------------

        queryset = (
            self.get_vendor_product_queryset()
            .select_related("category")
            .order_by("-created_at")
        )

        # -----------------------------------------------------
        # SEARCH
        # -----------------------------------------------------

        query = self.request.GET.get("q", "").strip()

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(sku__icontains=query)
            )

        # -----------------------------------------------------
        # CATEGORY
        # -----------------------------------------------------

        category = self.request.GET.get(
            "category",
            ""
        ).strip()

        if category:
            queryset = queryset.filter(
                category_id=category
            )

        # -----------------------------------------------------
        # STATUS
        # -----------------------------------------------------

        status = self.request.GET.get(
            "status",
            ""
        ).strip().lower()

        if status == "active":

            queryset = queryset.filter(
                is_active=True,
                stock__gt=0
            )

        elif status == "draft":

            queryset = queryset.filter(
                is_active=False
            )

        elif status == "out_of_stock":

            queryset = queryset.filter(
                stock=0
            )

        return queryset

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        # -----------------------------------------------------
        # Categories used by THIS vendor
        # -----------------------------------------------------

        categories = (
            Category.objects
            .filter(
                products__vendor=self.get_vendor()
            )
            .distinct()
            .order_by("name")
        )

        context["categories"] = categories

        # -----------------------------------------------------
        # Current filter values
        # -----------------------------------------------------

        context["current_query"] = (
            self.request.GET.get("q", "").strip()
        )

        context["current_category"] = (
            self.request.GET.get("category", "").strip()
        )

        context["current_status"] = (
            self.request.GET.get("status", "").strip()
        )

        return context



class ProductCreateView(VendorRequiredMixin, CreateView):
    model = Product
    template_name = "Vendor/product/product_create.html"
    form_class = ProductForm
    success_url = reverse_lazy("vendor:product_list")

    def form_valid(self, form):

        form.instance.vendor = self.get_vendor()

        messages.success(
            self.request,
            "Product created successfully."
        )

        return super().form_valid(form)


class ProductDetailView(VendorProductQuerysetMixin, DetailView):
    model = Product
    template_name = "Vendor/product/product_detail.html"
    context_object_name = "product"

    def get_queryset(self):

        return (
            self.get_vendor_product_queryset()
            .select_related(
                "vendor",
                "category",
            )
            .prefetch_related(
                "images",
                "specifications",
            )
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context["category"] = self.object.category

        return context


class ProductUpdateView(VendorProductQuerysetMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "Vendor/product/product_update.html"
    context_object_name = "product"
    success_url = reverse_lazy("vendor:product_list")

    def form_valid(self, form):

        messages.success(
            self.request,
            "Product updated successfully."
        )

        return super().form_valid(form)


class ProductDeleteView(VendorProductQuerysetMixin, DeleteView):
    model = Product
    template_name = "Vendor/product/product_delete.html"
    context_object_name = "product"
    success_url = reverse_lazy("vendor:product_list")

    def form_valid(self, form):

        messages.success(
            self.request,
            "Product deleted successfully."
        )

        return super().form_valid(form)


# ============================================================
# PRODUCT IMAGE MANAGEMENT
# ============================================================

class ProductImageManageView(
    VendorProductObjectMixin,
    View
):
    template_name = "Vendor/product/product_images.html"

    def get(self, request, pk):

        product = self.get_product(pk)

        form = ProductImageForm()

        return render(
            request,
            self.template_name,
            {
                "product": product,
                "form": form,
            },
        )

    @transaction.atomic
    def post(self, request, pk):

        product = self.get_product(pk)

        form = ProductImageForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            images = form.cleaned_data["images"]

            for image in images:

                ProductImage.objects.create(
                    product=product,
                    image=image,
                )

            messages.success(
                request,
                f"{len(images)} image(s) uploaded successfully.",
            )

            return redirect(
                "vendor:product_images",
                product.id,
            )

        return render(
            request,
            self.template_name,
            {
                "product": product,
                "form": form,
            },
        )


class ProductImageDeleteView(VendorRequiredMixin, View):

    def post(self, request, pk):

        image = get_object_or_404(
            ProductImage.objects.select_related(
                "product",
                "product__vendor",
            ),
            pk=pk,
            product__vendor=self.get_vendor(),
        )

        product_id = image.product_id

        image.delete()

        messages.success(
            request,
            "Product image deleted successfully.",
        )

        return redirect(
            "vendor:product_images",
            product_id,
        )


# ============================================================
# VENDOR PROFILE
# ============================================================

class ShopInformationUpdateView(VendorRequiredMixin, UpdateView):
    model = Vendor
    form_class = ShopInformationForm
    template_name = "Vendor/profile/shop_information.html"
    context_object_name = "vendor"

    def get_object(self, queryset=None):
        return self.get_vendor()

    def form_valid(self, form):

        messages.success(
            self.request,
            "Shop information updated successfully."
        )

        return super().form_valid(form)

    def form_invalid(self, form):

        messages.error(
            self.request,
            "Please correct the errors below."
        )

        return super().form_invalid(form)

    def get_success_url(self):
        return reverse("shop_information")


# ============================================================
# VENDOR ORDER LIST
# ============================================================

class VendorOrderListView(
    VendorOrderQuerysetMixin,
    ListView
):
    model = Order
    template_name = "Vendor/order/order_list.html"
    context_object_name = "orders"
    paginate_by = 10

    def get_queryset(self):

        vendor = self.get_vendor()

        queryset = (
            self.get_vendor_order_queryset()
            .select_related(
                "customer",
                "shipping_address",
                "payment",
            )
            .annotate(
                item_count=Count(
                    "items",
                    filter=Q(
                        items__product__vendor=vendor
                    ),
                    distinct=True,
                )
            )
            .order_by("-ordered_at")
        )

        # ----------------------------------------------------
        # Search
        # ----------------------------------------------------

        query = self.request.GET.get("q", "").strip()

        if query:
            queryset = queryset.filter(
                Q(order_number__icontains=query)
                | Q(customer__full_name__icontains=query)
                | Q(customer__user__email__icontains=query)
            )

        # ----------------------------------------------------
        # Status
        # ----------------------------------------------------

        status = self.request.GET.get(
            "status",
            ""
        ).lower()

        status_map = {
            "pending": "PENDING",
            "processing": "CONFIRMED",
            "confirmed": "CONFIRMED",
            "shipped": "SHIPPED",
            "delivered": "DELIVERED",
            "cancelled": "CANCELLED",
        }

        if status in status_map:

            queryset = queryset.filter(
                order_status=status_map[status]
            )

        # ----------------------------------------------------
        # From date
        # ----------------------------------------------------

        from_date = self.request.GET.get("from")

        if from_date:

            try:

                from_date = datetime.strptime(
                    from_date,
                    "%Y-%m-%d"
                ).date()

                queryset = queryset.filter(
                    ordered_at__date__gte=from_date
                )

            except ValueError:
                pass

        # ----------------------------------------------------
        # To date
        # ----------------------------------------------------

        to_date = self.request.GET.get("to")

        if to_date:

            try:

                to_date = datetime.strptime(
                    to_date,
                    "%Y-%m-%d"
                ).date()

                queryset = queryset.filter(
                    ordered_at__date__lte=to_date
                )

            except ValueError:
                pass

        return queryset

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        orders = context["orders"]

        for order in orders:

            self.prepare_order_context(order)

        context["orders"] = orders

        return context

    def prepare_order_context(self, order):

        order.customer_name = (
            order.customer.full_name
            if order.customer
            else "Guest Customer"
        )

        order.customer_email = (
            order.customer.user.email
            if order.customer and order.customer.user
            else ""
        )

        order.status = order.order_status.lower()

        order.created_at = order.ordered_at

        order.is_paid = (
            order.payment_status == "PAID"
        )

        return order


# ============================================================
# VENDOR ORDER DETAIL
# ============================================================

class VendorOrderDetailView(
    VendorOrderQuerysetMixin,
    VendorOrderContextMixin,
    DetailView
):
    model = Order
    template_name = "Vendor/order/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):

        vendor = self.get_vendor()

        return (
            self.get_vendor_order_queryset()
            .select_related(
                "customer",
                "customer__user",
                "shipping_address",
                "payment",
            )
            .prefetch_related(
                Prefetch(
                    "items",
                    queryset=OrderItem.objects.filter(
                        product__vendor=vendor
                    ).select_related("product"),
                )
            )
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        order = self.prepare_order_context(
            context["order"]
        )

        # ----------------------------------------------------
        # Shipping address
        # ----------------------------------------------------

        if order.shipping_address:

            address = order.shipping_address

            order.shipping_address_display = (
                f"{address.address}, "
                f"{address.city}, "
                f"{address.state}, "
                f"{address.country}, "
                f"{address.postal_code}"
            )

        else:

            order.shipping_address_display = ""

        # ----------------------------------------------------
        # Order items
        # ----------------------------------------------------

        for item in order.items.all():

            item.unit_price = item.price

        # ----------------------------------------------------
        # Timeline
        # ----------------------------------------------------

        context["default_timeline"] = (
            self.get_status_timeline(order)
        )

        return context

    def get_status_timeline(self, order):

        status_order = [
            ("pending", "Order Placed"),
            ("confirmed", "Payment / Order Confirmed"),
            ("shipped", "Shipped"),
            ("delivered", "Delivered"),
        ]

        current_status = order.order_status.lower()

        # ----------------------------------------------------
        # Cancelled order
        # ----------------------------------------------------

        if current_status == "cancelled":

            return [
                {
                    "label": "Order Placed",
                    "timestamp": order.ordered_at.strftime(
                        "%b %d, %Y, %I:%M %p"
                    ),
                    "done": True,
                },
                {
                    "label": "Cancelled",
                    "timestamp": "Current Status",
                    "done": True,
                },
            ]

        status_index = {
            "pending": 0,
            "confirmed": 1,
            "shipped": 2,
            "delivered": 3,
        }

        current_index = status_index.get(
            current_status,
            0
        )

        timeline = []

        for index, (status, label) in enumerate(
            status_order
        ):

            if index == 0:

                timestamp = (
                    order.ordered_at.strftime(
                        "%b %d, %Y, %I:%M %p"
                    )
                )

            else:

                timestamp = (
                    "Completed"
                    if index <= current_index
                    else "Pending"
                )

            timeline.append({
                "label": label,
                "timestamp": timestamp,
                "done": index <= current_index,
            })

        return timeline


# ============================================================
# ORDER STATUS
# ============================================================

class VendorOrderStatusView(
    VendorOrderQuerysetMixin,
    DetailView
):
    model = Order
    template_name = "Vendor/order/order_status.html"
    context_object_name = "order"

    def get_queryset(self):

        return (
            self.get_vendor_order_queryset()
            .select_related(
                "customer",
                "shipping_address",
            )
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        order = context["order"]

        order.status = order.order_status.lower()

        # Your current model does not have tracking_number.
        order.tracking_number = ""

        return context

    def post(self, request, *args, **kwargs):

        self.object = self.get_object()

        order = self.object

        new_status = request.POST.get(
            "status",
            ""
        ).lower()

        status_map = {
            "pending": "PENDING",
            "processing": "CONFIRMED",
            "confirmed": "CONFIRMED",
            "shipped": "SHIPPED",
            "delivered": "DELIVERED",
            "cancelled": "CANCELLED",
        }

        if new_status not in status_map:

            messages.error(
                request,
                "Invalid order status."
            )

            return redirect(
                "vendor:order_status",
                order.id
            )

        new_order_status = status_map[new_status]

        # ----------------------------------------------------
        # Prevent cancelled orders from being modified
        # ----------------------------------------------------

        if order.order_status == "CANCELLED":

            messages.error(
                request,
                "A cancelled order cannot be updated."
            )

            return redirect(
                "vendor:order_detail",
                order.id
            )

        order.order_status = new_order_status

        order.save(
            update_fields=["order_status"]
        )

        messages.success(
            request,
            f"Order #{order.id} status updated successfully."
        )

        return redirect(
            "vendor:order_detail",
            order.id
        )


# ============================================================
# STOCK MANAGEMENT
# ============================================================

class VendorStockManagementView(
    VendorProductQuerysetMixin,
    ListView
):
    model = Product
    template_name = "Vendor/stock/stock_management.html"
    context_object_name = "products"
    paginate_by = 10

    def get_queryset(self):

        queryset = (
            self.get_vendor_product_queryset()
            .select_related("category")
            .order_by("name")
        )

        # ----------------------------------------------------
        # Search
        # ----------------------------------------------------

        query = self.request.GET.get(
            "q",
            ""
        ).strip()

        if query:

            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(sku__icontains=query)
            )

        # ----------------------------------------------------
        # Stock filter
        # ----------------------------------------------------

        stock_filter = self.request.GET.get(
            "filter",
            ""
        ).strip()

        if stock_filter == "low_stock":

            queryset = queryset.filter(
                stock__gt=0,
                stock__lte=LOW_STOCK_THRESHOLD
            )

        elif stock_filter == "out_of_stock":

            queryset = queryset.filter(
                stock=0
            )

        return queryset

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        vendor = self.get_vendor()

        vendor_products = Product.objects.filter(
            vendor=vendor
        )

        context["stock_summary"] = {

            "total": vendor_products.count(),

            "low_stock": vendor_products.filter(
                stock__gt=0,
                stock__lte=LOW_STOCK_THRESHOLD
            ).count(),

            "out_of_stock": vendor_products.filter(
                stock=0
            ).count(),
        }

        context["low_stock_threshold"] = (
            LOW_STOCK_THRESHOLD
        )

        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        vendor = self.get_vendor()

        products = Product.objects.filter(
            vendor=vendor
        )

        updated_count = 0

        for product in products:

            field_name = f"stock_{product.id}"

            if field_name not in request.POST:
                continue

            raw_stock = request.POST.get(
                field_name
            )

            try:

                new_stock = int(raw_stock)

            except (TypeError, ValueError):

                messages.error(
                    request,
                    f"Invalid stock value for {product.name}."
                )

                continue

            if new_stock < 0:

                messages.error(
                    request,
                    f"Stock cannot be negative for {product.name}."
                )

                continue

            if product.stock != new_stock:

                product.stock = new_stock

                product.save(
                    update_fields=[
                        "stock",
                        "updated_at",
                    ]
                )

                updated_count += 1

        if updated_count:

            messages.success(
                request,
                f"{updated_count} product stock level(s) "
                "updated successfully."
            )

        else:

            messages.info(
                request,
                "No stock changes were made."
            )

        # ----------------------------------------------------
        # Preserve search/filter after POST
        # ----------------------------------------------------

        referer = request.META.get(
            "HTTP_REFERER"
        )

        if referer:
            return redirect(referer)

        return redirect(
            "vendor_stock_management"
        )


# ============================================================
# VENDOR DASHBOARD
# ============================================================

class VendorDashboardView(ApprovedVendorRequiredMixin, TemplateView):
    template_name = "Vendor/dashboard.html"

    VALID_ORDER_STATUSES = (
        "CONFIRMED",
        "SHIPPED",
        "DELIVERED",
    )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        vendor = self.get_vendor()

        now = timezone.now()

        # ====================================================
        # DATE RANGES
        # ====================================================

        current_30_start = (
            now - timedelta(days=30)
        )

        previous_30_start = (
            now - timedelta(days=60)
        )

        chart_start = (
            now - timedelta(days=13)
        )

        # ====================================================
        # PRODUCTS
        # ====================================================

        vendor_products = Product.objects.filter(
            vendor=vendor
        )

        # ====================================================
        # VENDOR ORDERS
        # ====================================================

        vendor_orders = (
            Order.objects
            .filter(
                items__product__vendor=vendor
            )
            .distinct()
        )

        # ====================================================
        # VALID ORDERS
        # ====================================================

        valid_vendor_orders = (
            vendor_orders.filter(
                order_status__in=self.VALID_ORDER_STATUSES
            )
        )

        # ====================================================
        # CURRENT 30-DAY ORDERS
        # ====================================================

        current_orders = (
            valid_vendor_orders.filter(
                ordered_at__gte=current_30_start
            )
        )

        orders_30d = current_orders.count()

        # ====================================================
        # PREVIOUS 30-DAY ORDERS
        # ====================================================

        previous_orders = (
            valid_vendor_orders.filter(
                ordered_at__gte=previous_30_start,
                ordered_at__lt=current_30_start,
            ).count()
        )

        # ====================================================
        # ORDER DELTA
        # ====================================================

        if previous_orders > 0:

            orders_delta_value = (
                (orders_30d - previous_orders)
                / previous_orders
            ) * 100

        elif orders_30d > 0:

            orders_delta_value = 100

        else:

            orders_delta_value = 0

        orders_delta = (
            f"{orders_delta_value:.1f}%"
        )

        orders_delta_direction = (
            "up"
            if orders_delta_value > 0
            else "down"
            if orders_delta_value < 0
            else "flat"
        )

        # ====================================================
        # CURRENT 30-DAY REVENUE
        # ====================================================

        current_vendor_items = (
            OrderItem.objects
            .filter(
                product__vendor=vendor,
                order__ordered_at__gte=current_30_start,
                order__order_status__in=(
                    self.VALID_ORDER_STATUSES
                ),
            )
        )

        revenue_30d = (
            current_vendor_items.aggregate(
                total=Sum("subtotal")
            )["total"]
            or Decimal("0.00")
        )

        # ====================================================
        # PREVIOUS 30-DAY REVENUE
        # ====================================================

        previous_vendor_items = (
            OrderItem.objects
            .filter(
                product__vendor=vendor,
                order__ordered_at__gte=previous_30_start,
                order__ordered_at__lt=current_30_start,
                order__order_status__in=(
                    self.VALID_ORDER_STATUSES
                ),
            )
        )

        previous_revenue = (
            previous_vendor_items.aggregate(
                total=Sum("subtotal")
            )["total"]
            or Decimal("0.00")
        )

        # ====================================================
        # REVENUE DELTA
        # ====================================================

        if previous_revenue > 0:

            revenue_delta_value = (
                (revenue_30d - previous_revenue)
                / previous_revenue
            ) * 100

        elif revenue_30d > 0:

            revenue_delta_value = 100

        else:

            revenue_delta_value = 0

        revenue_delta = (
            f"{revenue_delta_value:.1f}%"
        )

        revenue_delta_direction = (
            "up"
            if revenue_delta_value > 0
            else "down"
            if revenue_delta_value < 0
            else "flat"
        )

        # ====================================================
        # PENDING ORDERS
        # ====================================================

        pending_orders = (
            vendor_orders
            .filter(
                order_status="PENDING"
            )
            .count()
        )

        # ====================================================
        # CANCELLED ORDERS
        # ====================================================

        cancelled_orders = (
            vendor_orders
            .filter(
                order_status="CANCELLED"
            )
            .count()
        )

        # ====================================================
        # LOW STOCK
        # ====================================================

        low_stock_queryset = (
            vendor_products.filter(
                stock__gt=0,
                stock__lte=LOW_STOCK_THRESHOLD,
                is_active=True,
            )
        )

        low_stock_count = (
            low_stock_queryset.count()
        )

        low_stock_items = (
            low_stock_queryset
            .order_by(
                "stock",
                "name"
            )[:5]
        )

        # ====================================================
        # REVENUE CHART
        # ====================================================

        chart_items = (
            OrderItem.objects
            .filter(
                product__vendor=vendor,
                order__ordered_at__gte=chart_start,
                order__order_status__in=(
                    self.VALID_ORDER_STATUSES
                ),
            )
            .annotate(
                order_date=TruncDate(
                    "order__ordered_at"
                )
            )
            .values(
                "order_date"
            )
            .annotate(
                revenue=Sum("subtotal")
            )
            .order_by(
                "order_date"
            )
        )

        revenue_by_date = {
            row["order_date"]: row["revenue"]
            for row in chart_items
        }

        chart_labels = []
        chart_values = []

        for i in range(14):

            current_date = (
                chart_start.date()
                + timedelta(days=i)
            )

            chart_labels.append(
                current_date.strftime(
                    "%b %d"
                )
            )

            amount = (
                revenue_by_date.get(
                    current_date,
                    Decimal("0.00")
                )
            )

            chart_values.append(
                float(amount)
            )

        revenue_chart = {
            "labels": chart_labels,
            "values": chart_values,
        }

        # ====================================================
        # RECENT ORDERS
        # ====================================================

        recent_orders = (
            vendor_orders
            .select_related(
                "customer",
                "customer__user",
            )
            .annotate(
                vendor_total=Sum(
                    "items__subtotal",
                    filter=Q(
                        items__product__vendor=vendor
                    ),
                ),
                item_count=Sum(
                    "items__quantity",
                    filter=Q(
                        items__product__vendor=vendor
                    ),
                ),
            )
            .order_by(
                "-ordered_at"
            )[:5]
        )

        # ====================================================
        # TEMPLATE-FRIENDLY ORDER DATA
        # ====================================================

        for order in recent_orders:

            order.customer_name = (
                order.customer.full_name
                if order.customer
                else "Guest Customer"
            )

            order.status = (
                order.order_status.lower()
            )

            order.created_at = (
                order.ordered_at
            )

            order.total = (
                order.vendor_total
                or Decimal("0.00")
            )

            order.item_count = (
                order.item_count
                or 0
            )

        # ====================================================
        # CONTEXT
        # ====================================================

        context.update({

            # Revenue
            "revenue_30d": revenue_30d,
            "revenue_delta": revenue_delta,
            "revenue_delta_direction": (
                revenue_delta_direction
            ),

            # Orders
            "orders_30d": orders_30d,
            "orders_delta": orders_delta,
            "orders_delta_direction": (
                orders_delta_direction
            ),

            # Status
            "pending_orders": pending_orders,
            "cancelled_orders": cancelled_orders,

            # Stock
            "low_stock_count": low_stock_count,
            "low_stock_items": low_stock_items,
            "low_stock_threshold": (
                LOW_STOCK_THRESHOLD
            ),

            # Recent orders
            "recent_orders": recent_orders,

            # Chart
            "revenue_chart": revenue_chart,
        })

        return context


class VendorProfileView(LoginRequiredMixin, TemplateView):
    template_name = "Vendor/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        vendor = self.request.user.vendor
        context["vendor"] = vendor

        return context




    