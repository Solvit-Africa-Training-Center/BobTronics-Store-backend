from django.contrib import admin
from .models import Category, Product, ProductImage


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("category_id", "name", "created_at")
    search_fields = ("name", "description")
    ordering = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("product_id", "name", "category", "brand", "price", "stock_quantity", "is_available", "created_at")
    list_filter = ("category", "brand", "is_available", "created_at")
    search_fields = ("name", "brand", "description")
    list_editable = ("price", "stock_quantity", "is_available")
    inlines = [ProductImageInline]


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ("image_id", "product", "image_url", "is_primary", "created_at")
    list_filter = ("is_primary", "created_at")
    search_fields = ("product__name", "image_url")
