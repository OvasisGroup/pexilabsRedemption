#!/usr/bin/env python3
"""
Test script to demonstrate the Country model data usage.
Run this script to see how to work with the populated countries.
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from authentication.models import Country


def main():
    """Demonstrate Country model usage"""
    print("🌍 Country Database Demo")
    print("=" * 50)
    
    # Total countries
    total = Country.objects.count()
    print(f"📊 Total Countries: {total}")
    print()
    
    # Countries by continent (sample)
    regions = {
        'Europe': ['DE', 'FR', 'GB', 'IT', 'ES', 'NL', 'SE', 'NO'],
        'Asia': ['CN', 'IN', 'JP', 'KR', 'SG', 'TH', 'MY', 'ID'],
        'Africa': ['NG', 'ZA', 'KE', 'EG', 'MA', 'GH', 'ET', 'TZ'],
        'Americas': ['US', 'CA', 'BR', 'MX', 'AR', 'CL', 'CO', 'PE'],
        'Oceania': ['AU', 'NZ', 'FJ', 'PG', 'SB', 'VU', 'TO', 'WS']
    }
    
    for region, codes in regions.items():
        print(f"🌎 {region}:")
        countries = Country.objects.filter(code__in=codes).order_by('name')[:5]
        for country in countries:
            print(f"  • {country.name} ({country.code}) - {country.phone_code}")
        print()
    
    # Search examples
    print("🔍 Search Examples:")
    print("-" * 30)
    
    # Search by partial name
    search_term = "United"
    united_countries = Country.objects.filter(name__icontains=search_term)
    print(f"Countries containing '{search_term}':")
    for country in united_countries:
        print(f"  • {country.name} ({country.code})")
    print()
    
    # Countries with +1 phone code (NANP)
    nanp_countries = Country.objects.filter(phone_code='+1').order_by('name')
    print("Countries with +1 phone code:")
    for country in nanp_countries[:10]:  # Show first 10
        print(f"  • {country.name} ({country.code})")
    print()
    
    # Usage examples for forms/dropdowns
    print("💻 Usage Examples for Forms:")
    print("-" * 35)
    
    # Get all countries for dropdown
    all_countries = Country.objects.all().order_by('name')
    print(f"For Django forms - all {all_countries.count()} countries available")
    
    # Popular countries (commonly used first)
    popular_codes = ['US', 'CA', 'GB', 'AU', 'DE', 'FR', 'JP', 'CN', 'IN', 'BR']
    popular_countries = []
    other_countries = []
    
    for country in all_countries:
        if country.code in popular_codes:
            popular_countries.append(country)
        else:
            other_countries.append(country)
    
    # Sort popular countries by the order in popular_codes
    popular_countries.sort(key=lambda x: popular_codes.index(x.code))
    
    print("\nPopular countries (for top of dropdown):")
    for country in popular_countries[:5]:
        print(f"  • {country.name} ({country.code}) - {country.phone_code}")
    
    print(f"\n... and {len(other_countries)} more countries available")
    
    # API example data
    print("\n📡 API Usage Example:")
    print("-" * 25)
    sample_countries = Country.objects.all()[:3]
    api_data = []
    for country in sample_countries:
        api_data.append({
            'id': str(country.id),
            'name': country.name,
            'code': country.code,
            'phone_code': country.phone_code,
        })
    
    import json
    print("Sample API response:")
    print(json.dumps(api_data, indent=2))


if __name__ == '__main__':
    main()
