#!/usr/bin/env python
"""
Simple document upload test
"""

import os
import sys
import django

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from authentication.models import CustomUser, Merchant, MerchantDocument, DocumentType, DocumentStatus

def simple_test():
    print("Simple Document Test")
    print("=" * 40)
    
    # Check if we have any merchants
    merchants = Merchant.objects.all()
    print(f"Total merchants: {merchants.count()}")
    
    if merchants.exists():
        merchant = merchants.first()
        print(f"Test merchant: {merchant.business_name}")
        
        # Check documents for this merchant
        docs = MerchantDocument.objects.filter(merchant=merchant)
        print(f"Documents for merchant: {docs.count()}")
        
        for doc in docs:
            print(f"  - {doc.title} ({doc.document_type}) - {doc.status}")
    
    # Check all documents
    all_docs = MerchantDocument.objects.all()
    print(f"Total documents in system: {all_docs.count()}")

if __name__ == '__main__':
    simple_test()
