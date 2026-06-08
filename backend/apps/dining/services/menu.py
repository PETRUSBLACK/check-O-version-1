from django.db import transaction

from apps.businesses.models import Business, BusinessCategory
from apps.dining.models import Menu, MenuSection, MenuItem


class DiningError(Exception):
    pass


def _assert_restaurant(business: Business):
    """Guard: business must be category=restaurant."""
    if business.category != BusinessCategory.RESTAURANT:
        raise DiningError("This business is not registered as a restaurant.")


@transaction.atomic
def create_menu(*, business: Business, name: str = "Menu", description: str = "") -> Menu:
    _assert_restaurant(business)
    if Menu.objects.filter(business=business).exists():
        raise DiningError("This restaurant already has a menu. Update the existing one.")
    return Menu.objects.create(
        business=business,
        name=name,
        description=description,
        is_active=True,
    )


@transaction.atomic
def update_menu(*, menu: Menu, name: str = None, description: str = None, is_active: bool = None) -> Menu:
    if name is not None:
        menu.name = name
    if description is not None:
        menu.description = description
    if is_active is not None:
        menu.is_active = is_active
    menu.save()
    return menu


@transaction.atomic
def add_section(*, menu: Menu, name: str, position: int = 0) -> MenuSection:
    return MenuSection.objects.create(menu=menu, name=name, position=position)


@transaction.atomic
def add_menu_item(
    *,
    section: MenuSection,
    name: str,
    price,
    description: str = "",
    is_available: bool = True,
    dietary_flags: list = None,
    preparation_minutes: int = 15,
) -> MenuItem:
    return MenuItem.objects.create(
        section=section,
        name=name,
        price=price,
        description=description,
        is_available=is_available,
        dietary_flags=dietary_flags or [],
        preparation_minutes=preparation_minutes,
    )


@transaction.atomic
def toggle_item_availability(*, item: MenuItem) -> MenuItem:
    item.is_available = not item.is_available
    item.save(update_fields=["is_available", "updated_at"])
    return item
