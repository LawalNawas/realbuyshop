from django.contrib import admin
from .models import Category, Product, ProductVariant, Order, OrderItem


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


class ProductVariantInline(admin.TabularInline):
    model = ProductVariant
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['name', 'description']
    autocomplete_fields = ['category']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductVariantInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ['product']
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'full_name',
        'email',
        'total_amount',
        'status',
        'created_at'
    ]
    list_filter = ['status', 'created_at']
    search_fields = [
        'id',
        'full_name',
        'email',
        'payment_reference'
    ]
    readonly_fields = [
        'payment_reference',
        'total_amount',
        'created_at'
    ]
    inlines = [OrderItemInline]
# Register your models here.
