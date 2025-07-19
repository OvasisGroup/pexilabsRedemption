from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('pay/<str:slug>/', views.payment_link_view, name='payment_link'),
]
