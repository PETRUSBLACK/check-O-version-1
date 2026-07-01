from django.db import models


class BusinessStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING = "pending", "Pending Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    SUSPENDED = "suspended", "Suspended"


class BusinessCategory(models.TextChoices):
    RETAIL = "retail", "Retail Shop"
    GROCERY = "grocery", "Grocery / Supermarket"
    RESTAURANT = "restaurant", "Restaurant / Food"
    HOTEL = "hotel", "Hotel / Lodging"
    PHARMACY = "pharmacy", "Pharmacy"
    FASHION = "fashion", "Fashion / Clothing"
    ELECTRONICS = "electronics", "Electronics"
    BEAUTY = "beauty", "Beauty / Salon"
    HEALTH = "health", "Health / Fitness"
    EDUCATION = "education", "Education / Training"
    AUTOMOBILE = "automobile", "Automobile / Auto Parts"
    OTHER = "other", "Other"


class BusinessMemberRole(models.TextChoices):
    OWNER = "owner", "Owner"
    MANAGER = "manager", "Manager"
    CASHIER = "cashier", "Cashier"
    INVENTORY_MANAGER = "inventory_manager", "Inventory Manager"
    DELIVERY_MANAGER = "delivery_manager", "Delivery Manager"
    SUPPORT = "support", "Support"


class WeekDay(models.IntegerChoices):
    MONDAY = 1, "Monday"
    TUESDAY = 2, "Tuesday"
    WEDNESDAY = 3, "Wednesday"
    THURSDAY = 4, "Thursday"
    FRIDAY = 5, "Friday"
    SATURDAY = 6, "Saturday"
    SUNDAY = 7, "Sunday"