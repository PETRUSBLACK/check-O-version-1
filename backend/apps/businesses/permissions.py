from rest_framework.permissions import BasePermission

from apps.businesses.models import BusinessMember


class IsBusinessOwner(BasePermission):
    """
    Allows access only to the business owner.
    """

    message = "You are not the owner of this business."

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class IsBusinessMember(BasePermission):
    """
    Allows access to members of the business.
    """

    message = "You are not a member of this business."

    def has_object_permission(self, request, view, obj):
        return BusinessMember.objects.filter(
            business=obj,
            user=request.user,
            is_active=True,
        ).exists()