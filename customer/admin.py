from django.contrib import admin
from .models import Customer, Cart, CartItem, Wishlist, ShippingAddress, Order, OrderItem, Payment, ProductReview
# Register your models here.


admin.site.register(Customer)
admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(Wishlist)
admin.site.register(ShippingAddress)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Payment)
admin.site.register(ProductReview)