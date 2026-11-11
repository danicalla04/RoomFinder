from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve as serve_media
from django.http import JsonResponse
from django.db import connection
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.views import RegisterView, MeView, RoleTokenObtainPairView, VerifyEmailView, ResendVerificationView, AdminUsersView, ReviewOwnerView, AdminHotelOverviewView
from hotels.views import HotelViewSet, HotelPhotoViewSet
from rooms.views import FloorViewSet, RoomViewSet, RoomPhotoViewSet
from bookings.views import BookingViewSet
from payments.views import PaymentViewSet
from promotions.views import PromotionViewSet
from reviews.views import ReviewViewSet
from notifications.views import NotificationViewSet
from reports.views import ReportView

router = DefaultRouter()
for prefix, view, basename in [
    ("hotels", HotelViewSet, "hotel"),
    ("hotel-photos", HotelPhotoViewSet, "hotel-photo"),
    ("floors", FloorViewSet, "floor"),
    ("rooms", RoomViewSet, "room"),
    ("room-photos", RoomPhotoViewSet, "room-photo"),
    ("bookings", BookingViewSet, "booking"),
    ("payments", PaymentViewSet, "payment"),
    ("promotions", PromotionViewSet, "promotion"),
    ("reviews", ReviewViewSet, "review"),
    ("notifications", NotificationViewSet, "notification"),
]:
    router.register(prefix, view, basename=basename)


def health(request):
    with connection.cursor() as cursor:
        database_function = "current_database()" if connection.vendor == "postgresql" else "DATABASE()"
        cursor.execute(f"SELECT {database_function}, VERSION()")
        database, version = cursor.fetchone()
    return JsonResponse({"status": "ok", "database": database, "engine": version})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health),
    path("api/v1/auth/register/", RegisterView.as_view()),
    path("api/v1/auth/verify-email/", VerifyEmailView.as_view()),
    path("api/v1/auth/resend-verification/", ResendVerificationView.as_view()),
    path("api/v1/admin/users/", AdminUsersView.as_view()),
    path("api/v1/admin/users/<int:pk>/review/", ReviewOwnerView.as_view()),
    path("api/v1/admin/hotels/<int:pk>/", AdminHotelOverviewView.as_view()),
    path("api/v1/auth/token/", RoleTokenObtainPairView.as_view()),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view()),
    path("api/v1/auth/me/", MeView.as_view()),
    path("api/v1/reports/summary/", ReportView.as_view()),
    path("api/v1/", include(router.urls)),
]

# Uploaded hotel and room photos are public. The volume keeps them across deploys.
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", serve_media, {"document_root": settings.MEDIA_ROOT})
]
