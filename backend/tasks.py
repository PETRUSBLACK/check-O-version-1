"""
SmartMall Background Tasks.

These tasks need to run on a schedule via Celery, Django-Q, or a cron job.

Setup with Django-Q (recommended):
    pip install django-q2
    Add 'django_q' to INSTALLED_APPS
    Run: python manage.py qcluster

Or schedule via cron:
    # Run every hour
    0 * * * * cd /app && python manage.py run_tasks

Run with:  python manage.py run_tasks --scheduled   (every 5 minutes, one cron job)
That runs the "frequent" tasks every time, the hourly tasks once an hour and
the daily tasks once a day. See core/management/commands/run_tasks.py.

Task schedule:
    expire_unpaid_orders       → every 5 minutes (30-minute payment window)
    remind_vendors_waiting     → every 5 minutes (paid orders untouched for 2 hours)
    expire_pickup_orders       → every 5 minutes
    renew_subscriptions        → daily at midnight
    deactivate_expired_promos  → every hour
    send_pickup_reminders      → every hour
"""

import logging

logger = logging.getLogger(__name__)


def expire_pickup_orders():
    """
    Find all pickup orders past their deadline and expire them.
    Releases stock and triggers refunds automatically.
    Run every 5 minutes.
    """
    from django.utils import timezone
    from apps.orders.models import Order, OrderStatus
    from apps.orders.services.order_service import expire_pickup_order

    expired = Order.objects.filter(
        fulfilment_type="pickup",
        status=OrderStatus.READY_FOR_PICKUP,
        pickup_deadline__lt=timezone.now(),
    )

    count = 0
    for order in expired:
        try:
            expire_pickup_order(order_id=order.pk)
            count += 1
            logger.info("task_expired_pickup_order order=%s", order.pk)
        except Exception as exc:
            logger.error("task_expire_pickup_failed order=%s error=%s", order.pk, exc)

    logger.info("task_expire_pickup_orders expired=%d", count)
    return count


def send_pickup_reminders():
    """
    Send reminder notifications to customers approaching pickup deadlines.
    Sends at: 24 hours, 6 hours, 1 hour before deadline.
    Run every hour.
    """
    from django.utils import timezone
    from apps.orders.models import Order, OrderStatus
    from apps.notifications.services.notification_service import notify_pickup_reminder

    now = timezone.now()
    reminders_sent = 0

    reminder_windows = [
        (23.5, 24.5, 24),
        (5.5, 6.5, 6),
        (0.5, 1.5, 1),
    ]

    for min_hours, max_hours, label_hours in reminder_windows:
        orders = Order.objects.filter(
            fulfilment_type="pickup",
            status=OrderStatus.READY_FOR_PICKUP,
            pickup_deadline__gt=now + timezone.timedelta(hours=min_hours),
            pickup_deadline__lte=now + timezone.timedelta(hours=max_hours),
        ).select_related("customer")

        for order in orders:
            try:
                notify_pickup_reminder(order=order, hours_remaining=label_hours)
                reminders_sent += 1
                logger.info("task_pickup_reminder order=%s hours=%d", order.pk, label_hours)
            except Exception as exc:
                logger.error("task_pickup_reminder_failed order=%s error=%s", order.pk, exc)

    logger.info("task_pickup_reminders sent=%d", reminders_sent)
    return reminders_sent


def renew_subscriptions():
    """
    Auto-renew subscriptions that are expiring today.
    Run daily at midnight.
    """
    from django.utils import timezone
    from apps.subscriptions.models import VendorSubscription, SubscriptionStatus
    from apps.subscriptions.services.subscription_service import renew_subscription

    tomorrow = timezone.now() + timezone.timedelta(days=1)

    expiring = VendorSubscription.objects.filter(
        status=SubscriptionStatus.ACTIVE,
        auto_renew=True,
        expires_at__lt=tomorrow,
        plan__price_monthly=0,  # Auto-renew free plans only (paid plans need payment)
    )

    count = 0
    for sub in expiring:
        try:
            renew_subscription(subscription_id=sub.pk)
            count += 1
            logger.info("task_subscription_renewed sub=%s business=%s", sub.pk, sub.business_id)
        except Exception as exc:
            logger.error("task_subscription_renewal_failed sub=%s error=%s", sub.pk, exc)

    logger.info("task_renew_subscriptions renewed=%d", count)
    return count


