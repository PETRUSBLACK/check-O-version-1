"""
Branch API views.
"""

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.businesses.selectors import get_branches

from apps.businesses.services import (
    create_branch,
    update_branch,
)

from apps.businesses.serializers import (
    BranchListSerializer,
    BranchDetailSerializer,
    BranchCreateSerializer,
    BranchUpdateSerializer,
)