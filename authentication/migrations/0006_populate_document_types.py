"""
Data migration to populate DocumentTypeModel with default document types
"""

from django.db import migrations


def create_default_document_types(apps, schema_editor):
    """Create default document types"""
    DocumentTypeModel = apps.get_model('authentication', 'DocumentTypeModel')
    
    # Default document types based on the existing choices
    default_types = [
        {
            'name': 'Business License',
            'code': 'business_license',
            'description': 'Official business license or permit required to operate the business legally',
            'is_required': True,
            'display_order': 1,
            'icon': 'fas fa-certificate',
        },
        {
            'name': 'Business Registration',
            'code': 'business_registration',
            'description': 'Official business registration documents from government authorities',
            'is_required': True,
            'display_order': 2,
            'icon': 'fas fa-building',
        },
        {
            'name': 'Tax Certificate',
            'code': 'tax_certificate',
            'description': 'Tax registration certificate or tax identification documents',
            'is_required': True,
            'display_order': 3,
            'icon': 'fas fa-receipt',
        },
        {
            'name': 'Identity Document',
            'code': 'identity_document',
            'description': 'Government-issued identification document of the business owner',
            'is_required': True,
            'display_order': 4,
            'icon': 'fas fa-id-card',
        },
        {
            'name': 'Bank Statement',
            'code': 'bank_statement',
            'description': 'Recent bank statements for financial verification',
            'is_required': False,
            'display_order': 5,
            'icon': 'fas fa-university',
        },
        {
            'name': 'Utility Bill',
            'code': 'utility_bill',
            'description': 'Recent utility bill for address verification',
            'is_required': False,
            'display_order': 6,
            'icon': 'fas fa-file-invoice',
        },
        {
            'name': 'Insurance Certificate',
            'code': 'insurance_certificate',
            'description': 'Business insurance certificate or policy documents',
            'is_required': False,
            'display_order': 7,
            'icon': 'fas fa-shield-alt',
        },
        {
            'name': 'Financial Statement',
            'code': 'financial_statement',
            'description': 'Business financial statements or accounting records',
            'is_required': False,
            'display_order': 8,
            'icon': 'fas fa-chart-bar',
        },
        {
            'name': 'Other',
            'code': 'other',
            'description': 'Other supporting documents not covered by specific categories',
            'is_required': False,
            'display_order': 9,
            'icon': 'fas fa-file',
        },
    ]
    
    for doc_type_data in default_types:
        DocumentTypeModel.objects.get_or_create(
            code=doc_type_data['code'],
            defaults=doc_type_data
        )


def reverse_create_default_document_types(apps, schema_editor):
    """Remove default document types"""
    DocumentTypeModel = apps.get_model('authentication', 'DocumentTypeModel')
    DocumentTypeModel.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('authentication', '0005_add_document_type_model'),
    ]

    operations = [
        migrations.RunPython(
            create_default_document_types,
            reverse_create_default_document_types,
        ),
    ]
