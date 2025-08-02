from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils.safestring import mark_safe
import json
from .models import Product, Cart, CartItem

def product_list(request):
    """Display all active products with pagination and filtering"""
    products = Product.objects.filter(is_active=True)
    
    # Get filter parameters
    category_filter = request.GET.get('category')
    search_query = request.GET.get('search')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')
    sort_by = request.GET.get('sort', 'name')
    
    # Apply filters
    if category_filter:
        products = products.filter(category=category_filter)
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    if price_min:
        try:
            products = products.filter(price__gte=float(price_min))
        except ValueError:
            pass
    
    if price_max:
        try:
            products = products.filter(price__lte=float(price_max))
        except ValueError:
            pass
    
    # Apply sorting
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'oldest':
        products = products.order_by('created_at')
    else:
        products = products.order_by('name')
    
    # Pagination
    paginator = Paginator(products, 6)  # Show 6 products per page
    page = request.GET.get('page')
    
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    
    # Get all categories for filter dropdown
    categories = Product.CATEGORY_CHOICES
    
    context = {
        'products': products_page,
        'categories': categories,
        'current_category': category_filter,
        'current_search': search_query,
        'current_price_min': price_min,
        'current_price_max': price_max,
        'current_sort': sort_by,
        'total_products': paginator.count,
    }
    
    return render(request, 'shop/product_list.html', context)

def product_detail(request, product_id):
    """Display product details"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    return render(request, 'shop/product_detail.html', {'product': product})

@login_required
def cart_view(request):
    """Display user's cart"""
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'shop/cart.html', {'cart': cart})

@login_required
@require_POST
def add_to_cart(request, product_id):
    """Add product to cart"""
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity > product.stock_quantity:
        messages.error(request, f'Only {product.stock_quantity} items available in stock.')
        return redirect('shop:product_detail', product_id=product_id)
    
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': quantity}
    )
    
    if not created:
        new_quantity = cart_item.quantity + quantity
        if new_quantity > product.stock_quantity:
            messages.error(request, f'Cannot add more items. Only {product.stock_quantity} available.')
            return redirect('shop:product_detail', product_id=product_id)
        cart_item.quantity = new_quantity
        cart_item.save()
    
    messages.success(request, f'{product.name} added to cart!')
    return redirect('shop:cart')

@login_required
@require_POST
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    quantity = int(request.POST.get('quantity', 1))
    
    if quantity <= 0:
        cart_item.delete()
        messages.success(request, 'Item removed from cart.')
    elif quantity > cart_item.product.stock_quantity:
        messages.error(request, f'Only {cart_item.product.stock_quantity} items available.')
    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, 'Cart updated successfully.')
    
    return redirect('shop:cart')

@login_required
@require_POST
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    product_name = cart_item.product.name
    cart_item.delete()
    messages.success(request, f'{product_name} removed from cart.')
    return redirect('shop:cart')

@login_required
def checkout(request):
    """Display checkout page with cart data for frontend payment processing"""
    cart = get_object_or_404(Cart, user=request.user)
    
    if not cart.items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('shop:cart')
    
    # Check stock availability
    for item in cart.items.all():
        if item.quantity > item.product.stock_quantity:
            messages.error(request, f'Insufficient stock for {item.product.name}. Only {item.product.stock_quantity} available.')
            return redirect('shop:cart')
    
    # Prepare payment data for frontend
    payment_data = {
        'amount': float(cart.total_amount),
        'currency': 'USD',
        'customer_email': request.user.email,
        'description': f'Order for {cart.total_items} items',
        'callback_url': request.build_absolute_uri(reverse('shop:payment_success')),
        'cancel_url': request.build_absolute_uri(reverse('shop:payment_cancel'))
    }
    
    # Store cart_id in session for later verification
    request.session['cart_id'] = cart.id
    
    context = {
        'cart': cart,
        'payment_data': mark_safe(json.dumps(payment_data)),
        'api_endpoint': 'http://localhost:8002/checkout/make-payment/',
        'auth_token': 'pk_merchant_552ca963-c8f7-478f-9973-255c4339aab2_9Y935b10MWoVvTb9:O_mGxcZ1T-P2_lvjZQlDMXP6tvNNF3Do8HgWuQgVcxQ'
    }
    
    return render(request, 'shop/checkout.html', context)

@login_required
def payment_success(request):
    """Handle successful payment"""
    # Get session_id from URL parameters (sent by payment gateway)
    session_id = request.GET.get('session_id')
    cart_id = request.session.get('cart_id')
    
    if session_id and cart_id:
        try:
            cart = Cart.objects.get(id=cart_id, user=request.user)
            
            # Update stock quantities
            for item in cart.items.all():
                product = item.product
                product.stock_quantity -= item.quantity
                product.save()
            
            # Clear cart
            cart.items.all().delete()
            
            # Clear session data
            if 'cart_id' in request.session:
                del request.session['cart_id']
            
            messages.success(request, 'Payment successful! Your order has been processed.')
            return render(request, 'shop/payment_success.html', {'session_id': session_id})
        
        except Cart.DoesNotExist:
            messages.error(request, 'Cart not found.')
    
    messages.error(request, 'Payment verification failed.')
    return redirect('shop:cart')

@login_required
def payment_cancel(request):
    """Handle cancelled payment"""
    # Clear session data
    if 'payment_session_id' in request.session:
        del request.session['payment_session_id']
    if 'cart_id' in request.session:
        del request.session['cart_id']
    
    messages.info(request, 'Payment was cancelled.')
    return redirect('shop:cart')
