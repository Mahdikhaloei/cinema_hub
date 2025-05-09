from datetime import timedelta

import factory
from apps.cinema.models import CinemaHall, Movie, Reservation, ReservationSeat, Seat, Showtime
from apps.user.tests.factories import UserFactory
from django.contrib.auth import get_user_model
from django.utils import timezone
from faker import Faker

fake = Faker()
User = get_user_model()



class CinemaHallFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CinemaHall

    name = factory.Sequence(lambda n: f"Hall {n}")
    rows = factory.Faker("random_int", min=5, max=10)
    seats_per_row = factory.Faker("random_int", min=5, max=10)
    image = None


class SeatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Seat

    hall = factory.SubFactory(CinemaHallFactory)
    row = factory.Sequence(lambda n: (n // 20) + 1)
    seat_number = factory.Sequence(lambda n: (n % 20) + 1)


class MovieFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Movie

    title = factory.Sequence(lambda n: f"Movie {n}")
    duration = factory.Faker("random_int", min=60, max=180)
    poster = None


class ShowtimeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Showtime

    movie = factory.SubFactory(MovieFactory)
    hall = factory.SubFactory(CinemaHallFactory)
    start_time = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=1))


class ReservationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Reservation

    user = factory.SubFactory(UserFactory)
    showtime = factory.SubFactory(ShowtimeFactory)


class ReservationSeatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReservationSeat

    reservation = factory.SubFactory(ReservationFactory)
    seat = factory.SubFactory(SeatFactory)
