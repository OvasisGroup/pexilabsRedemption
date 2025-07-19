import os, sys, django
sys.path.append('/Users/asd/Desktop/desktop/pexilabs')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.test import Client
from authentication.models import CustomUser, UserRole

print("Testing Merchant Verifier Dashboard...")

# Test access
client = Client()
staff_user, created = CustomUser.objects.get_or_create(
    email='test@staff.com',
    defaults={
        'first_name': 'Test', 
        'last_name': 'Staff', 
        'is_verified': True, 
        'is_staff': True, 
        'role': UserRole.STAFF
    }
)
if created:
    staff_user.set_password('pass123')
    staff_user.save()

client.force_login(staff_user)
response = client.get('/dashboard/merchant-verifier/')
print(f'Dashboard access status: {response.status_code}')

if response.status_code == 200:
    print('✅ Merchant Verifier Dashboard works!')
    
    # Test detail view
    from authentication.models import Merchant
    if Merchant.objects.exists():
        merchant = Merchant.objects.first()
        detail_response = client.get(f'/dashboard/merchant-verifier/{merchant.id}/')
        print(f'Detail view status: {detail_response.status_code}')
        if detail_response.status_code == 200:
            print('✅ Merchant detail view works!')
        else:
            print(f'❌ Detail view failed: {detail_response.status_code}')
    else:
        print('ℹ️  No merchants found for detail testing')
        
elif response.status_code == 302:
    print(f'⚠️  Redirected to: {response.get("Location", "Unknown")}')
else:
    print(f'❌ Failed with status: {response.status_code}')

print("Test completed!")
