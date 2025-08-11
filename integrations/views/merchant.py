from rest_framework import generics, filters, permissions
from django_filters.rest_framework import DjangoFilterBackend

from ..models import MerchantIntegration
from ..serializers import (
    MerchantIntegrationListSerializer,
    MerchantIntegrationDetailSerializer,
    MerchantIntegrationCreateSerializer,
    MerchantIntegrationUpdateSerializer
)
from .base import StandardResultsSetPagination


class MerchantIntegrationListView(generics.ListCreateAPIView):
    """List and create merchant integrations"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_enabled', 'status', 'integration__integration_type']
    search_fields = ['integration__name', 'integration__provider_name']
    ordering_fields = ['created_at', 'last_used_at', 'total_requests']
    ordering = ['-created_at']
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return MerchantIntegrationCreateSerializer
        return MerchantIntegrationListSerializer

    def get_queryset(self):
        """Get merchant's integrations"""
        return MerchantIntegration.objects.filter(
            merchant=self.request.user.merchant
        ).select_related('integration', 'merchant')


class MerchantIntegrationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete merchant integration"""
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id'

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return MerchantIntegrationUpdateSerializer
        return MerchantIntegrationDetailSerializer

    def get_queryset(self):
        """Get merchant's integrations"""
        return MerchantIntegration.objects.filter(
            merchant=self.request.user.merchant
        ).select_related('integration', 'merchant')