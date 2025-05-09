from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CinemaHall, Seat


@receiver(post_save, sender=CinemaHall)
def create_seats_for_hall(sender, instance, created, **kwargs):
    """
    Create seats for a CinemaHall after it's created.
    """
    if created:
        for row in range(1, instance.rows + 1):
            for seat_number in range(1, instance.seats_per_row + 1):
                Seat.objects.create(
                    hall=instance,
                    row=row,
                    seat_number=seat_number
                )
