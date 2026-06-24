import requests
import stripe
from django.conf import settings
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Cart
from django.contrib.auth.decorators import login_required
from .models import ProductVariant, Cart, CartItem
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login
from .forms import RegisterForm
from .models import Product, Cart, CartItem, Order
from django.db.models import Q, F, Case, When, Value, IntegerField


stripe.api_key = settings.STRIPE_SECRET_KEY



def home(request):
    products = Product.objects.filter(is_active=True)

    return render(
        request,
        'users/home.html',
        {
            'products': products
        }
    )


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)

            print("REGISTER SUCCESS")  # DEBUG LINE

            return redirect('home')
        else:
            print(form.errors)  # DEBUG

    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})

def product_list(request):

    products = Product.objects.filter(
        is_active=True
    )

    query = request.GET.get('q')

    if query:
        products = products.filter(
            name__icontains=query
        )

    return render(
    request,
    'users/product_list.html',
    {
        'products': products
    }
)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug)

    return render(
        request,
        'users/product_detail.html',
        {'product': product}
    )

@login_required
def profile_view(request):

    return render(
        request,
        'users/profile.html'
    )



def product_search(request):
    query = request.GET.get('q', '')

    products = Product.objects.filter(
        name__icontains=query,
        is_active=True
    )

    return render(request, 'search_results.html', {
        'products': products,
        'query': query
    })



def search_results(request):

    query = request.GET.get('q', '')

    products = Product.objects.filter(
        is_active=True
    )

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    return render(
        request,
        'users/search_results.html',
        {
            'products': products,
            'query': query
        }
    )



@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    cart, created = Cart.objects.get_or_create(user=request.user)

    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart,
        product=product
    )

    if not item_created:
        cart_item.quantity += 1
        cart_item.save()

    return redirect('cart')



def cart_view(request):
    cart, created = Cart.objects.get_or_create(
    user=request.user
)

    cart_items = cart.items.all()

    total_price = sum(
    item.product.price * item.quantity
    for item in cart_items
)

    return render(
        request,
        'users/cart.html',
        {
            'cart_items': cart_items,
            'total_price': total_price
        }
    )



@login_required
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(
    user=request.user
)
    items = CartItem.objects.filter(cart=cart)

    return render(request, 'cart_detail.html', {
        'items': items
    })


@login_required
def remove_from_cart(request, item_id):

    item = get_object_or_404(
        CartItem,
        id=item_id,
        cart__user=request.user
    )

    item.delete()

    return redirect('cart')



def create_checkout_session(request, order_id):
    order = Order.objects.get(id=order_id)
    
    # Convert total decimal amount to cents for Stripe
    amount_in_cents = int(order.total_amount * 100)
    
    checkout_session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'usd',
                'product_data': {'name': f"Order #{order.id}"},
                'unit_amount': amount_in_cents,
            },
            'quantity': 1,
        }],
         mode='payment',
        success_url=request.build_absolute_uri(reverse('payment_success')) + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=request.build_absolute_uri(reverse('payment_cancel')),
        client_reference_id=str(order.id)
    )
    
    order.payment_reference = checkout_session.id
    order.save()
    return redirect(checkout_session.url, code=303)

@login_required
def initiate_payment(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)

    url = "https://api.paystack.co/transaction/initialize"

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "email": order.email,
        "amount": int(order.total_amount * 100),  # Paystack uses kobo
        "callback_url": request.build_absolute_uri(
            f"/payment/verify/{order.id}/"
        )
    }

    response = requests.post(url, json=data, headers=headers)
    res_data = response.json()

    if res_data["status"]:
        return redirect(res_data["data"]["authorization_url"])

    return redirect("checkout")



@login_required
def verify_payment(request, order_id):
    order = Order.objects.get(id=order_id, user=request.user)

    reference = request.GET.get("reference")

    url = f"https://api.paystack.co/transaction/verify/{reference}"

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    }

    response = requests.get(url, headers=headers)
    res_data = response.json()

    if res_data["data"]["status"] == "success":

        order.status = "Paid"
        order.payment_reference = reference
        order.save()

        # OPTIONAL: reduce stock
        for item in order.items.all():
             Product.objects.filter(id=item.product.id).update(
            stock=Case(
                When(stock__gte=item.quantity, then=F('stock') - item.quantity),
                default=Value(0),
                output_field=IntegerField()
            )
        )

        return render(request, "payment/success.html", {"order": order})

    return render(request, "payment/failed.html", {"order": order})



@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        order_id = session.get('client_reference_id')

        # Fulfill the order safely using atomic transactions
        order = Order.objects.get(id=order_id)
        order.status = 'Paid'
        order.save()
        
    return HttpResponse(status=200)


@login_required
def checkout(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart)

    if not cart_items.exists():
        return JsonResponse({"error": "Your cart is empty."}, status=400)

    total_price = sum(
        item.product.price * item.quantity
        for item in cart_items
    )

    if request.method == "POST":
        full_name = request.POST.get("full_name")
        email = request.POST.get("email")
        address = request.POST.get("address")

        order = Order.objects.create(
            user=request.user,
            full_name=full_name,
            email=email,
            address=address,
            total_amount=total_price
        )

        for item in cart_items:
            Product.objects.filter(id=item.product.id, stock__gte=item.quantity).update(
                stock=F('stock') - item.quantity
            )

            order.items.create(
                product=item.product,
                price=item.product.price,
                quantity=item.quantity
            )

        cart_items.delete()

        return redirect("order_success", order_id=order.id)

    return render(
        request,
        "users/checkout.html",
        {
            "cart_items": cart_items,
            "total_price": total_price,
        }
    )
    # continue checkout




@login_required
def orders_view(request):

    orders = Order.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(
        request,
        'users/orders.html',
        {
            'orders': orders
        }
    )


@login_required
def order_detail(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    for item in order.items.all():
        Product.objects.filter(
        id=item.product.id
    )
    
    return render(
        request,
        'users/order_detail.html',
        {
            'order': order
        }
    )



@login_required
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    return render(
        request,
        'users/order_success.html',
        {
            'order': order
        }
    )
# Create your views here.
