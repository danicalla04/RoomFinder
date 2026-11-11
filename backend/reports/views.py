import csv
from datetime import datetime, time, timedelta
from decimal import Decimal
from django.http import HttpResponse
from django.db.models import Sum, Count
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from accounts.permissions import admin
from bookings.models import Booking
from bookings.demo import DEMO_PREFIX
from hotels.models import Hotel
from hotels.location import CITY_NAME, PROVINCE_NAME, LOCATION_LABEL
from rooms.models import Room
from accounts.models import User


class ReportView(APIView):
    def get(self, request):
        if not admin(request.user) and request.user.role != "owner":
            raise PermissionDenied(
                "Reports are restricted to hotel owners and administrators."
            )
        hotels = (
            Hotel.objects.filter(city=CITY_NAME)
            if admin(request.user)
            else Hotel.objects.filter(city=CITY_NAME, owner=request.user)
        )
        bookings = Booking.objects.filter(room__floor__hotel__in=hotels)
        if request.query_params.get("format") == "csv":
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = (
                'attachment; filename="roomfinder-report.csv"'
            )
            writer = csv.writer(response)
            writer.writerow(
                [
                    "Reference",
                    "Hotel",
                    "City",
                    "Province",
                    "Room",
                    "Check in",
                    "Check out",
                    "Status",
                    "Total PHP",
                    "Data type",
                ]
            )
            for b in bookings.select_related("room__floor__hotel"):
                writer.writerow(
                    [
                        b.reference,
                        b.room.floor.hotel.name,
                        CITY_NAME,
                        PROVINCE_NAME,
                        b.room.number,
                        b.check_in,
                        b.check_out,
                        b.status,
                        b.total,
                        (
                            "Demo"
                            if b.special_requests.startswith(DEMO_PREFIX)
                            else "Reservation"
                        ),
                    ]
                )
            return response
        confirmed = bookings.filter(status="confirmed")
        today = timezone.localdate()
        room_count = Room.objects.filter(floor__hotel__in=hotels, active=True).count()
        occupied = (
            confirmed.filter(check_in__lte=today, check_out__gt=today)
            .values("room_id")
            .distinct()
            .count()
        )
        trend = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            # Filter with aware Manila day boundaries. SQL __date casts need
            # MySQL timezone tables, which are often absent in XAMPP installs.
            day_start = timezone.make_aware(
                datetime.combine(day, time.min), timezone.get_current_timezone()
            )
            day_end = day_start + timedelta(days=1)
            day_filter = {"created_at__gte": day_start, "created_at__lt": day_end}
            trend.append(
                {
                    "date": day.isoformat(),
                    "bookings": bookings.filter(**day_filter).count(),
                    "revenue": confirmed.filter(**day_filter).aggregate(v=Sum("total"))[
                        "v"
                    ]
                    or 0,
                }
            )
        return Response(
            {
                "city": CITY_NAME,
                "province": PROVINCE_NAME,
                "location": LOCATION_LABEL,
                "hotel_count": hotels.count(),
                "pending_hotels": hotels.filter(status="pending").count(),
                "room_count": room_count,
                "booking_count": bookings.count(),
                "demo_booking_count": bookings.filter(
                    special_requests__startswith=DEMO_PREFIX
                ).count(),
                "confirmed_count": confirmed.count(),
                "revenue": confirmed.aggregate(v=Sum("total"))["v"] or Decimal("0"),
                "occupancy": round(occupied / room_count * 100, 1) if room_count else 0,
                "customer_count": (
                    User.objects.filter(role="customer").count()
                    if admin(request.user)
                    else bookings.values("customer_id").distinct().count()
                ),
                "trend": trend,
                "top_hotels": list(
                    confirmed.values("room__floor__hotel__name")
                    .annotate(bookings=Count("id"), revenue=Sum("total"))
                    .order_by("-revenue")[:5]
                ),
            }
        )
