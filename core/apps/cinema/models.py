from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count
from django.db.models.query import QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from utils.mixins.models import Timestampable

User = get_user_model()


class CinemaHall(Timestampable, models.Model):
    """
     Model representing a cinema hall in the CinemaHub application.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name=_("room name"))
    rows = models.PositiveIntegerField(verbose_name=_("rows number"))
    seats_per_row = models.PositiveIntegerField(verbose_name=_("seats per row"))
    image = models.ImageField(
        upload_to="cinema_hall/images/",
        blank=True,
        null=True,
        verbose_name=_("cinema hall image")
    )

    class Meta:
        verbose_name = _("Cinema Hall")
        verbose_name_plural = _("Cinema Halls")

    def __str__(self) -> str:
        return self.name

    @property
    def total_seats(self) -> int:
        return self.rows * self.seats_per_row


class Seat(Timestampable, models.Model):
    """
    Model representing a seat in a cinema hall.
    """
    hall = models.ForeignKey(
        CinemaHall,
        on_delete=models.CASCADE,
        related_name="seats",
        verbose_name=_("cinema hall")
    )
    row = models.PositiveIntegerField(verbose_name=_("row number"))
    seat_number = models.PositiveIntegerField(verbose_name=_("seat number"))

    @staticmethod
    def row_to_label(row: int) -> str:
        """
        Convert a row number to a label (e.g., 1 -> A, 27 -> AA).
        """
        if row is None or row <= 0:
            raise ValueError("Row number must be a positive integer")
        label = ""
        while row > 0:
            row -= 1
            label = chr(row % 26 + 65) + label
            row //= 26
        return label

    @property
    def label(self) -> str:
        """
        Generate the label for the seat, combining row letters and seat number.
        """
        row_letter = self.row_to_label(self.row)
        return f"{row_letter}{self.seat_number}"

    def __str__(self) -> str:
        return f"{self.hall.name} - Seat {self.label}"

    class Meta:
        verbose_name = _("Seat")
        verbose_name_plural = _("Seats")


class Movie(Timestampable, models.Model):
    """
    Model representing a movie in the CinemaHub application.
    """
    title = models.CharField(max_length=200, unique=True, verbose_name=_("movie title"))
    poster = models.ImageField(
        upload_to="movies/posters/",
        blank=True,
        null=True,
        verbose_name=_("movie poster")
    )
    duration = models.PositiveIntegerField(verbose_name=_("movie duration (minutes)"))

    class Meta:
        verbose_name = _("Movie")
        verbose_name_plural = _("Movies")

    def __str__(self) -> str:
        return self.title


class Showtime(Timestampable, models.Model):
    """
    Model representing a movie showtime in a specific cinema hall.
    """
    movie = models.ForeignKey(
        Movie,
        on_delete=models.CASCADE,
        related_name="showtimes",
        verbose_name=_("movie")
    )
    hall = models.ForeignKey(
        CinemaHall,
        on_delete=models.CASCADE,
        related_name="showtimes",
        verbose_name=_("cinema hall")
    )
    start_time = models.DateTimeField(verbose_name=_("start time"))

    class Meta:
        verbose_name = _("Showtime")
        verbose_name_plural = _("Showtimes")

    def __str__(self) -> str:
        return f"{self.movie.title} at {self.start_time} in {self.hall.name}"

    def clean(self):
        if self.start_time < timezone.now():
            raise ValidationError(_("Showtime cannot be in the past."))

        conflicting_showtimes = Showtime.objects.filter(
            hall=self.hall,
            start_time__lt=self.start_time + timedelta(minutes=self.movie.duration),
            start_time__gt=self.start_time - timedelta(minutes=self.movie.duration)
        ).exclude(pk=self.pk)

        if conflicting_showtimes.exists():
            raise ValidationError(_("This showtime conflicts with another showtime in the same hall."))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        end_time = self.start_time + timedelta(minutes=self.movie.duration)
        return timezone.now() > end_time

    @property
    def total_capacity(self) -> int:
        return self.hall.total_seats

    @property
    def reserved_seats_count(self) -> int:
        queryset = ReservationSeat.objects.filter(
            reservation__showtime=self,
            reservation__status__in=["PENDING", "CONFIRMED"]
        )
        return queryset.aggregate(count=Count("id"))["count"]

    @property
    def reserved_seats_list(self) -> QuerySet["ReservationSeat"]:
        return ReservationSeat.objects.filter(
            reservation__showtime=self,
            reservation__status__in=["PENDING", "CONFIRMED"]
        ).select_related("seat", "reservation")

    @property
    def remaining_capacity(self) -> int:
        return self.total_capacity - self.reserved_seats_count


class ReservationStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    CONFIRMED = "CONFIRMED", _("Confirmed")
    CANCELED = "CANCELED", _("Canceled")


class Reservation(Timestampable, models.Model):
    """
    Model representing a user's reservation for a showtime
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="reservations",
        verbose_name=_("user")
    )
    showtime = models.ForeignKey(
        Showtime,
        on_delete=models.CASCADE,
        related_name="reservations",
        verbose_name=_("show time")
    )
    reserved_at = models.DateTimeField(auto_now_add=True, verbose_name=_("reserved at"))
    status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.PENDING,
        verbose_name=_("status")
    )

    class Meta:
        verbose_name = _("Reservation")
        verbose_name_plural = _("Reservations")

    def __str__(self) -> str:
        return f"Reservation by {self.user.email} for {self.showtime}"

    def clean(self):
        if self.showtime.is_expired:
            raise ValidationError(_("Cannot reserve an expired showtime."))


class ReservationSeat(Timestampable, models.Model):
    """
    Model representing a reserved seat for a reservation.
    """
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="reserved_seats",
        verbose_name=_("reservation")
    )
    seat = models.ForeignKey(
        Seat,
        on_delete=models.CASCADE,
        related_name="reserved_seats",
        verbose_name=_("seat")
    )

    class Meta:
        verbose_name = _("Reservation Seat")
        verbose_name_plural = _("Reservation Seats")
        constraints = [
            models.UniqueConstraint(
                fields=["seat", "reservation"],
                name="unique_seat_reservation"
            )
        ]

    def __str__(self) -> str:
        return f"{self.seat} reserved for {self.reservation.showtime}"

    def clean(self):
        existing_reservations = ReservationSeat.objects.filter(
            seat=self.seat,
            reservation__showtime=self.reservation.showtime,
            reservation__status__in=["PENDING", "CONFIRMED"]
        ).exclude(reservation=self.reservation)

        if existing_reservations.exists():
            raise ValidationError(_("This seat is already reserved for this showtime."))

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
