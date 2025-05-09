from apps.cinema.models import CinemaHall, Movie, Reservation, ReservationSeat, Seat, Showtime
from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class SeatInline(admin.TabularInline):
    model = Seat
    extra = 0
    fields = ("row", "seat_number", "label")
    readonly_fields = ("label",)


@admin.register(CinemaHall)
class CinemaHallAdmin(admin.ModelAdmin):
    list_display = ("name", "rows", "seats_per_row", "total_seats")
    search_fields = ("name",)
    ordering = ("name",)
    inlines = [SeatInline]
    fieldsets = (
        (_("Basic Info"), {
            "fields": ("name",)
        }),
        (_("Seating Info"), {
            "fields": ("rows", "seats_per_row")
        }),
        (_("Media"), {
            "fields": ("image",)
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("label", "hall", "row", "seat_number", "created_at")
    list_filter = ("hall",)
    search_fields = ("label", "hall__name")
    ordering = ("hall", "row", "seat_number")
    fieldsets = (
        (None, {
            "fields": ("hall", "row", "seat_number", "label")
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("title", "duration", "created_at")
    search_fields = ("title",)
    ordering = ("title",)
    fieldsets = (
        (_("Basic Info"), {
            "fields": ("title", "poster", "duration")
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    readonly_fields = ("created_at", "updated_at")


@admin.register(Showtime)
class ShowtimeAdmin(admin.ModelAdmin):
    list_display = ("movie", "hall", "start_time", "is_expired", "created_at")
    list_filter = ("hall", "movie", "start_time")
    search_fields = ("movie__title", "hall__name")
    ordering = ("-start_time",)
    fieldsets = (
        (_("Showtime Info"), {
            "fields": ("movie", "hall", "start_time")
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    readonly_fields = ("created_at", "updated_at", "is_expired")


class ReservationSeatInline(admin.TabularInline):
    model = ReservationSeat
    extra = 0
    fields = ("seat",)
    autocomplete_fields = ("seat",)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("user", "showtime", "status", "reserved_at")
    list_filter = ("status", "reserved_at")
    search_fields = ("user__username", "showtime__movie__title")
    ordering = ("-reserved_at",)
    inlines = [ReservationSeatInline]
    fieldsets = (
        (_("Reservation Info"), {
            "fields": ("user", "showtime", "status")
        }),
        (_("Timestamps"), {
            "fields": ("reserved_at", "created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    readonly_fields = ("reserved_at", "created_at", "updated_at")


@admin.register(ReservationSeat)
class ReservationSeatAdmin(admin.ModelAdmin):
    list_display = ("seat", "reservation", "created_at")
    search_fields = ("seat__label", "reservation__user__username")
    list_filter = ("seat__hall",)
    ordering = ("-created_at",)
    fieldsets = (
        (_("Reservation Seat Info"), {
            "fields": ("seat", "reservation")
        }),
        (_("Timestamps"), {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
    readonly_fields = ("created_at", "updated_at")
