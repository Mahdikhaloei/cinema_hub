from typing import Any

from apps.cinema.models import CinemaHall, Reservation, ReservationSeat, Seat, Showtime
from apps.user.models import User
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.db import transaction
from django.http import HttpRequest, HttpResponseRedirect, response
from django.shortcuts import get_object_or_404, redirect
from django.utils.timezone import now
from django.views import View
from django.views.generic import ListView, TemplateView


class HomeView(TemplateView):
    template_name = "pages/cinema/index.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["halls"] = CinemaHall.objects.all()
        return context


class ShowtimeListView(ListView):
    model = Showtime
    template_name = "pages/cinema/hall_showtimes.html"
    context_object_name = "showtimes"

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> response.HttpResponseBase:
        self.hall = get_object_or_404(CinemaHall, id=self.kwargs["hall_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return (
            Showtime.objects
            .filter(hall=self.hall)
            .select_related("movie", "hall")
            .order_by("start_time")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["hall"] = self.hall
        context["reserved_map"] = self.get_reserved_map(context["showtimes"])
        context["seats_map"] = self.get_seats_map(self.hall)
        context["now"] = now()
        return context

    @staticmethod
    def get_reserved_map(showtimes: list[Showtime]) -> dict[int, list[int]]:
        showtime_ids = [st.id for st in showtimes]
        reserved_seats = ReservationSeat.objects.filter(
            reservation__showtime_id__in=showtime_ids,
            reservation__status__in=["PENDING", "CONFIRMED"]
        ).select_related("seat", "reservation")

        reserved_map: dict[int, list[int]] = {}

        for rs in reserved_seats:
            showtime_id = rs.reservation.showtime_id
            if showtime_id not in reserved_map:
                reserved_map[showtime_id] = []
            reserved_map[showtime_id].append(rs.seat.id)
        return reserved_map

    @staticmethod
    def get_seats_map(hall: CinemaHall) -> dict[int, list[dict[str, Any]]]:
        """Returns a dict mapping hall IDs to list of seat info."""
        seat_map = {}
        seats = Seat.objects.filter(hall=hall).order_by("row", "seat_number")
        seat_map[hall.id] = [
            {
                "id": seat.id,
                "label": seat.label,
                "row": seat.row,
                "seat_number": seat.seat_number,
            }
            for seat in seats
        ]
        return seat_map


class ReservationService:
    @staticmethod
    def create_reservation(user: User, showtime: Showtime, seat_ids: list[int]) -> Reservation:
        with transaction.atomic():
            reservation = Reservation.objects.create(user=user, showtime=showtime)
            for seat_id in seat_ids:
                seat = get_object_or_404(Seat, pk=seat_id, hall=showtime.hall)
                ReservationSeat.objects.create(reservation=reservation, seat=seat)
        return reservation


class ReserveSeatsView(LoginRequiredMixin, View):
    def post(self, request: HttpRequest, showtime_id: int) -> HttpResponseRedirect:
        if isinstance(request.user, AnonymousUser):
            messages.error(request, "You must be logged in to make a reservation.")
            return redirect("auth:auth_request")

        seat_ids_input = request.POST.get("seat_ids", "")
        seat_ids = [int(i) for i in seat_ids_input.split(",") if i.isdigit()]

        showtime = get_object_or_404(Showtime, pk=showtime_id)

        if not seat_ids:
            messages.error(request, "Please select at least one seat")
            return redirect("cinema:hall_showtimes", hall_id=showtime.hall.id)

        ReservationService.create_reservation(request.user, showtime, seat_ids)

        messages.success(request, "Your reservation was successful")
        return redirect("cinema:hall_showtimes", hall_id=showtime.hall.id)
