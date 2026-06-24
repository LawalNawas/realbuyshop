from decimal import Decimal
from django.conf import settings
from django.http import JsonResponse
from .models import ProductVariant

class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, variant, quantity=1, override_quantity=False):
        variant_id = str(variant.id)
        if variant_id not in self.cart:
            self.cart[variant_id] = {'quantity': 0, 'price': str(variant.price)}
        
        if override_quantity:
            self.cart[variant_id]['quantity'] = quantity
        else:
            self.cart[variant_id]['quantity'] += quantity
        self.save()

    def save(self):
        self.session.modified = True

    def remove(self, variant):
        variant_id = str(variant.id)
        if variant_id in self.cart:
            del self.cart[variant_id]
            self.save()

    def save(self):
        self.session.modified = True

    def remove(self, variant):
        variant_id = str(variant.id)
        if variant_id in self.cart:
            del self.cart[variant_id]
            self.save()

     def get_total_price(self):
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        self.save()

def validate_cart(cart_items):
    for item in cart_items:
        variant = ProductVariant.objects.get(id=item["variant_id"])

        if variant.stock < item["quantity"]:
            return {
                "valid": False,
                "message": f"Not enough stock for {variant}"
            }

    return {"valid": True}