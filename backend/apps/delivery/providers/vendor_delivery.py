"""
Vendor-managed delivery provider.
The vendor handles delivery themselves using their own riders.
"""

import logging
import uuid

logger = logging.getLogger(__name__)


class VendorDeliveryProvider:
    """
    Vendor manages delivery with their own riders.
    No external API calls — tracking is updated manually by the vendor.
    """

    def assign(self, *, shipment) -> dict:
        tracking_number = f"VM-{str(uuid.uuid4())[:8].upper()}"
        logger.info("vendor_delivery_assigned shipment=%s tracking=%s", shipment.pk, tracking_number)
        return {
            "tracking_number": tracking_number,
            "provider": "vendor_managed",
            "instructions": "Vendor will contact customer for delivery arrangements.",
        }

    def get_tracking_url(self, *, tracking_number: str) -> str:
        return f"/track/{tracking_number}"

    def estimate_delivery(self) -> dict:
        return {
            "estimated_hours": 24,
            "note": "Delivery time depends on vendor rider availability.",
        }
