"""
Logistics partner delivery provider.
Third-party companies: GIG Logistics, Kwik Delivery, DHL.
"""

import logging
import uuid

logger = logging.getLogger(__name__)

_PARTNER_CONFIG = {
    "gig": {"name": "GIG Logistics", "estimated_hours": 48},
    "kwik": {"name": "Kwik Delivery", "estimated_hours": 4},
    "dhl": {"name": "DHL", "estimated_hours": 72},
}


class LogisticsPartnerProvider:
    """
    Logistics partner handles pickup from vendor and delivery to customer.
    In production, this would call each partner's API.
    Currently returns structured booking data for manual coordination.
    """

    def __init__(self, partner: str):
        self.partner = partner.lower()
        self.config = _PARTNER_CONFIG.get(self.partner, {
            "name": partner, "estimated_hours": 48
        })

    def book(self, *, shipment) -> dict:
        """
        Book a pickup with the logistics partner.
        Returns booking reference and instructions.
        """
        booking_ref = f"{self.partner.upper()}-{str(uuid.uuid4())[:8].upper()}"
        logger.info(
            "logistics_partner_booked partner=%s shipment=%s ref=%s",
            self.partner, shipment.pk, booking_ref,
        )
        return {
            "booking_ref": booking_ref,
            "partner": self.config["name"],
            "estimated_hours": self.config["estimated_hours"],
            "instructions": f"Package will be picked up by {self.config['name']} within 2 hours.",
        }

    def get_tracking_url(self, *, tracking_number: str) -> str:
        urls = {
            "gig": f"https://giglogistics.com/track/{tracking_number}",
            "kwik": f"https://kwikdelivery.com/track/{tracking_number}",
            "dhl": f"https://dhl.com/track/{tracking_number}",
        }
        return urls.get(self.partner, f"/track/{tracking_number}")

    def estimate_delivery(self) -> dict:
        return {
            "estimated_hours": self.config["estimated_hours"],
            "partner": self.config["name"],
        }
