import logging
import json
from datetime import datetime, timedelta
from django.db.models import Q, Count, Avg, Sum, F, ExpressionWrapper, FloatField
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse

from ..models import Integration, IntegrationType, IntegrationStatus, MerchantIntegration
from ..serializers import (
    IntegrationChoiceSerializer,
    IntegrationStatsSerializer,
    IntegrationHealthSerializer
)
from authentication.api_auth import APIKeyOrTokenAuthentication
from .base import APIKeyPermission

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Get available integration types and providers",
    description="Get available integration types and providers",
    responses={200: IntegrationChoiceSerializer(many=True)}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def integration_choices(request):
    """Get available integration types and providers"""
    # Get integration types
    type_choices = [
        {'value': choice[0], 'display': choice[1]}
        for choice in IntegrationType.choices
    ]
    
    # Get integration status choices
    status_choices = [
        {'value': choice[0], 'display': choice[1]}
        for choice in IntegrationStatus.choices
    ]
    
    # Get available providers
    providers = Integration.objects.filter(
        status=IntegrationStatus.ACTIVE,
        is_global=True
    ).values('provider_name').distinct().order_by('provider_name')
    
    provider_choices = [
        {'value': provider['provider_name'], 'display': provider['provider_name']}
        for provider in providers
    ]
    
    result = {
        'types': type_choices,
        'statuses': status_choices,
        'providers': provider_choices
    }
    
    return Response(result)


