from django.shortcuts import render
from django.views.generic import View, TemplateView, ListView, CreateView, DetailView, DeleteView, UpdateView
from .models import Product, ProductImage, ProductSpecification
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .forms import ProductForm, ProductImageForm
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.db import transaction



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








    