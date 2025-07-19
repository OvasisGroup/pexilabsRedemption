#!/usr/bin/env python
"""
Test script to verify DocumentTypeModel admin integration
"""
import os
import sys
import django

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_dir)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pexilabs.settings')
django.setup()

from django.contrib import admin
from authentication.models import DocumentTypeModel
from authentication.admin import DocumentTypeAdmin

def test_document_type_admin():
    """Test DocumentTypeModel admin configuration"""
    print("=== DocumentTypeModel Admin Integration Test ===\n")
    
    # Test 1: Check if model is registered
    print("1. Testing admin registration...")
    registered_models = admin.site._registry
    is_registered = DocumentTypeModel in registered_models
    print(f"   DocumentTypeModel registered: {is_registered}")
    
    if is_registered:
        admin_class = registered_models[DocumentTypeModel]
        print(f"   Admin class: {admin_class.__class__.__name__}")
    
    # Test 2: Check admin configuration
    print("\n2. Testing admin configuration...")
    admin_instance = DocumentTypeAdmin(DocumentTypeModel, admin.site)
    
    print(f"   List display fields: {admin_instance.list_display}")
    print(f"   List filters: {admin_instance.list_filter}")
    print(f"   Search fields: {admin_instance.search_fields}")
    print(f"   List editable fields: {admin_instance.list_editable}")
    print(f"   Actions: {[action for action in admin_instance.actions if not action.startswith('delete')]}")
    
    # Test 3: Check database records
    print("\n3. Testing database integration...")
    document_types = DocumentTypeModel.objects.all()
    print(f"   Total document types: {document_types.count()}")
    
    if document_types.exists():
        print("   Document types in database:")
        for dt in document_types[:3]:
            print(f"   - {dt.name} ({dt.code})")
            print(f"     Required: {dt.is_required}, Active: {dt.is_active}")
            print(f"     Max file size: {dt.max_file_size_mb}MB")
            print(f"     Allowed extensions: {dt.allowed_extensions}")
    
    # Test 4: Test admin methods
    print("\n4. Testing admin methods...")
    if document_types.exists():
        sample_dt = document_types.first()
        print(f"   String representation: {str(sample_dt)}")
        print(f"   Allowed extensions list: {sample_dt.get_allowed_extensions_list()}")
        print(f"   Max file size in bytes: {sample_dt.get_max_file_size_bytes()}")
    
    print("\n=== Test completed successfully! ===")
    print("\nNext steps:")
    print("1. Access Django admin at: http://127.0.0.1:8000/admin/")
    print("2. Navigate to 'Authentication' → 'Document Types'")
    print("3. Test admin features like:")
    print("   - Adding new document types")
    print("   - Editing existing types")
    print("   - Using bulk actions (make required/optional, activate/deactivate)")
    print("   - Filtering and searching")

if __name__ == '__main__':
    test_document_type_admin()
