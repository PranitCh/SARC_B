from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Subscription, Transaction

@receiver(post_save, sender=Subscription)
def create_transaction_for_subscription(sender, instance, created, **kwargs):
    if not created:
        return

    t = Transaction.objects.create(
        budget=instance.budget,
        desc=f"Subscription: {instance.name}",
        amount=instance.amount,
        is_income=False,
        date=timezone.now().date()
    )
    instance.transaction = t
    instance.save(update_fields=["transaction"])
