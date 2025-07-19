"""
Example API views for Country model.
Add these to your authentication/views.py or create a separate api_views.py
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from authentication.models import Country


@api_view(['GET'])
@permission_classes([AllowAny])  # Countries can be public
def countries_list(request):
    """
    Get list of all countries with optional search
    
    Query Parameters:
    - search: Search by country name
    - popular: Return popular countries first (true/false)
    - limit: Limit number of results
    
    Example URLs:
    - /api/countries/
    - /api/countries/?search=united
    - /api/countries/?popular=true&limit=20
    """
    try:
        # Get query parameters
        search = request.GET.get('search', '').strip()
        popular = request.GET.get('popular', '').lower() == 'true'
        limit = request.GET.get('limit')
        
        # Base queryset
        queryset = Country.objects.all()
        
        # Apply search filter
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(code__icontains=search)
            )
        
        # Handle popular countries first
        if popular:
            popular_codes = ['US', 'CA', 'GB', 'AU', 'DE', 'FR', 'JP', 'CN', 'IN', 'BR', 'NG', 'ZA', 'KE', 'EG']
            popular_countries = queryset.filter(code__in=popular_codes).order_by('name')
            other_countries = queryset.exclude(code__in=popular_codes).order_by('name')
            
            # Combine popular first, then others
            countries_list = list(popular_countries) + list(other_countries)
        else:
            countries_list = list(queryset.order_by('name'))
        
        # Apply limit
        if limit:
            try:
                limit = int(limit)
                countries_list = countries_list[:limit]
            except ValueError:
                pass
        
        # Serialize data
        data = []
        for country in countries_list:
            data.append({
                'id': str(country.id),
                'name': country.name,
                'code': country.code,
                'phone_code': country.phone_code,
                'created_at': country.created_at.isoformat(),
            })
        
        return Response({
            'success': True,
            'count': len(data),
            'data': data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def country_detail(request, country_code):
    """
    Get details of a specific country by code
    
    Example: /api/countries/US/
    """
    try:
        country = Country.objects.get(code=country_code.upper())
        
        data = {
            'id': str(country.id),
            'name': country.name,
            'code': country.code,
            'phone_code': country.phone_code,
            'created_at': country.created_at.isoformat(),
            'updated_at': country.updated_at.isoformat(),
        }
        
        return Response({
            'success': True,
            'data': data
        })
        
    except Country.DoesNotExist:
        return Response({
            'success': False,
            'error': f'Country with code "{country_code}" not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def countries_by_phone_code(request, phone_code):
    """
    Get countries by phone code
    
    Example: /api/countries/phone/+1/
    """
    try:
        # Ensure phone code starts with +
        if not phone_code.startswith('+'):
            phone_code = '+' + phone_code
            
        countries = Country.objects.filter(phone_code=phone_code).order_by('name')
        
        if not countries.exists():
            return Response({
                'success': False,
                'error': f'No countries found with phone code "{phone_code}"'
            }, status=status.HTTP_404_NOT_FOUND)
        
        data = []
        for country in countries:
            data.append({
                'id': str(country.id),
                'name': country.name,
                'code': country.code,
                'phone_code': country.phone_code,
            })
        
        return Response({
            'success': True,
            'count': len(data),
            'phone_code': phone_code,
            'data': data
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# URL patterns (add to your urls.py)
"""
from django.urls import path
from . import country_api_views

urlpatterns = [
    path('api/countries/', country_api_views.countries_list, name='countries-list'),
    path('api/countries/<str:country_code>/', country_api_views.country_detail, name='country-detail'),
    path('api/countries/phone/<str:phone_code>/', country_api_views.countries_by_phone_code, name='countries-by-phone'),
]
"""
