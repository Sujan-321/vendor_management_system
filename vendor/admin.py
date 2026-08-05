from django.contrib import admin
from .models import Vendor, Category, Product, ProductImage, ProductSpecification, Coupon

admin.site.register(Vendor)
admin.site.register(Category)
admin.site.register(Product)
admin.site.register(ProductImage)
admin.site.register(ProductSpecification)
admin.site.register(Coupon)