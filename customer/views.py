from django.db.models import F, Q, Count
from django.views.generic import View, ListView, TemplateView, CreateView
from django.utils import timezone
from datetime import timedelta
from vendor.models import Category, Product, Coupon
from customer.models import Customer, Order, Wishlist, Cart, CartItem, OrderItem, ShippingAddress, Payment
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from decimal import Decimal
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.core.paginator import Paginator   

import base64
import hashlib
import hmac
import json
import uuid
import requests

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse


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

class FilterMixin:

    def get_category_queryset(self):
        return (
            Category.objects
            .filter(is_active=True)
            .annotate(
                product_count=Count(
                    "products",
                    filter=Q(
                        products__is_active=True,
                        products__vendor__is_active=True,
                        products__vendor__approval_status="APPROVED",
                    )
                )
            )
        )

    def get_selected_categories(self):
        """
            if user click multiple category through filter then following url come as request
                ?category=fashion&category=electronics&category=shoes
            
            then getlist() function convert that url into something like this
                ["fashion", "electronics", "shoes"]
        """
        return self.request.GET.getlist("category") # if user 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        selected_categories = self.get_selected_categories()

        categories = self.get_category_queryset()

        # Mark selected categories as checked
        for category in categories:
            category.checked = category.slug in selected_categories

        context["categories"] = categories
        context["selected_categories"] = selected_categories

        return context

class ShopView(FilterMixin, ListView):

    model = Product
    template_name = "Customer/shop.html"
    context_object_name = "products"
    paginate_by = 12

    def get_queryset(self):

        queryset = (
            Product.objects
            .filter(
                is_active=True,
                vendor__is_active=True,
                vendor__approval_status="APPROVED",
            )
            .select_related(
                "vendor",
                "category",
            )
        )

        # -----------------------------
        # Category filter
        # -----------------------------
        categories = self.request.GET.getlist("category")

        if categories:
            queryset = queryset.filter(
                category__slug__in=categories
            )

        # -----------------------------
        # Minimum price
        # -----------------------------
        min_price = self.request.GET.get("min_price")

        if min_price:
            queryset = queryset.filter(
                price__gte=min_price
            )

        # -----------------------------
        # Maximum price
        # -----------------------------
        max_price = self.request.GET.get("max_price")

        if max_price:
            queryset = queryset.filter(
                price__lte=max_price
            )

        # -----------------------------
        # Deal / sale filter
        # -----------------------------
        deal = self.request.GET.get("deal")

        if deal == "true":
            queryset = queryset.filter(
                discount_price__isnull=False,
                discount_price__lt=F("price"),
            )

        return queryset    


class SearchResultView(ListView):

    model = Product
    template_name = "product/search_result.html"
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
    template_name = "order/order_history.html"
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

class OrderDetailView(LoginRequiredMixin, View):

    template_name = "order/order_detail.html"

    def get(self, request, *args, **kwargs):

        customer = get_object_or_404(
            Customer,
            user=request.user
        )

        order = get_object_or_404(
            Order.objects
            .select_related(
                "shipping_address",
                "payment",
            )
            .prefetch_related(
                "items__product"
            ),
            id=kwargs["pk"],
            customer=customer,
        )

        return render(
            request,
            self.template_name,
            {
                "order": order,
            }
        )

class OrderListView(LoginRequiredMixin, View):

    template_name = "order/order_list.html"

    def get(self, request, *args, **kwargs):

        customer = get_object_or_404(
            Customer,
            user=request.user
        )

        orders = (
            Order.objects
            .filter(customer=customer)
            .select_related(
                "shipping_address",
                "payment",
            )
            .order_by("-ordered_at")
        )

        return render(
            request,
            self.template_name,
            {
                "orders": orders,
            }
        )


class OrderCancelView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):

        customer = get_object_or_404(
            Customer,
            user=request.user
        )

        order = get_object_or_404(
            Order,
            id=kwargs["pk"],
            customer=customer,
        )

        if order.order_status not in ["PENDING", "CONFIRMED"]:
            messages.error(
                request,
                "This order cannot be cancelled."
            )

            return redirect("customer:order_detail", order.id)

        order.order_status = "CANCELLED"
        order.save(update_fields=["order_status"])

        messages.success(
            request,
            f"Order #{order.order_number} has been cancelled successfully."
        )

        return redirect("customer:order_list")



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

        if request.POST.get("buy_now") == "1":
            return redirect("customer:checkout")
        

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


