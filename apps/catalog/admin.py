from django.contrib import admin

from .models import Category, Product, ProductImage, StockMovement


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "brand", "price", "stock_quantity", "is_available")
    list_filter = ("category", "brand", "is_available")
    search_fields = ("name", "brand")
    inlines = [ProductImageInline]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "movement_id",
        "product",
        "movement_type",
        "source",
        "quantity_change",
        "quantity_before",
        "quantity_after",
        "actor",
        "created_at",
    )
    list_filter = ("movement_type", "source", "created_at")
    search_fields = ("product__name", "reason", "reference_id", "actor__email")
    readonly_fields = (
        "product",
        "movement_type",
        "source",
        "quantity_change",
        "quantity_before",
        "quantity_after",
        "reason",
        "reference_id",
        "actor",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
