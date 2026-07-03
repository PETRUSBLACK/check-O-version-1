from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.businesses.models import BusinessMember
from apps.businesses.serializers import BusinessMemberSerializer


class BusinessMemberViewSet(viewsets.ModelViewSet):

    permission_classes = [
        IsAuthenticated,
    ]

    queryset = (
        BusinessMember.objects
        .select_related(
            "business",
            "branch",
            "user",
        )
    )

    serializer_class = BusinessMemberSerializer