def generate_esewa_signature(total_amount, transaction_uuid, product_code):
    message = (
        f"total_amount={total_amount},"
        f"transaction_uuid={transaction_uuid},"
        f"product_code={product_code}"
    )

    signature = hmac.new(
        settings.ESEWA_SECRET_KEY.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).digest()

    return base64.b64encode(signature).decode("utf-8")

def verify_esewa_transaction(
    transaction_uuid,
    total_amount
):

    

    params = {
        "product_code": settings.ESEWA_PRODUCT_CODE,
        "total_amount": f"{total_amount:.2f}",
        "transaction_uuid": transaction_uuid,
    }

    try:

        response = requests.get(
            settings.ESEWA_STATUS_URL,
            params=params,
            timeout=10,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException:

        return {
            "status": "ERROR"
        }



class CreateOrderView(LoginRequiredMixin, View):

    SHIPPING_CHARGE = Decimal("150.00")
    FREE_SHIPPING_AMOUNT = Decimal("2000.00")
    TAX_PERCENT = Decimal("0")

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        customer = get_object_or_404(
            Customer,
            user=request.user
        )

        # --------------------------------------------------
        # 1. Get customer's cart
        # --------------------------------------------------
        cart = get_object_or_404(
            Cart,
            customer=customer
        )

        cart_items = (
            CartItem.objects
            .filter(cart=cart)
            .select_related("product")
        )

        if not cart_items.exists():
            messages.error(
                request,
                "Your cart is empty."
            )
            return redirect("customer:cart")

        # --------------------------------------------------
        # 2. Validate stock and calculate subtotal
        # --------------------------------------------------
        subtotal = Decimal("0.00")

        for item in cart_items:

            if item.product.stock < item.quantity:
                messages.error(
                    request,
                    f"Only {item.product.stock} units of "
                    f"{item.product.name} are available."
                )
                return redirect("customer:cart")

            subtotal += item.subtotal

        # --------------------------------------------------
        # 3. Calculate shipping
        # --------------------------------------------------
        if subtotal >= self.FREE_SHIPPING_AMOUNT:
            shipping = Decimal("0.00")
        else:
            shipping = self.SHIPPING_CHARGE

        # --------------------------------------------------
        # 4. Calculate tax
        # --------------------------------------------------
        tax = (
            subtotal *
            self.TAX_PERCENT /
            Decimal("100")
        )

        # --------------------------------------------------
        # 5. Calculate discount
        # --------------------------------------------------
        discount = Decimal("0.00")

        promo_code = request.session.get("promo_code")

        if promo_code:

            try:
                coupon = Coupon.objects.get(
                    code=promo_code,
                    is_active=True
                )

                if (
                    coupon.valid_from <= timezone.localdate()
                    and
                    coupon.valid_to >= timezone.localdate()
                    and
                    subtotal >= coupon.minimum_purchase
                ):
                    discount = (
                        subtotal *
                        Decimal(coupon.discount) /
                        Decimal("100")
                    )

            except Coupon.DoesNotExist:
                promo_code = None

        # --------------------------------------------------
        # 6. Calculate final order total
        # --------------------------------------------------
        total = (
            subtotal
            + shipping
            + tax
            - discount
        )

        if total < Decimal("0.00"):
            total = Decimal("0.00")

        # --------------------------------------------------
        # 7. Validate shipping address from checkout form
        # --------------------------------------------------
        full_name = request.POST.get("full_name", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        country = request.POST.get("country", "").strip()
        postal_code = request.POST.get("postal_code", "").strip()

        if not full_name:
            messages.error(
                request,
                "Full name is required."
            )
            return redirect("customer:checkout")

        if not phone_number:
            messages.error(
                request,
                "Phone number is required."
            )
            return redirect("customer:checkout")

        if not address:
            messages.error(
                request,
                "Address is required."
            )
            return redirect("customer:checkout")

        if not city:
            messages.error(
                request,
                "City is required."
            )
            return redirect("customer:checkout")

        if not country:
            messages.error(
                request,
                "Country is required."
            )
            return redirect("customer:checkout")

        if not postal_code:
            messages.error(
                request,
                "Postal code is required."
            )
            return redirect("customer:checkout")

        # --------------------------------------------------
        # 8. Create shipping address
        # --------------------------------------------------
        shipping_address = ShippingAddress.objects.create(
            customer=customer,
            full_name=full_name,
            phone_number=phone_number,
            address=address,
            city=city,
            state=state,
            country=country,
            postal_code=postal_code,
            is_default=False,
        )

        # --------------------------------------------------
        # 9. Generate unique order number
        # --------------------------------------------------
        order_number = (
            f"ORD-{timezone.now().strftime('%Y%m%d%H%M%S')}-"
            f"{uuid.uuid4().hex[:6].upper()}"
        )

        # --------------------------------------------------
        # 10. Create order
        # --------------------------------------------------
        order = Order.objects.create(
            customer=customer,
            shipping_address=shipping_address,
            order_number=order_number,
            subtotal=subtotal,
            shipping_charge=shipping,
            discount=discount,
            total=total,
            order_status="PENDING",
            payment_status="PENDING",
        )

        # --------------------------------------------------
        # 11. Create order items
        # --------------------------------------------------
        for item in cart_items:

            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.final_price,
                subtotal=item.subtotal,
            )

        # --------------------------------------------------
        # 12. Do NOT create Payment here.
        # PaymentMethodView will create/update it after
        # the customer selects eSewa/Khalti/COD/Card.
        # --------------------------------------------------

        return redirect(
            "customer:payment_method",
            order.id
        )


class PaymentMethodView(LoginRequiredMixin, View):

    template_name = "payment/payment_method.html"

    def get(self, request, *args, **kwargs):

        customer = get_object_or_404(
            Customer,
            user=request.user
        )

        order = get_object_or_404(
            Order,
            id=kwargs["order_id"],
            customer=customer
        )

        # Make sure this order actually has a Payment.
        payment = Payment.objects.filter(
            order=order
        ).first()

        context = {
            "order": order,
            "payment": payment,
        }

        return render(
            request,
            self.template_name,
            context
        )

    @transaction.atomic
    def post(self, request, *args, **kwargs):

        # --------------------------------------------------
        # 1. Get customer
        # --------------------------------------------------
        customer = get_object_or_404(
            Customer,
            user=request.user
        )

        # --------------------------------------------------
        # 2. Get customer's order
        # --------------------------------------------------
        order = get_object_or_404(
            Order,
            id=kwargs["order_id"],
            customer=customer
        )

        # --------------------------------------------------
        # 3. Get selected payment method
        # --------------------------------------------------
        payment_method = request.POST.get(
            "payment_method",
            ""
        ).strip().lower()

        # --------------------------------------------------
        # 4. Validate payment method
        # --------------------------------------------------
        payment_method_map = {
            "esewa": "ESEWA",
            "khalti": "KHALTI",
            "cod": "COD",
            "card": "STRIPE",
        }

        if payment_method not in payment_method_map:

            messages.error(
                request,
                "Please select a valid payment method."
            )

            return redirect(
                "customer:payment_method",
                order_id=order.id
            )

        payment_method_code = payment_method_map[
            payment_method
        ]

        # --------------------------------------------------
        # 5. Get or create Payment
        # --------------------------------------------------
        payment, created = Payment.objects.get_or_create(
            order=order,
            defaults={
                "payment_method": payment_method_code,
                "amount": order.total,
            }
        )

        # --------------------------------------------------
        # 6. Update existing payment
        # --------------------------------------------------
        if not created:

            payment.payment_method = payment_method_code
            payment.amount = order.total

            # If customer chooses another payment method,
            # remove the old transaction ID.
            payment.transaction_id = ""

            payment.paid_at = None

            payment.save(
                update_fields=[
                    "payment_method",
                    "amount",
                    "transaction_id",
                    "paid_at",
                ]
            )

        # --------------------------------------------------
        # 7. eSewa
        # --------------------------------------------------
        if payment_method == "esewa":

            return redirect(
                "customer:esewa_payment",
                order_id=order.id
            )

        # --------------------------------------------------
        # 8. Khalti
        # --------------------------------------------------
        if payment_method == "khalti":

            messages.info(
                request,
                "Khalti payment integration is not implemented yet."
            )

            return redirect(
                "customer:payment_method",
                order_id=order.id
            )

        # --------------------------------------------------
        # 9. Card / Stripe
        # --------------------------------------------------
        if payment_method == "card":

            messages.info(
                request,
                "Card payment integration is not implemented yet."
            )

            return redirect(
                "customer:payment_method",
                order_id=order.id
            )

        # --------------------------------------------------
        # 10. Cash on Delivery
        # --------------------------------------------------
        if payment_method == "cod":

            # Re-check stock before confirming COD order.
            for item in order.items.select_related("product"):

                if not item.product:
                    continue

                if item.product.stock < item.quantity:

                    messages.error(
                        request,
                        f"Only {item.product.stock} units of "
                        f"{item.product.name} are available."
                    )

                    return redirect(
                        "customer:cart"
                    )

            # --------------------------------------------------
            # Reduce stock
            # --------------------------------------------------
            for item in order.items.select_related("product"):

                if not item.product:
                    continue

                item.product.stock -= item.quantity

                item.product.save(
                    update_fields=["stock"]
                )

            # --------------------------------------------------
            # Update order
            # --------------------------------------------------
            order.order_status = "CONFIRMED"
            order.payment_status = "PENDING"

            order.save(
                update_fields=[
                    "order_status",
                    "payment_status",
                ]
            )

            # --------------------------------------------------
            # Clear cart
            # --------------------------------------------------
            CartItem.objects.filter(
                cart__customer=customer
            ).delete()

            # --------------------------------------------------
            # Remove promo code
            # --------------------------------------------------
            request.session.pop(
                "promo_code",
                None
            )

            messages.success(
                request,
                "Your order has been placed successfully."
            )

            return redirect(
                "customer:order_history"
            )

        return redirect(
            "customer:payment_method",
            order_id=order.id
        )




class EsewaPaymentView(LoginRequiredMixin, TemplateView):

    template_name = "payment/esewa_payment.html"

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        customer = get_object_or_404(
            Customer,
            user=self.request.user
        )

        order = get_object_or_404(
            Order,
            id=self.kwargs["order_id"],
            customer=customer
        )

        payment = get_object_or_404(
            Payment,
            order=order
        )

        if payment.payment_method != "ESEWA":
            messages.error(
                self.request,
                "Invalid payment method."
            )
            return context

        # Don't create a new UUID on every page refresh.
        transaction_uuid = (
            payment.transaction_id
            or f"{order.order_number}-{uuid.uuid4().hex[:8]}"
        )

        if not payment.transaction_id:
            payment.transaction_id = transaction_uuid
            payment.save(update_fields=["transaction_id"])

        product_code = settings.ESEWA_PRODUCT_CODE

        total_amount = f"{order.total:.2f}"

        signature = generate_esewa_signature(
            total_amount=total_amount,
            transaction_uuid=transaction_uuid,
            product_code=product_code,
        )

        success_url = self.request.build_absolute_uri(
            reverse(
                "customer:esewa_success"
            )
        )

        failure_url = self.request.build_absolute_uri(
            reverse(
                "customer:esewa_failure"
            )
        )

        context.update({
            "order": order,
            "payment": payment,
            "transaction_uuid": transaction_uuid,
            "merchant_code": product_code,
            "esewa_signature": signature,
            "esewa_url": settings.ESEWA_PAYMENT_URL,
            "success_url": success_url,
            "failure_url": failure_url,
        })

        return context


class EsewaSuccessView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):

        encoded_data = request.GET.get("data")

        if not encoded_data:
            messages.error(
                request,
                "Invalid eSewa response."
            )
            return redirect("customer:cart")

        try:
            decoded_data = base64.b64decode(
                encoded_data
            ).decode("utf-8")

            response_data = json.loads(decoded_data)

        except (
            ValueError,
            json.JSONDecodeError,
            UnicodeDecodeError
        ):
            messages.error(
                request,
                "Unable to read eSewa payment response."
            )
            return redirect("customer:cart")

        transaction_uuid = response_data.get(
            "transaction_uuid"
        )

        transaction_code = response_data.get(
            "transaction_code"
        )

        status = response_data.get(
            "status"
        )

        if not transaction_uuid:
            messages.error(
                request,
                "Invalid transaction."
            )
            return redirect("customer:cart")

        customer = get_object_or_404(
            Customer,
            user=request.user
        )

        payment = get_object_or_404(
            Payment,
            transaction_id=transaction_uuid,
            order__customer=customer
        )

        order = payment.order

        # Check the eSewa response itself first.
        if status != "COMPLETE":

            order.payment_status = "FAILED"
            order.save(update_fields=["payment_status"])

            return render(
                request,
                "payment/payment_fail.html",
                {
                    "order": order,
                    "payment": payment,
                    "error_reason": (
                        f"eSewa returned status: {status}"
                    ),
                }
            )

        # Verify the transaction with eSewa.
        verification = verify_esewa_transaction(
            transaction_uuid=transaction_uuid,
            total_amount=order.total,
        )

        if verification.get("status") != "COMPLETE":

            order.payment_status = "FAILED"
            order.save(update_fields=["payment_status"])

            return render(
                request,
                "payment/payment_fail.html",
                {
                    "order": order,
                    "payment": payment,
                    "error_reason": (
                        "eSewa transaction verification failed."
                    ),
                }
            )

        # Payment is verified.
        with transaction.atomic():

            payment.transaction_id = (
                verification.get("ref_id")
                or transaction_code
                or transaction_uuid
            )

            payment.amount = order.total
            payment.paid_at = timezone.now()

            payment.save(
                update_fields=[
                    "transaction_id",
                    "amount",
                    "paid_at",
                ]
            )

            order.payment_status = "PAID"
            order.order_status = "CONFIRMED"

            order.save(
                update_fields=[
                    "payment_status",
                    "order_status",
                ]
            )

            # Reduce stock
            for item in order.items.select_related("product"):

                if item.product:

                    item.product.stock = (
                        item.product.stock - item.quantity
                    )

                    item.product.save(
                        update_fields=["stock"]
                    )

            # Clear customer's cart
            CartItem.objects.filter(
                cart__customer=customer
            ).delete()

            request.session.pop(
                "promo_code",
                None
            )

        return render(
            request,
            "payment/payment_success.html",
            {
                "order": order,
                "payment": payment,
            }
        )


