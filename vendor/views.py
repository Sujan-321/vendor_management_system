from django.shortcuts import render
from django.views.generic import View, TemplateView, ListView, CreateView, DetailView, DeleteView, UpdateView
from .models import Product, ProductImage, ProductSpecification, Vendor
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .forms import ProductForm, ProductImageForm, ShopInformationForm
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.db import transaction
from django.db.models import Count, Q, Prefetch, Sum
from customer.models import Order, OrderItem
from datetime import datetime
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db.models.functions import TruncDate



LOW_STOCK_THRESHOLD = 30


# Create your views here.
class HomeView(TemplateView):
    template_name = "Vendor/base.html"

class VendorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """
    Allow access only to authenticated users who have a Vendor profile.
    """

    def test_func(self):
        return hasattr(self.request.user, "vendor")

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



class ProductDeleteView(LoginRequiredMixin ,DeleteView):
    model = Product
    template_name = "Vendor/product/product_delete.html"
    context_object_name = "product"
    success_url = reverse_lazy("vendor:product_list")
    success_message = "Successfully delete the product."

    def get_queryset(self):
        return (
            Product.objects
            .filter(vendor__user=self.request.user)
            .select_related("vendor", "category")
        )


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "Vendor/product/product_update.html"
    context_object_name = "product"
    success_url = reverse_lazy("vendor:product_list")

    def get_queryset(self):
        return (
            Product.objects
            .filter(vendor__user=self.request.user)
            .select_related("vendor", "category")
        )

class ProductImageManageView(LoginRequiredMixin, View):

    template_name = "Vendor/product/product_images.html"

    def get_product(self, pk):
        return get_object_or_404(
            Product.objects.select_related(
                "vendor",
                "category",
            ),
            pk=pk,
            vendor__user=self.request.user,
        )

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



