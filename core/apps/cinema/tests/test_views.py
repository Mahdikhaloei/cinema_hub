from datetime import timedelta

from apps.cinema.models import CinemaHall, Reservation, ReservationSeat
from apps.cinema.tests.factories import (
    CinemaHallFactory, MovieFactory, ReservationFactory, ReservationSeatFactory, SeatFactory, ShowtimeFactory
)
from apps.user.tests.factories import UserFactory
from django.conf import settings
from django.contrib.messages import get_messages
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone


class HomeViewTest(TestCase):
    def setUp(self):
        self.hall1 = CinemaHall.objects.create(name="Hall 1", rows=5, seats_per_row=5)
        self.hall2 = CinemaHall.objects.create(name="Hall 2", rows=6, seats_per_row=6)

    def test_home_view_status_code(self):
        response = self.client.get(reverse("cinema:home"))
        self.assertEqual(response.status_code, 200)

    def test_home_view_template_used(self):
        response = self.client.get(reverse("cinema:home"))
        self.assertTemplateUsed(response, "pages/cinema/index.html")

    def test_home_view_context_contains_halls(self):
        response = self.client.get(reverse("cinema:home"))
        halls = response.context["halls"]
        self.assertIn(self.hall1, halls)
        self.assertIn(self.hall2, halls)
        self.assertEqual(len(halls), 2)


class ShowtimeListViewTest(TestCase):
    def setUp(self):
        self.hall = CinemaHallFactory()
        self.movie = MovieFactory()
        self.showtime1 = ShowtimeFactory(
            movie=self.movie,
            hall=self.hall,
            start_time=timezone.now() + timedelta(days=2)
        )
        self.showtime2 = ShowtimeFactory(
            movie=self.movie,
            hall=self.hall,
            start_time=timezone.now() + timedelta(hours=2)
        )
        self.seat1 = SeatFactory(hall=self.hall, row=1, seat_number=1)
        self.seat2 = SeatFactory(hall=self.hall, row=1, seat_number=2)
        self.user = UserFactory()
        self.reservation = ReservationFactory(user=self.user, showtime=self.showtime1, status="CONFIRMED")
        ReservationSeatFactory(reservation=self.reservation, seat=self.seat1)

    def test_status_code(self):
        url = reverse("cinema:hall_showtimes", args=[self.hall.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_template_used(self):
        url = reverse("cinema:hall_showtimes", args=[self.hall.id])
        response = self.client.get(url)
        self.assertTemplateUsed(response, "pages/cinema/hall_showtimes.html")

    def test_context_showtimes(self):
        url = reverse("cinema:hall_showtimes", args=[self.hall.id])
        response = self.client.get(url)
        showtimes = list(response.context["showtimes"])
        self.assertIn(self.showtime1, showtimes)
        self.assertIn(self.showtime2, showtimes)
        self.assertEqual(len(showtimes), 2)

    def test_context_hall(self):
        url = reverse("cinema:hall_showtimes", args=[self.hall.id])
        response = self.client.get(url)
        self.assertEqual(response.context["hall"], self.hall)

    def test_reserved_map(self):
        url = reverse("cinema:hall_showtimes", args=[self.hall.id])
        response = self.client.get(url)
        reserved_map = response.context["reserved_map"]
        self.assertIn(self.showtime1.id, reserved_map)
        self.assertIn(self.seat1.id, reserved_map[self.showtime1.id])
        self.assertNotIn(self.seat2.id, reserved_map[self.showtime1.id])

    def test_seats_map(self):
        url = reverse("cinema:hall_showtimes", args=[self.hall.id])
        response = self.client.get(url)
        seats_map = response.context["seats_map"]
        self.assertIn(self.hall.id, seats_map)
        self.assertGreaterEqual(len(seats_map[self.hall.id]), 2)


class ReserveSeatsViewTest(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)

        self.hall = CinemaHallFactory(rows=5, seats_per_row=5)
        self.movie = MovieFactory(duration=120)
        self.showtime = ShowtimeFactory(
            movie=self.movie,
            hall=self.hall,
            start_time=timezone.now() + timedelta(hours=2)
        )
        self.seat1 = SeatFactory(hall=self.hall, row=1, seat_number=1)
        self.seat2 = SeatFactory(hall=self.hall, row=1, seat_number=2)

    def test_reserve_seats_view_redirects_if_not_authenticated(self):
        self.client.logout()
        url = reverse("cinema:reserve_seats", kwargs={"showtime_id": self.showtime.id})
        response = self.client.post(url, {"seat_ids": f"{self.seat1.id},{self.seat2.id}"})
        self.assertEqual(response.status_code, 302)
        expected_url = f"{settings.LOGIN_URL}?next={url}"
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)

    def test_reserve_seats_view_successful_reservation(self):
        response = self.client.post(
            reverse("cinema:reserve_seats", kwargs={"showtime_id": self.showtime.id}),
            {"seat_ids": f"{self.seat1.id},{self.seat2.id}"}
        )
        self.assertRedirects(response, reverse("cinema:home"))

        reservation = Reservation.objects.filter(user=self.user, showtime=self.showtime).first()
        self.assertIsNotNone(reservation)
        self.assertEqual(reservation.reserved_seats.count(), 2)
        self.assertTrue(ReservationSeat.objects.filter(reservation=reservation, seat=self.seat1).exists())
        self.assertTrue(ReservationSeat.objects.filter(reservation=reservation, seat=self.seat2).exists())

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Your reservation was successful")

    def test_reserve_seats_view_empty_seat_ids(self):
        response = self.client.post(
            reverse("cinema:reserve_seats", kwargs={"showtime_id": self.showtime.id}),
            {"seat_ids": ""}
        )
        self.assertRedirects(response, reverse("cinema:hall_showtimes", kwargs={"hall_id": self.hall.id}))

        self.assertFalse(Reservation.objects.filter(user=self.user, showtime=self.showtime).exists())

        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(len(messages), 1)
        self.assertEqual(str(messages[0]), "Please select at least one seat")