class EsewaFailureView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):

        transaction_uuid = request.GET.get(
            "transaction_uuid"
        )

        customer = get_object_or_404(
            Customer,
            user=request.user
        )

        payment = None

        if transaction_uuid:
            payment = Payment.objects.filter(
                transaction_id=transaction_uuid,
                order__customer=customer
            ).select_related("order").first()

        if not payment:

            messages.error(
                request,
                "Unable to identify the payment."
            )

            return redirect("customer:cart")

        order = payment.order

        if order.payment_status != "PAID":

            order.payment_status = "FAILED"
            order.save(
                update_fields=["payment_status"]
            )

        return render(
            request,
            "payment/payment_fail.html",
            {
                "order": order,
                "payment": payment,
                "error_reason": (
                    "The eSewa transaction was cancelled "
                    "or could not be completed."
                ),
            }
        )


class OrderHistoryView(LoginRequiredMixin, View):

    template_name = "order/order_history.html"

    def get(self, request, *args, **kwargs):

        customer = get_object_or_404(
            Customer,
            user=request.user
        )

        orders = (
            Order.objects
            .filter(customer=customer)
            .select_related(
                "shipping_address",
                "payment",
            )
            .prefetch_related(
                "items__product"
            )
            .order_by("-ordered_at")
        )

        # --------------------------------------------------
        # Filter by order status
        # --------------------------------------------------

        status = request.GET.get("status", "").strip().upper()

        if status:
            valid_statuses = {
                "PENDING",
                "CONFIRMED",
                "SHIPPED",
                "DELIVERED",
                "CANCELLED",
            }

            if status in valid_statuses:
                orders = orders.filter(
                    order_status=status
                )

        # --------------------------------------------------
        # Filter by date
        # --------------------------------------------------

        date_range = request.GET.get(
            "date_range",
            ""
        ).strip()

        today = timezone.localdate()

        if date_range == "30":

            start_date = today - timedelta(days=30)

            orders = orders.filter(
                ordered_at__date__gte=start_date
            )

        elif date_range == "90":

            start_date = today - timedelta(days=90)

            orders = orders.filter(
                ordered_at__date__gte=start_date
            )

        elif date_range == "365":

            start_date = today - timedelta(days=365)

            orders = orders.filter(
                ordered_at__date__gte=start_date
            )

        # --------------------------------------------------
        # Pagination
        # --------------------------------------------------

        paginator = Paginator(
            orders,
            10
        )

        page_number = request.GET.get(
            "page"
        )

        orders_page = paginator.get_page(
            page_number
        )

        return render(
            request,
            self.template_name,
            {
                "orders": orders_page,
            }
        )


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "Customer/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user

        customer = getattr(user, "customer", None)
        vendor = getattr(user, "vendor", None)

        context["customer"] = customer
        context["vendor"] = vendor

        return context



