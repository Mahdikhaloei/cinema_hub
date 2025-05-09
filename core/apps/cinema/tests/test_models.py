from datetime import timedelta

from apps.cinema.models import CinemaHall, Seat, Showtime
from apps.cinema.tests.factories import (
    CinemaHallFactory, MovieFactory, ReservationFactory, ReservationSeatFactory, ShowtimeFactory
)
from apps.user.tests.factories import UserFactory
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone


class CinemaHallModelTestCase(TestCase):
    def setUp(self):
        self.hall = CinemaHallFactory(rows=8, seats_per_row=10, name="Test Hall")

    def test_cinema_hall_creation(self):
        self.assertIsInstance(self.hall, CinemaHall)
        self.assertEqual(self.hall.name, "Test Hall")
        self.assertEqual(self.hall.rows, 8)
        self.assertEqual(self.hall.seats_per_row, 10)

    def test_total_seats_property(self):
        self.assertEqual(self.hall.total_seats, 80)

    def test_str_method(self):
        self.assertEqual(str(self.hall), "Test Hall")

    def test_name_uniqueness(self):
        with self.assertRaises(IntegrityError):
            CinemaHall.objects.create(
                name="Test Hall", rows=5, seats_per_row=5
            )


class SeatModelTestCase(TestCase):
    def setUp(self):
        self.hall = CinemaHallFactory(rows=8, seats_per_row=10, name="Test Hall")

    def test_row_to_label_valid(self):
        seat = Seat(hall=self.hall, row=8, seat_number=10)
        self.assertEqual(seat.row_to_label(seat.row), "H")

    def test_row_to_label_invalid(self):
        seat = Seat(hall=self.hall, row=0, seat_number=1)
        with self.assertRaises(ValueError):
            seat.row_to_label(seat.row)

    def test_label_property(self):
        seat = Seat(hall=self.hall, row=2, seat_number=10)
        self.assertEqual(seat.label, "B10")

    def test_label_invalid_row(self):
        seat = Seat(hall=self.hall, row=0, seat_number=1)
        with self.assertRaises(ValueError):
            _ = seat.label


class MovieModelTestCase(TestCase):
    def setUp(self):
        self.movie = MovieFactory(title="inception")

    def test_str_method(self):
        self.assertEqual(str(self.movie), "inception")


class ShowTimeModelTestCase(TestCase):
    def setUp(self):
        self.movie = MovieFactory(
            title="inception",
            duration=120
        )
        self.hall = CinemaHallFactory(rows=10, seats_per_row=10)
        self.start_time = timezone.now() + timedelta(days=1)
        self.showtime = ShowtimeFactory(
            movie=self.movie,
            hall=self.hall,
            start_time=self.start_time
        )

    def test_str_method(self):
        expected_string = f"inception at {self.start_time} in {self.hall.name}"
        self.assertEqual(str(self.showtime), expected_string)

    def test_clean_start_time_in_the_past(self):
        self.showtime.start_time = timezone.now() - timedelta(days=1)
        with self.assertRaises(ValidationError):
            self.showtime.clean()

    def test_clean_conflicting_showtimes(self):
        with self.assertRaises(ValidationError):
            ShowtimeFactory(
            movie=self.movie,
            hall=self.hall,
            start_time=self.showtime.start_time + timedelta(minutes=60)
        )

    def test_is_expired(self):
        self.assertFalse(self.showtime.is_expired)
        expired_showtime = Showtime(
            movie=self.movie,
            hall=self.hall,
            start_time=timezone.now() - timedelta(days=1)
        )
        try:
            expired_showtime.full_clean()
        except ValidationError:
            pass
        self.assertTrue(expired_showtime.is_expired)

    def test_total_capacity(self):
        self.assertEqual(self.showtime.total_capacity, self.hall.total_seats)

    def test_reserved_seats_count(self):
        ReservationSeatFactory(reservation__showtime=self.showtime, reservation__status="PENDING")
        ReservationSeatFactory(reservation__showtime=self.showtime, reservation__status="CONFIRMED")
        self.assertEqual(self.showtime.reserved_seats_count, 2)

    def test_reserved_seats_list(self):
        reservation_seat_1 = ReservationSeatFactory(
            reservation__showtime=self.showtime,
            reservation__status="PENDING"
        )
        reservation_seat_2 = ReservationSeatFactory(
            reservation__showtime=self.showtime,
            reservation__status="CONFIRMED"
        )

        reserved_seats = self.showtime.reserved_seats_list
        self.assertEqual(len(reserved_seats), 2)
        self.assertIn(reservation_seat_1, reserved_seats)
        self.assertIn(reservation_seat_2, reserved_seats)

    def test_remaining_capacity(self):
        ReservationSeatFactory(reservation__showtime=self.showtime, reservation__status="PENDING")
        ReservationSeatFactory(reservation__showtime=self.showtime, reservation__status="CONFIRMED")
        self.assertEqual(self.showtime.remaining_capacity, self.showtime.total_capacity - 2)


class ReservationModelTestCase(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.showtime = ShowtimeFactory()
        self.reservation = ReservationFactory(
            user=self.user,
            showtime=self.showtime,
        )

    def test_str_method(self):
        expected_string = f"Reservation by {self.user.email} for {self.showtime}"
        self.assertEqual(str(self.reservation), expected_string)


class ReservationSeatModelTestCase(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.showtime = ShowtimeFactory(start_time=timezone.now() + timedelta(hours=1))
        self.reservation = ReservationFactory(user=self.user, showtime=self.showtime, status="PENDING")
        self.reservation_seat = ReservationSeatFactory(reservation=self.reservation)

    def test_str_method(self):
        expected_string = f"{self.reservation_seat.seat} reserved for {self.reservation.showtime}"
        self.assertEqual(str(self.reservation_seat), expected_string)
