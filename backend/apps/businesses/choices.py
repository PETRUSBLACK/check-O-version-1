from django.db import models


class BusinessStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING = "pending", "Pending Review"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    SUSPENDED = "suspended", "Suspended"


class BusinessCategory(models.TextChoices):
    RETAIL = "retail", "Retail Store"
    SUPERMARKET = "supermarket", "Supermarket"
    PHARMACY = "pharmacy", "Pharmacy"
    RESTAURANT = "restaurant", "Restaurant"

    HOTEL = "hotel", "Hotel"
    FASHION = "fashion", "Fashion"
    ELECTRONICS = "electronics", "Electronics"
    BEAUTY = "beauty", "Beauty & Salon"
    HEALTH = "health", "Health & Fitness"
    EDUCATION = "education", "Education"
    AUTOMOBILE = "automobile", "Automobile"
    OTHER = "other", "Other"


class VerificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class BusinessMemberRole(models.TextChoices):
    OWNER = "owner", "Owner"
    MANAGER = "manager", "Manager"
    CASHIER = "cashier", "Cashier"
    INVENTORY_MANAGER = "inventory_manager", "Inventory Manager"
    DELIVERY_MANAGER = "delivery_manager", "Delivery Manager"
    DELIVERY_RIDER = "delivery_rider", "Delivery Rider"
    ACCOUNTANT = "accountant", "Accountant"
    SUPPORT = "support", "Support"


class BusinessDocumentType(models.TextChoices):
    CAC_CERTIFICATE = "cac_certificate", "CAC Certificate"
    TAX_CERTIFICATE = "tax_certificate", "Tax Certificate"
    BUSINESS_LICENSE = "business_license", "Business License"
    FOOD_LICENSE = "food_license", "Food License"
    PHARMACY_LICENSE = "pharmacy_license", "Pharmacy License"
    INSURANCE = "insurance", "Insurance"
    OTHER = "other", "Other"


class WeekDay(models.IntegerChoices):
    MONDAY = 1, "Monday"
    TUESDAY = 2, "Tuesday"
    WEDNESDAY = 3, "Wednesday"
    THURSDAY = 4, "Thursday"
    FRIDAY = 5, "Friday"
    SATURDAY = 6, "Saturday"
    SUNDAY = 7, "Sunday"