# class PaymentMethodView(LoginRequiredMixin, TemplateView):

#     template_name = "payment/payment_method.html"

#     def get_context_data(self, **kwargs):

#         context = super().get_context_data(**kwargs)

#         customer = get_object_or_404(
#             Customer,
#             user=self.request.user
#         )

#         order = get_object_or_404(
#             Order,
#             id=self.kwargs["order_id"],
#             customer=customer
#         )

#         context["order"] = order

#         return context



# class CreateOrderView(LoginRequiredMixin, View):

#     SHIPPING_CHARGE = Decimal("150.00")
#     FREE_SHIPPING_AMOUNT = Decimal("2000.00")
#     TAX_PERCENT = Decimal("0")

#     @transaction.atomic
#     def post(self, request, *args, **kwargs):

#         customer = get_object_or_404(
#             Customer,
#             user=request.user
#         )

#         cart = get_object_or_404(
#             Cart,
#             customer=customer
#         )

#         cart_items = (
#             CartItem.objects
#             .filter(cart=cart)
#             .select_related("product")
#         )

#         if not cart_items.exists():
#             messages.error(request, "Your cart is empty.")
#             return redirect("customer:cart")

#         subtotal = Decimal("0")

#         for item in cart_items:

#             if item.product.stock < item.quantity:
#                 messages.error(
#                     request,
#                     f"Only {item.product.stock} units of "
#                     f"{item.product.name} are available."
#                 )
#                 return redirect("customer:cart")