@extend_schema(
    summary="Get integration statistics",
    description="Get integration usage statistics",
    responses={200: IntegrationStatsSerializer}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def integration_stats(request):
    """Get integration statistics for merchant"""
    merchant = request.user.merchant
    today = timezone.now().date()
    
    # Basic counts
    total_integrations = Integration.objects.filter(
        Q(is_global=True) | Q(merchant_configurations__merchant=merchant)
    ).distinct().count()
    
    active_integrations = Integration.objects.filter(
        Q(is_global=True) | Q(merchant_configurations__merchant=merchant),
        status=IntegrationStatus.ACTIVE
    ).distinct().count()
    
    enabled_merchant_integrations = MerchantIntegration.objects.filter(
        merchant=merchant,
        is_enabled=True
    ).count()
    
    # API call statistics for today
    api_calls_today = IntegrationAPICall.objects.filter(
        merchant_integration__merchant=merchant,
        created_at__date=today
    )
    
    total_api_calls_today = api_calls_today.count()
    successful_api_calls_today = api_calls_today.filter(is_successful=True).count()
    failed_api_calls_today = api_calls_today.filter(is_successful=False).count()
    
    success_rate_today = 0
    if total_api_calls_today > 0:
        success_rate_today = (successful_api_calls_today / total_api_calls_today) * 100
    
    # Average response time
    avg_response_time = api_calls_today.filter(
        response_time_ms__isnull=False
    ).aggregate(avg=Avg('response_time_ms'))['avg'] or 0
    
    # Most used integration and operation
    most_used_integration = api_calls_today.values(
        'merchant_integration__integration__name'
    ).annotate(count=Count('id')).order_by('-count').first()
    
    most_used_operation = api_calls_today.values(
        'operation_type'
    ).annotate(count=Count('id')).order_by('-count').first()
    
    stats = {
        'total_integrations': total_integrations,
        'active_integrations': active_integrations,
        'enabled_merchant_integrations': enabled_merchant_integrations,
        'total_api_calls_today': total_api_calls_today,
        'successful_api_calls_today': successful_api_calls_today,
        'failed_api_calls_today': failed_api_calls_today,
        'success_rate_today': round(success_rate_today, 2),
        'avg_response_time_ms': round(avg_response_time, 2),
        'most_used_integration': most_used_integration['merchant_integration__integration__name'] if most_used_integration else 'None',
        'most_used_operation': most_used_operation['operation_type'] if most_used_operation else 'None'
    }
    
    serializer = IntegrationStatsSerializer(stats)
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    summary="Check integration health",
    description="Check health status of integrations",
    responses={200: IntegrationHealthSerializer(many=True)}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def integration_health(request):
    """Get health status for merchant's integrations"""
    merchant = request.user.merchant
    
    merchant_integrations = MerchantIntegration.objects.filter(
        merchant=merchant
    ).select_related('integration')
    
    health_data = []
    for mi in merchant_integrations:
        health_data.append({
            'integration_id': mi.integration.id,
            'integration_name': mi.integration.name,
            'provider_name': mi.integration.provider_name,
            'is_healthy': mi.is_healthy(),
            'last_health_check': mi.integration.last_health_check,
            'health_error_message': mi.integration.health_error_message,
            'status': mi.status,
            'consecutive_failures': mi.consecutive_failures,
            'success_rate': mi.get_success_rate()
        })
    
    serializer = IntegrationHealthSerializer(health_data, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    summary="List all available integration providers",
    description="List all available integration providers",
    responses={200: OpenApiResponse(description="Integration providers list")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def integration_providers_list(request):
    """List all available integration providers"""
    try:
        # Get integrations with their provider configurations
        integrations = Integration.objects.filter(
            status=IntegrationStatus.ACTIVE,
            is_global=True
        ).select_related('provider_config').order_by('provider_name', 'name')
        
        providers_data = []
        for integration in integrations:
            provider_data = {
                'id': str(integration.id),
                'name': integration.name,
                'code': integration.code,
                'provider_name': integration.provider_name,
                'integration_type': integration.integration_type,
                'description': integration.description,
                'supports_webhooks': integration.supports_webhooks,
                'supports_bulk_operations': integration.supports_bulk_operations,
                'supports_real_time': integration.supports_real_time,
                'is_sandbox': integration.is_sandbox,
                'version': integration.version,
                'authentication_type': integration.authentication_type,
            }
            
            # Add provider-specific configuration if available
            if hasattr(integration, 'provider_config'):
                provider_config = integration.provider_config
                provider_data.update({
                    'supported_operations': provider_config.supported_operations,
                    'endpoints': provider_config.endpoints,
                    'fee_structure': provider_config.fee_structure,
                    'limits': provider_config.limits,
                    'webhook_config': provider_config.webhook_config,
                })
            
            providers_data.append(provider_data)
        
        return Response({
            'success': True,
            'count': len(providers_data),
            'data': providers_data
        })
        
    except Exception as e:
        logger.error(f"Integration providers list error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get integration provider details",
    description="Get detailed information about a specific integration provider",
    responses={200: OpenApiResponse(description="Integration provider details")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def integration_provider_detail(request, integration_id):
    """Get detailed information about a specific integration provider"""
    try:
        integration = Integration.objects.select_related('provider_config').get(
            id=integration_id,
            status=IntegrationStatus.ACTIVE,
            is_global=True
        )
        
        provider_data = {
            'id': str(integration.id),
            'name': integration.name,
            'code': integration.code,
            'provider_name': integration.provider_name,
            'integration_type': integration.integration_type,
            'description': integration.description,
            'provider_website': integration.provider_website,
            'provider_documentation': integration.provider_documentation,
            'base_url': integration.base_url,
            'is_sandbox': integration.is_sandbox,
            'version': integration.version,
            'authentication_type': integration.authentication_type,
            'supports_webhooks': integration.supports_webhooks,
            'supports_bulk_operations': integration.supports_bulk_operations,
            'supports_real_time': integration.supports_real_time,
            'rate_limits': {
                'per_minute': integration.rate_limit_per_minute,
                'per_hour': integration.rate_limit_per_hour,
                'per_day': integration.rate_limit_per_day,
            },
            'health_status': {
                'is_healthy': integration.is_healthy,
                'last_health_check': integration.last_health_check,
                'health_error_message': integration.health_error_message,
            },
            'created_at': integration.created_at,
            'updated_at': integration.updated_at,
        }
        
        # Add provider-specific configuration if available
        if hasattr(integration, 'provider_config'):
            provider_config = integration.provider_config
            provider_data.update({
                'provider_configuration': {
                    'supported_operations': provider_config.supported_operations,
                    'endpoints': provider_config.endpoints,
                    'fee_structure': provider_config.fee_structure,
                    'limits': provider_config.limits,
                    'webhook_config': provider_config.webhook_config,
                    'sandbox_config': provider_config.sandbox_config,
                    'production_config': provider_config.production_config,
                }
            })
        
        # Add bank-specific details if it's a bank integration
        if hasattr(integration, 'bank_details'):
            bank_details = integration.bank_details
            provider_data['bank_details'] = {
                'bank_name': bank_details.bank_name,
                'bank_code': bank_details.bank_code,
                'country_code': bank_details.country_code,
                'swift_code': bank_details.swift_code,
                'supported_services': {
                    'account_inquiry': bank_details.supports_account_inquiry,
                    'funds_transfer': bank_details.supports_funds_transfer,
                    'balance_check': bank_details.supports_balance_check,
                    'statement_retrieval': bank_details.supports_statement_retrieval,
                    'card_payments': bank_details.supports_card_payments,
                }
            }
        
        return Response({
            'success': True,
            'data': provider_data
        })
        
    except Integration.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Integration provider not found'
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        logger.error(f"Integration provider detail error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def configure_merchant_integration(request, integration_id):
    """Configure a specific integration for a merchant"""
    try:
        # Get the integration
        integration = Integration.objects.get(
            id=integration_id,
            status=IntegrationStatus.ACTIVE,
            is_global=True
        )
        
        # Get merchant
        merchant = None
        if hasattr(request.user, '_api_key'):
            # For API key users, you might need to implement merchant resolution
            # This depends on your business logic
            merchant = None  # Implement based on your needs
        elif hasattr(request.user, 'merchant_account'):
            merchant = request.user.merchant_account
        
        if not merchant:
            return Response({
                'success': False,
                'message': 'Merchant not found or not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get configuration data from request
        configuration = request.data.get('configuration', {})
        credentials = request.data.get('credentials', {})
        
        # Create or update merchant integration
        merchant_integration, created = MerchantIntegration.objects.get_or_create(
            merchant=merchant,
            integration=integration,
            defaults={
                'configuration': configuration,
                'status': IntegrationStatus.DRAFT,
                'is_enabled': False,
            }
        )
        
        if not created:
            # Update existing configuration
            merchant_integration.configuration.update(configuration)
            merchant_integration.save()
        
        # Encrypt and store credentials if provided
        if credentials:
            merchant_integration.encrypt_credentials(credentials)
        
        return Response({
            'success': True,
            'message': 'Integration configured successfully',
            'data': {
                'id': str(merchant_integration.id),
                'integration_name': integration.name,
                'provider_name': integration.provider_name,
                'status': merchant_integration.status,
                'is_enabled': merchant_integration.is_enabled,
                'created': created,
            }
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
    except Integration.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Integration not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Configure merchant integration error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get detailed integration statistics",
    description="Get integration usage statistics",
    responses={200: OpenApiResponse(description="Integration statistics retrieved")}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def integration_statistics(request):
    """Get integration usage statistics"""
    try:
        # Get merchant
        merchant = request.user.merchant
        
        if not merchant:
            return Response({
                'success': False,
                'message': 'Merchant not found or not authorized'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Get time range from query parameters
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Get merchant integrations
        merchant_integrations = MerchantIntegration.objects.filter(
            merchant=merchant
        ).select_related('integration')
        
        # Calculate statistics
        total_integrations = merchant_integrations.count()
        active_integrations = merchant_integrations.filter(is_enabled=True).count()
        
        # Get API call statistics
        api_calls = IntegrationAPICall.objects.filter(
            merchant_integration__merchant=merchant,
            created_at__gte=start_date
        )
        
        total_api_calls = api_calls.count()
        successful_calls = api_calls.filter(is_successful=True).count()
        failed_calls = api_calls.filter(is_successful=False).count()
        
        # Calculate success rate
        success_rate = (successful_calls / total_api_calls * 100) if total_api_calls > 0 else 0
        
        # Get integration-wise statistics
        integration_stats = []
        for mi in merchant_integrations:
            integration_calls = api_calls.filter(merchant_integration=mi)
            integration_stats.append({
                'integration_name': mi.integration.name,
                'provider_name': mi.integration.provider_name,
                'integration_type': mi.integration.integration_type,
                'is_enabled': mi.is_enabled,
                'total_requests': mi.total_requests,
                'successful_requests': mi.successful_requests,
                'failed_requests': mi.failed_requests,
                'success_rate': mi.get_success_rate(),
                'last_used_at': mi.last_used_at,
                'recent_calls': integration_calls.count(),
            })
        
        # Get daily usage data for chart
        daily_data = []
        for i in range(days):
            date = timezone.now().date() - timedelta(days=i)
            day_calls = api_calls.filter(created_at__date=date)
            daily_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'total': day_calls.count(),
                'successful': day_calls.filter(is_successful=True).count(),
                'failed': day_calls.filter(is_successful=False).count(),
            })
        
        return Response({
            'success': True,
            'data': {
                'summary': {
                    'total_integrations': total_integrations,
                    'active_integrations': active_integrations,
                    'total_api_calls': total_api_calls,
                    'successful_calls': successful_calls,
                    'failed_calls': failed_calls,
                    'success_rate': round(success_rate, 2),
                    'time_period': f'Last {days} days',
                },
                'integrations': integration_stats,
                'daily_usage': daily_data,
            }
        })
        
    except Exception as e:
        logger.error(f"Integration statistics error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An unexpected error occurred'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    summary="Get integration type choices",
    description="Get available integration type choices",
    responses={200: IntegrationChoiceSerializer(many=True)}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def integration_type_choices(request):
    """Get integration type choices"""
    choices = [
        {'value': choice[0], 'display': choice[1]}
        for choice in IntegrationType.choices
    ]
    return Response(choices)


@extend_schema(
    summary="Get integration status choices",
    description="Get available integration status choices",
    responses={200: IntegrationChoiceSerializer(many=True)}
)
@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([APIKeyPermission])
def integration_status_choices(request):
    """Get integration status choices"""
    choices = [
        {'value': choice[0], 'display': choice[1]}
        for choice in IntegrationStatus.choices
    ]
    return Response(choices)


@api_view(['GET'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def integration_settings_view(request):
    """Integration settings page for merchants"""
    # Check if user has merchant account
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        messages.error(request, "Access denied. Merchant account required.")
        return redirect('dashboard:dashboard_redirect')
    
    merchant = request.user.merchant_account
    
    # Get available integrations
    available_integrations = Integration.objects.filter(
        Q(is_global=True) | Q(status=IntegrationStatus.ACTIVE)
    ).order_by('integration_type', 'provider_name')
    
    # Get merchant's current integrations
    merchant_integrations = MerchantIntegration.objects.filter(
        merchant=merchant
    ).select_related('integration').order_by('-updated_at')
    
    # Get integration statistics
    integration_stats = {
        'total_available': available_integrations.count(),
        'total_configured': merchant_integrations.count(),
        'active_integrations': merchant_integrations.filter(is_enabled=True).count(),
        'by_type': available_integrations.values('integration_type').annotate(
            count=Count('id')
        ).order_by('integration_type')
    }
    
    # Add validation status for integrations
    from django.conf import settings
    import os
    
    validation_status = {
        'uba_bank': {
            'configured': bool(os.getenv('UBA_BASE_URL') and os.getenv('UBA_ACCESS_TOKEN')),
            'feature_enabled': getattr(settings, 'ENABLE_UBA_INTEGRATION', False),
            'api_key_set': bool(os.getenv('UBA_ACCESS_TOKEN')),
            'base_url_set': bool(os.getenv('UBA_BASE_URL')),
            'sandbox_mode': getattr(settings, 'UBA_SANDBOX', True),
        },
        'cybersource': {
            'configured': bool(os.getenv('CYBERSOURCE_MERCHANT_ID') and os.getenv('CYBERSOURCE_API_KEY')),
            'feature_enabled': getattr(settings, 'ENABLE_CYBERSOURCE_INTEGRATION', False),
            'merchant_id_set': bool(os.getenv('CYBERSOURCE_MERCHANT_ID')),
            'api_key_set': bool(os.getenv('CYBERSOURCE_API_KEY')),
            'sandbox_mode': getattr(settings, 'CYBERSOURCE_SANDBOX', True),
        },
        'corefy': {
            'configured': bool(os.getenv('COREFY_API_KEY') and os.getenv('COREFY_SECRET_KEY')),
            'feature_enabled': getattr(settings, 'ENABLE_COREFY_INTEGRATION', False),
            'api_key_set': bool(os.getenv('COREFY_API_KEY')),
            'secret_key_set': bool(os.getenv('COREFY_SECRET_KEY')),
            'sandbox_mode': getattr(settings, 'COREFY_SANDBOX', True),
        },
        'global_settings': {
            'health_check_enabled': bool(os.getenv('INTEGRATION_HEALTH_CHECK_INTERVAL')),
            'request_logging': getattr(settings, 'INTEGRATION_LOG_REQUESTS', False),
            'response_logging': getattr(settings, 'INTEGRATION_LOG_RESPONSES', False),
        }
    }
    
    context = {
        'page_title': 'Integration Settings',
        'available_integrations': available_integrations,
        'merchant_integrations': merchant_integrations,
        'integration_stats': integration_stats,
        'integration_types': IntegrationType.choices,
        'integration_statuses': IntegrationStatus.choices,
        'merchant': merchant,
        'validation_status': validation_status,
    }
    
    return render(request, 'integrations/settings.html', context)


@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def configure_integration_api(request):
    """API endpoint to configure a new integration for merchant"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        data = json.loads(request.body)
        integration_id = data.get('integration_id')
        configuration = data.get('configuration', {})
        credentials = data.get('credentials', {})
        
        if not integration_id:
            return JsonResponse({'error': 'Integration ID is required'}, status=400)
        
        # Get the integration
        try:
            integration = Integration.objects.get(id=integration_id)
        except Integration.DoesNotExist:
            return JsonResponse({'error': 'Integration not found'}, status=404)
        
        merchant = request.user.merchant_account
        
        # Create or update merchant integration
        merchant_integration, created = MerchantIntegration.objects.get_or_create(
            merchant=merchant,
            integration=integration,
            defaults={
                'configuration': configuration,
                'is_enabled': False,
                'status': IntegrationStatus.DRAFT
            }
        )
        
        if not created:
            # Update existing integration
            merchant_integration.configuration.update(configuration)
            merchant_integration.save()
        
        # Encrypt and store credentials if provided
        if credentials:
            # Handle UBA-specific credentials
            if integration.code == 'uba_kenya_pay':
                uba_credentials = {
                    'access_token': credentials.get('access_token'),
                    'configuration_id': credentials.get('configuration_id'),
                    'customization_id': credentials.get('customization_id')
                }
                merchant_integration.encrypt_credentials(uba_credentials)
            else:
                # Handle generic credentials
                merchant_integration.encrypt_credentials(credentials)
            merchant_integration.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Integration {integration.name} configured successfully',
            'integration_id': str(merchant_integration.id),
            'created': created
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error configuring integration: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@api_view(['POST'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def toggle_integration_api(request, integration_id):
    """API endpoint to enable/disable an integration"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        merchant = request.user.merchant_account
        merchant_integration = MerchantIntegration.objects.get(
            id=integration_id,
            merchant=merchant
        )
        
        # Toggle enabled status
        merchant_integration.is_enabled = not merchant_integration.is_enabled
        merchant_integration.status = IntegrationStatus.ACTIVE if merchant_integration.is_enabled else IntegrationStatus.INACTIVE
        merchant_integration.save()
        
        return JsonResponse({
            'success': True,
            'enabled': merchant_integration.is_enabled,
            'status': merchant_integration.status,
            'message': f'Integration {"enabled" if merchant_integration.is_enabled else "disabled"} successfully'
        })
        
    except MerchantIntegration.DoesNotExist:
        return JsonResponse({'error': 'Integration not found'}, status=404)
    except Exception as e:
        logger.error(f"Error toggling integration: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@api_view(['DELETE'])
@authentication_classes([APIKeyOrTokenAuthentication])
@permission_classes([permissions.IsAuthenticated])
def remove_integration_api(request, integration_id):
    """API endpoint to remove an integration"""
    if not hasattr(request.user, 'merchant_account') or not request.user.merchant_account:
        return JsonResponse({'error': 'Merchant account required'}, status=403)
    
    try:
        merchant = request.user.merchant_account
        merchant_integration = MerchantIntegration.objects.get(
            id=integration_id,
            merchant=merchant
        )
        
        integration_name = merchant_integration.integration.name
        merchant_integration.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Integration {integration_name} removed successfully'
        })
        
    except MerchantIntegration.DoesNotExist:
        return JsonResponse({'error': 'Integration not found'}, status=404)
    except Exception as e:
        logger.error(f"Error removing integration: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)