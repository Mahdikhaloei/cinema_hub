from apps.cinema.views import HomeView, ReserveSeatsView, ShowtimeListView
from django.urls import path

app_name = "cinema"

urlpatterns = [
    path("home/", HomeView.as_view(), name="home"),
    path("hall/<int:hall_id>/showtimes/", ShowtimeListView.as_view(), name="hall_showtimes"),
    path("reserve/<int:showtime_id>/", ReserveSeatsView.as_view(), name="reserve_seats"),
]