#             subtotal += item.subtotal

#         shipping = (
#             Decimal("0")
#             if subtotal >= self.FREE_SHIPPING_AMOUNT
#             else self.SHIPPING_CHARGE
#         )

#         tax = (
#             subtotal *
#             self.TAX_PERCENT /
#             Decimal("100")
#         )

#         discount = Decimal("0")

#         promo_code = request.session.get("promo_code")

#         if promo_code:

#             try:
#                 coupon = Coupon.objects.get(
#                     code=promo_code,
#                     is_active=True
#                 )

#                 if subtotal >= coupon.minimum_purchase:
#                     discount = (
#                         subtotal *
#                         Decimal(coupon.discount) /
#                         Decimal("100")
#                     )

#             except Coupon.DoesNotExist:
#                 promo_code = None

#         total = subtotal + shipping + tax - discount

#         # Use customer's default shipping address
#         shipping_address = (
#             ShippingAddress.objects
#             .filter(
#                 customer=customer,
#                 is_default=True
#             )
#             .first()
#         )

#         if not shipping_address:
#             shipping_address = (
#                 ShippingAddress.objects
#                 .filter(customer=customer)
#                 .first()
#             )

#         if not shipping_address:
#             messages.error(
#                 request,
#                 "Please add a shipping address before placing your order."
#             )
#             return redirect("customer:checkout")

#         order_number = (
#             f"ORD-{timezone.now().strftime('%Y%m%d%H%M%S')}-"
#             f"{uuid.uuid4().hex[:6].upper()}"
#         )

#         order = Order.objects.create(
#             customer=customer,
#             shipping_address=shipping_address,
#             order_number=order_number,
#             subtotal=subtotal,
#             shipping_charge=shipping,
#             discount=discount,
#             total=total,
#             order_status="PENDING",
#             payment_status="PENDING",
#         )

#         for item in cart_items:

#             OrderItem.objects.create(
#                 order=order,
#                 product=item.product,
#                 quantity=item.quantity,
#                 price=item.product.final_price,
#                 subtotal=item.subtotal,
#             )

#         # Payment is created as pending.
#         # paid_at should be NULL until payment succeeds.
#         Payment.objects.create(
#             order=order,
#             payment_method="ESEWA",
#             amount=total,
#             transaction_id="",
#         )

#         # Do not delete the cart yet.
#         # We will delete it only after successful payment.
#         return redirect(
#             "customer:payment_method",
#             order.id
#         )