class ProductImageDeleteView(LoginRequiredMixin, View):

    def post(self, request, pk):

        image = get_object_or_404(
            ProductImage.objects.select_related(
                "product",
                "product__vendor",
            ),
            pk=pk,
            product__vendor__user=request.user,
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



# now this section for profile management of vendor app views

class ShopInformationUpdateView(LoginRequiredMixin, UpdateView):
    model = Vendor
    form_class = ShopInformationForm
    template_name = "Vendor/profile/shop_information.html"
    context_object_name = "vendor"

    def get_object(self, queryset=None):
        return self.request.user.vendor

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


class VendorOrderListView(VendorRequiredMixin, ListView):
    model = Order
    template_name = "Vendor/order/order_list.html"
    context_object_name = "orders"
    paginate_by = 10

    def get_queryset(self):
        vendor = self.request.user.vendor

        queryset = (
            Order.objects
            .filter(
                items__product__vendor=vendor
            )
            .select_related(
                "customer",
                "shipping_address",
                "payment",
            )
            .annotate(
                item_count=Count(
                    "items",
                    filter=Q(items__product__vendor=vendor),
                    distinct=True,
                )
            )
            .distinct()
            .order_by("-ordered_at")
        )

        # -------------------------
        # Search
        # -------------------------
        query = self.request.GET.get("q", "").strip()

        if query:
            queryset = queryset.filter(
                Q(order_number__icontains=query)
                | Q(customer__full_name__icontains=query)
                | Q(customer__user__email__icontains=query)
            )

        # -------------------------
        # Status filter
        # -------------------------
        status = self.request.GET.get("status", "").lower()

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

        # -------------------------
        # From date
        # -------------------------
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

        # -------------------------
        # To date
        # -------------------------
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

        # Convert model field names to names expected by template.
        for order in orders:
            order.customer_name = order.customer.full_name

            order.customer_email = (
                order.customer.user.email
                if order.customer.user
                else ""
            )

            order.status = order.order_status.lower()

            order.created_at = order.ordered_at

            order.is_paid = (
                order.payment_status == "PAID"
            )

        context["orders"] = orders

        return context



class VendorOrderDetailView(VendorRequiredMixin, DetailView):
    model = Order
    template_name = "Vendor/order/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        vendor = self.request.user.vendor

        return (
            Order.objects
            .filter(
                items__product__vendor=vendor
            )
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
            .distinct()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        order = context["order"]

        # -------------------------
        # Template-compatible fields
        # -------------------------
        order.customer_name = order.customer.full_name

        order.customer_email = (
            order.customer.user.email
            if order.customer.user
            else ""
        )

        order.customer_phone = order.customer.phone_number

        order.status = order.order_status.lower()

        order.created_at = order.ordered_at

        order.is_paid = (
            order.payment_status == "PAID"
        )

        # Shipping address
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

        # Payment information
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

        # Your model does not have tax.
        order.tax = 0

        # Your model uses shipping_charge.
        order.shipping = order.shipping_charge

        # Make OrderItem compatible with template.
        for item in order.items.all():
            item.unit_price = item.price

        context["default_timeline"] = self.get_status_timeline(order)

        return context

    def get_status_timeline(self, order):
        """
        Build a simple timeline based on the current order status.

        Your model does not currently have a separate status-history model,
        so exact timestamps for every status are not available.
        """

        status_order = [
            ("pending", "Order Placed"),
            ("confirmed", "Payment / Order Confirmed"),
            ("shipped", "Shipped"),
            ("delivered", "Delivered"),
        ]

        current_status = order.order_status.lower()

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

        for index, (status, label) in enumerate(status_order):

            if index == 0:
                timestamp = order.ordered_at.strftime(
                    "%b %d, %Y, %I:%M %p"
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


class VendorOrderStatusView(VendorRequiredMixin, DetailView):
    model = Order
    template_name = "Vendor/order/order_status.html"
    context_object_name = "order"

    def get_queryset(self):
        vendor = self.request.user.vendor

        return (
            Order.objects
            .filter(
                items__product__vendor=vendor
            )
            .select_related(
                "customer",
                "shipping_address",
            )
            .distinct()
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        order = context["order"]

        # Convert uppercase model value to lowercase
        # because the template uses lowercase values.
        order.status = order.order_status.lower()

        # Your Order model does not have tracking_number.
        order.tracking_number = ""

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        order = self.object

        new_status = request.POST.get("status", "").lower()

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

        # Prevent changing a cancelled order.
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


class VendorStockManagementView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "Vendor/stock/stock_management.html"
    context_object_name = "products"
    paginate_by = 10

    def get_queryset(self):
        vendor = self.request.user.vendor

        queryset = (
            Product.objects
            .filter(vendor=vendor)
            .select_related("category")
            .order_by("name")
        )

        # -------------------------
        # Search
        # -------------------------
        query = self.request.GET.get("q", "").strip()

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(sku__icontains=query)
            )

        # -------------------------
        # Stock filter
        # -------------------------
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

        vendor = self.request.user.vendor

        # Summary should represent the vendor's complete catalog,
        # not only the currently filtered products.
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

        # The template uses product.low_stock_threshold.
        # Product model doesn't actually contain this field,
        # so provide the value through context.
        context["low_stock_threshold"] = LOW_STOCK_THRESHOLD

        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        vendor = request.user.vendor

        # Only products belonging to the logged-in vendor
        # can be updated.
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
                f"{updated_count} product stock level(s) updated successfully."
            )
        else:
            messages.info(
                request,
                "No stock changes were made."
            )

        # Preserve search/filter after POST.
        query_string = request.META.get(
            "HTTP_REFERER"
        )

        if query_string:
            return redirect(query_string)

        return redirect(
            "vendor_stock_management"
        )


class VendorDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "Vendor/dashboard.html"

    # ---------------------------------------------------------
    # Statuses considered as genuine/valid orders
    # ---------------------------------------------------------
    VALID_ORDER_STATUSES = (
        "CONFIRMED",
        "SHIPPED",
        "DELIVERED",
    )

    def dispatch(self, request, *args, **kwargs):
        """
        Make sure the logged-in user actually has a vendor profile
        and that the vendor is active/approved.
        """

        if not hasattr(request.user, "vendor"):
            return redirect("accounts:login")

        vendor = request.user.vendor

        if not vendor.is_active:
            return redirect("accounts:login")

        if vendor.approval_status != "APPROVED":
            return redirect("vendor:vendor_profile")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        vendor = self.request.user.vendor
        now = timezone.now()

        # =====================================================
        # DATE RANGES
        # =====================================================

        current_30_start = now - timedelta(days=30)
        previous_30_start = now - timedelta(days=60)

        chart_start = now - timedelta(days=13)

        # =====================================================
        # VENDOR PRODUCTS
        # =====================================================

        vendor_products = Product.objects.filter(
            vendor=vendor
        )

        # =====================================================
        # ALL ORDERS THAT CONTAIN THIS VENDOR'S PRODUCTS
        #
        # IMPORTANT:
        # An Order belongs to a vendor if at least one
        # OrderItem contains a product belonging to that vendor.
        # =====================================================

        vendor_orders = (
            Order.objects
            .filter(
                items__product__vendor=vendor
            )
            .distinct()
        )

        # =====================================================
        # VALID VENDOR ORDERS
        #
        # Pending and cancelled orders are NOT genuine
        # completed/accepted sales for dashboard order count.
        # =====================================================

        valid_vendor_orders = vendor_orders.filter(
            order_status__in=self.VALID_ORDER_STATUSES
        )

        # =====================================================
        # CURRENT 30-DAY ORDERS
        # =====================================================

        current_orders = valid_vendor_orders.filter(
            ordered_at__gte=current_30_start
        )

        orders_30d = current_orders.count()

        # =====================================================
        # PREVIOUS 30-DAY ORDERS
        # =====================================================

        previous_orders = valid_vendor_orders.filter(
            ordered_at__gte=previous_30_start,
            ordered_at__lt=current_30_start,
        ).count()

        # =====================================================
        # ORDER DELTA
        # =====================================================

        if previous_orders > 0:
            orders_delta_value = (
                (orders_30d - previous_orders)
                / previous_orders
            ) * 100
        elif orders_30d > 0:
            orders_delta_value = 100
        else:
            orders_delta_value = 0

        orders_delta = f"{orders_delta_value:.1f}%"

        orders_delta_direction = (
            "up"
            if orders_delta_value > 0
            else "down"
            if orders_delta_value < 0
            else "flat"
        )

        # =====================================================
        # CURRENT 30-DAY VENDOR REVENUE
        #
        # Revenue is calculated from OrderItem.subtotal
        # belonging ONLY to this vendor.
        #
        # We deliberately do NOT use Order.total because
        # Order.total belongs to the customer's complete order
        # and may contain products from multiple vendors.
        # =====================================================

        current_vendor_items = (
            OrderItem.objects
            .filter(
                product__vendor=vendor,
                order__ordered_at__gte=current_30_start,
                order__order_status__in=self.VALID_ORDER_STATUSES,
            )
        )

        revenue_30d = (
            current_vendor_items.aggregate(
                total=Sum("subtotal")
            )["total"]
            or Decimal("0.00")
        )

        # =====================================================
        # PREVIOUS 30-DAY VENDOR REVENUE
        # =====================================================

        previous_vendor_items = (
            OrderItem.objects
            .filter(
                product__vendor=vendor,
                order__ordered_at__gte=previous_30_start,
                order__ordered_at__lt=current_30_start,
                order__order_status__in=self.VALID_ORDER_STATUSES,
            )
        )

        previous_revenue = (
            previous_vendor_items.aggregate(
                total=Sum("subtotal")
            )["total"]
            or Decimal("0.00")
        )

        # =====================================================
        # REVENUE DELTA
        # =====================================================

        if previous_revenue > 0:
            revenue_delta_value = (
                (revenue_30d - previous_revenue)
                / previous_revenue
            ) * 100

        elif revenue_30d > 0:
            revenue_delta_value = 100

        else:
            revenue_delta_value = 0

        revenue_delta = f"{revenue_delta_value:.1f}%"

        revenue_delta_direction = (
            "up"
            if revenue_delta_value > 0
            else "down"
            if revenue_delta_value < 0
            else "flat"
        )

        # =====================================================
        # PENDING ORDERS
        # =====================================================

        pending_orders = vendor_orders.filter(
            order_status="PENDING"
        ).count()

        # =====================================================
        # CANCELLED ORDERS
        # =====================================================

        cancelled_orders = vendor_orders.filter(
            order_status="CANCELLED"
        ).count()

        # =====================================================
        # LOW STOCK
        # =====================================================

        low_stock_queryset = vendor_products.filter(
            stock__gt=0,
            stock__lte=LOW_STOCK_THRESHOLD,
            is_active=True,
        )

        low_stock_count = low_stock_queryset.count()

        low_stock_items = (
            low_stock_queryset
            .order_by("stock", "name")[:5]
        )

        # =====================================================
        # REVENUE GRAPH - LAST 14 DAYS
        #
        # Database aggregation instead of hard-coded values.
        # =====================================================

        chart_items = (
            OrderItem.objects
            .filter(
                product__vendor=vendor,
                order__ordered_at__gte=chart_start,
                order__order_status__in=self.VALID_ORDER_STATUSES,
            )
            .annotate(
                order_date=TruncDate(
                    "order__ordered_at"
                )
            )
            .values("order_date")
            .annotate(
                revenue=Sum("subtotal")
            )
            .order_by("order_date")
        )

        # Convert database result into dictionary:
        # {
        #     date: revenue
        # }
        revenue_by_date = {
            row["order_date"]: row["revenue"]
            for row in chart_items
        }

        chart_labels = []
        chart_values = []

        # Generate every day, including days with zero sales.
        for i in range(14):

            current_date = (
                chart_start.date()
                + timedelta(days=i)
            )

            chart_labels.append(
                current_date.strftime("%b %d")
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

        # =====================================================
        # RECENT ORDERS
        #
        # We show recent vendor orders, including cancelled
        # orders so the vendor can see actual order activity.
        #
        # Pending orders are also visible here.
        # =====================================================

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
            .order_by("-ordered_at")[:5]
        )

        # =====================================================
        # TEMPLATE-FRIENDLY ORDER DATA
        # =====================================================

        for order in recent_orders:

            order.customer_name = (
                order.customer.full_name
                if order.customer
                else "Guest Customer"
            )

            order.status = order.order_status.lower()

            order.created_at = order.ordered_at

            order.total = (
                order.vendor_total
                or Decimal("0.00")
            )

            order.item_count = (
                order.item_count
                or 0
            )

        # =====================================================
        # CONTEXT
        # =====================================================

        context.update({

            # -------------------------------
            # Revenue
            # -------------------------------

            "revenue_30d": revenue_30d,
            "revenue_delta": revenue_delta,
            "revenue_delta_direction": revenue_delta_direction,

            # -------------------------------
            # Orders
            # -------------------------------

            "orders_30d": orders_30d,
            "orders_delta": orders_delta,
            "orders_delta_direction": orders_delta_direction,

            # -------------------------------
            # Order statuses
            # -------------------------------

            "pending_orders": pending_orders,
            "cancelled_orders": cancelled_orders,

            # -------------------------------
            # Stock
            # -------------------------------

            "low_stock_count": low_stock_count,
            "low_stock_items": low_stock_items,
            "low_stock_threshold": LOW_STOCK_THRESHOLD,

            # -------------------------------
            # Recent orders
            # -------------------------------

            "recent_orders": recent_orders,

            # -------------------------------
            # Chart
            # -------------------------------

            "revenue_chart": revenue_chart,
        })

        return context