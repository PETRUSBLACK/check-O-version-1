from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema

from apps.businesses.models import Business
from apps.dining.models import Menu, MenuSection, MenuItem, DietaryFlag
from apps.dining.serializers import (
    MenuSerializer,
    MenuSectionSerializer,
    MenuItemSerializer,
    DietaryFlagSerializer,
)
from apps.dining.services.menu import DiningError, add_menu_item, add_section, create_menu, toggle_item_availability, update_menu
from core.permissions import IsVendor


class MenuView(APIView):
    """
    GET  — public: retrieve a restaurant's full menu.
    POST — vendor: create the menu for their restaurant.
    PUT  — vendor: update menu name/description/active status.
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated(), IsVendor()]

    @extend_schema(
        tags=["dining"],
        summary="Get restaurant menu",
        description="Returns the full menu with sections and items for a restaurant business.",
        responses={200: MenuSerializer},
    )
    def get(self, request, business_id):
        menu = Menu.objects.filter(
            business_id=business_id, is_active=True
        ).prefetch_related("sections__items").first()
        if not menu:
            return Response({"detail": "No active menu found."}, status=404)
        return Response(MenuSerializer(menu).data)

    @extend_schema(
        tags=["dining"],
        summary="Create restaurant menu (vendor only)",
        request=MenuSerializer,
        responses={201: MenuSerializer},
    )
    def post(self, request, business_id):
        business = Business.objects.filter(pk=business_id, owner=request.user).first()
        if not business:
            return Response({"detail": "Business not found."}, status=404)
        try:
            menu = create_menu(
                business=business,
                name=request.data.get("name", "Menu"),
                description=request.data.get("description", ""),
            )
        except DiningError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(MenuSerializer(menu).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["dining"],
        summary="Update restaurant menu (vendor only)",
        request=MenuSerializer,
        responses={200: MenuSerializer},
    )
    def put(self, request, business_id):
        menu = Menu.objects.filter(business_id=business_id, business__owner=request.user).first()
        if not menu:
            return Response({"detail": "Menu not found."}, status=404)
        menu = update_menu(
            menu=menu,
            name=request.data.get("name"),
            description=request.data.get("description"),
            is_active=request.data.get("is_active"),
        )
        return Response(MenuSerializer(menu).data)


class MenuSectionView(APIView):
    """Vendor: add a section to their restaurant menu."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=["dining"],
        summary="Add a section to the menu (vendor only)",
        description="e.g. Starters, Mains, Drinks, Desserts.",
        request=MenuSectionSerializer,
        responses={201: MenuSectionSerializer},
    )
    def post(self, request, business_id):
        menu = Menu.objects.filter(
            business_id=business_id, business__owner=request.user
        ).first()
        if not menu:
            return Response({"detail": "Menu not found."}, status=404)
        section = add_section(
            menu=menu,
            name=request.data.get("name", ""),
            position=request.data.get("position", 0),
        )
        return Response(MenuSectionSerializer(section).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["dining"],
        summary="Delete a menu section (vendor only)",
        responses={204: None},
    )
    def delete(self, request, business_id, section_id):
        section = MenuSection.objects.filter(
            pk=section_id, menu__business_id=business_id, menu__business__owner=request.user
        ).first()
        if not section:
            return Response({"detail": "Section not found."}, status=404)
        section.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class MenuItemView(APIView):
    """Vendor: add items to a menu section."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=["dining"],
        summary="Add item to a menu section (vendor only)",
        request=MenuItemSerializer,
        responses={201: MenuItemSerializer},
    )
    def post(self, request, business_id, section_id):
        section = MenuSection.objects.filter(
            pk=section_id,
            menu__business_id=business_id,
            menu__business__owner=request.user,
        ).first()
        if not section:
            return Response({"detail": "Section not found."}, status=404)

        ser = MenuItemSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        vd = ser.validated_data

        item = add_menu_item(
            section=section,
            name=vd["name"],
            price=vd["price"],
            description=vd.get("description", ""),
            is_available=vd.get("is_available", True),
            dietary_flags=vd.get("dietary_flags", []),
            preparation_minutes=vd.get("preparation_minutes", 15),
        )
        return Response(MenuItemSerializer(item).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["dining"],
        summary="Update a menu item (vendor only)",
        request=MenuItemSerializer,
        responses={200: MenuItemSerializer},
    )
    def put(self, request, business_id, section_id, item_id):
        item = MenuItem.objects.filter(
            pk=item_id,
            section_id=section_id,
            section__menu__business_id=business_id,
            section__menu__business__owner=request.user,
        ).first()
        if not item:
            return Response({"detail": "Item not found."}, status=404)
        ser = MenuItemSerializer(item, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)

    @extend_schema(
        tags=["dining"],
        summary="Delete a menu item (vendor only)",
        responses={204: None},
    )
    def delete(self, request, business_id, section_id, item_id):
        item = MenuItem.objects.filter(
            pk=item_id,
            section_id=section_id,
            section__menu__business_id=business_id,
            section__menu__business__owner=request.user,
        ).first()
        if not item:
            return Response({"detail": "Item not found."}, status=404)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ToggleMenuItemView(APIView):
    """Vendor: toggle item availability (e.g. sold out today)."""
    permission_classes = [IsAuthenticated, IsVendor]

    @extend_schema(
        tags=["dining"],
        summary="Toggle menu item availability (vendor only)",
        responses={200: MenuItemSerializer},
    )
    def post(self, request, business_id, item_id):
        item = MenuItem.objects.filter(
            pk=item_id,
            section__menu__business_id=business_id,
            section__menu__business__owner=request.user,
        ).first()
        if not item:
            return Response({"detail": "Item not found."}, status=404)
        item = toggle_item_availability(item=item)
        return Response(MenuItemSerializer(item).data)


class DietaryFlagsView(APIView):
    """Public: list all valid dietary flags."""
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["dining"],
        summary="List all dietary flags",
        responses={200: DietaryFlagSerializer(many=True)},
    )
    def get(self, request):
        data = [{"value": v, "label": l} for v, l in DietaryFlag.choices]
        return Response(data)