def deactivate_expired_promotions():
    """
    Deactivate promotions whose end date has passed.
    Run every hour.
    """
    from django.utils import timezone
    from apps.ads.models import ProductPromotion

    expired = ProductPromotion.objects.filter(
        is_active=True,
        ends_at__lt=timezone.now(),
    )

    count = expired.update(is_active=False)
    logger.info("task_deactivate_expired_promotions deactivated=%d", count)
    return count


def expire_unconfirmed_subscriptions():
    """
    Mark pending subscriptions as expired if not paid within 24 hours.
    Run daily.
    """
    from django.utils import timezone
    from apps.subscriptions.models import VendorSubscription, SubscriptionStatus

    cutoff = timezone.now() - timezone.timedelta(hours=24)
    expired = VendorSubscription.objects.filter(
        status=SubscriptionStatus.PENDING,
        created_at__lt=cutoff,
    )

    count = expired.update(status=SubscriptionStatus.EXPIRED)
    logger.info("task_expire_unconfirmed_subscriptions expired=%d", count)
    return count


def expire_unpaid_orders():
    """
    Cancel orders not paid within the 30-minute payment window and return
    their stock to the bucket it came from.
    Run every 5 minutes.
    """
    from apps.orders.services.stock_service import release_expired_holds

    count = release_expired_holds()
    logger.info("task_expire_unpaid_orders cancelled=%d", count)
    return count


VENDOR_REMINDER_AFTER_HOURS = 2


def remind_vendors_waiting():
    """
    Remind vendors about paid orders they have not started on after 2 hours.
    Each order triggers at most one reminder. Orders are NOT auto-cancelled.
    Run every 5 minutes.
    """
    from django.utils import timezone
    from apps.businesses.models import Business
    from apps.orders.models import Order, OrderStatus
    from apps.notifications.services.notification_service import notify

    cutoff = timezone.now() - timezone.timedelta(hours=VENDOR_REMINDER_AFTER_HOURS)
    waiting = Order.objects.filter(
        status=OrderStatus.PAID,
        paid_at__lte=cutoff,
        vendor_reminder_sent_at__isnull=True,
    )

    sent = 0
    for order in waiting:
        owners = {
            b.owner
            for b in Business.objects.filter(products__orderitem__order=order)
            .select_related("owner")
            .distinct()
        }
        for owner in owners:
            try:
                notify(
                    user=owner,
                    title="An order is waiting for you",
                    body=(
                        f"Order {str(order.pk)[:8]} was paid over "
                        f"{VENDOR_REMINDER_AFTER_HOURS} hours ago. "
                        "Please start processing it, or cancel it with a reason."
                    ),
                    event_type="order.vendor_reminder",
                    payload={"order_id": str(order.pk)},
                )
                sent += 1
            except Exception as exc:
                logger.error("task_vendor_reminder_failed order=%s error=%s", order.pk, exc)
        order.vendor_reminder_sent_at = timezone.now()
        order.save(update_fields=["vendor_reminder_sent_at", "updated_at"])

    logger.info("task_remind_vendors_waiting sent=%d", sent)
    return sent


def run_all_frequent_tasks():
    """Run all tasks that should execute every 5 minutes."""
    expire_unpaid_orders()
    remind_vendors_waiting()
    expire_pickup_orders()


def run_all_hourly_tasks():
    """Run all tasks that should execute every hour."""
    expire_pickup_orders()
    send_pickup_reminders()
    deactivate_expired_promotions()


def run_all_daily_tasks():
    """Run all tasks that should execute once per day."""
    renew_subscriptions()
    expire_unconfirmed_subscriptions()
