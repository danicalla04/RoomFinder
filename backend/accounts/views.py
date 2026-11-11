from rest_framework.generics import CreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from smtplib import SMTPException
from .serializers import (
    RegisterSerializer,
    UserSerializer,
    RoleTokenObtainPairSerializer,
)
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import User
from hotels.models import Hotel
from rooms.models import Floor, Room, RoomPhoto
from bookings.models import Booking
from django.shortcuts import get_object_or_404
from .email_verification import verify_code, resend_wait_seconds, send_verification
from .serializers import EmailDeliveryUnavailable
from accounts.permissions import IsAdmin


class RegisterView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class MeView(RetrieveUpdateAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class RoleTokenObtainPairView(TokenObtainPairView):
    serializer_class = RoleTokenObtainPairSerializer


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "")
        code = request.data.get("code", "")
        if not isinstance(email, str) or not isinstance(code, str) or not email or not code:
            return Response({"detail": "Enter your email and six-digit code."}, status=400)
        with transaction.atomic():
            user = verify_code(email, code)
            if not user:
                return Response({"detail": "This code is invalid or expired. Request another email if needed."}, status=400)
        detail = (
            "Email verified. Your hotel-owner request is awaiting administrator approval."
            if not user.is_active
            else "Email verified. You can now sign in."
        )
        return Response({"detail": detail, "can_sign_in": user.is_active})


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "")
        if not isinstance(email, str) or not email:
            return Response({"email": ["Enter your email address."]}, status=400)
        try:
            with transaction.atomic():
                user = User.objects.select_for_update().get(
                    email__iexact=email.strip(), is_active=False, email_verified_at__isnull=True
                )
                wait = resend_wait_seconds(user)
                if wait:
                    return Response({"detail": f"Please wait {wait} seconds before requesting another email.", "retry_after": wait}, status=429)
                send_verification(user)
        except User.DoesNotExist:
            pass
        except (OSError, RuntimeError, SMTPException) as exc:
            raise EmailDeliveryUnavailable() from exc
        return Response({"detail": "If this account needs verification, a new email has been sent."})


class AdminUsersView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        users = User.objects.order_by("-date_joined", "-id").only(
            "id", "username", "first_name", "last_name", "email", "role", "is_active", "email_verified_at",
            "owner_approval_status", "date_joined"
        )
        hotels_by_owner = {}
        for hotel in Hotel.objects.order_by("name").values(
            "id", "owner_id", "name", "address", "city", "status", "description"
        ):
            hotels_by_owner.setdefault(hotel["owner_id"], []).append({
                key: value for key, value in hotel.items() if key != "owner_id"
            })
        return Response([
            {
                "id": user.id,
                "username": user.username,
                "display_name": user.get_full_name() or user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "email_verified": bool(user.email_verified_at),
                "owner_approval_status": user.owner_approval_status if user.role == User.Role.OWNER else None,
                "hotels": hotels_by_owner.get(user.id, []) if user.role == User.Role.OWNER else [],
                "date_joined": user.date_joined,
            }
            for user in users
        ])


class ReviewOwnerView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        decision = request.data.get("decision")
        if decision not in (User.OwnerApproval.APPROVED, User.OwnerApproval.REJECTED):
            return Response({"detail": "Choose approved or rejected."}, status=400)
        with transaction.atomic():
            try:
                owner = User.objects.select_for_update().get(pk=pk, role=User.Role.OWNER)
            except User.DoesNotExist:
                return Response({"detail": "Hotel owner not found."}, status=404)
            if owner.owner_approval_status == decision:
                return Response({"detail": "This request already has that decision."}, status=400)
            if decision == User.OwnerApproval.APPROVED and not owner.email_verified_at:
                return Response({"detail": "The owner must verify their email first."}, status=400)
            owner.owner_approval_status = decision
            owner.is_active = decision == User.OwnerApproval.APPROVED and bool(owner.email_verified_at)
            owner.save(update_fields=["owner_approval_status", "is_active"])
        return Response({"detail": "Owner request updated.", "status": owner.owner_approval_status})


class AdminHotelOverviewView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        hotel = get_object_or_404(Hotel.objects.select_related("owner"), pk=pk)
        floors = list(Floor.objects.filter(hotel=hotel).order_by("number").values(
            "id", "number", "name", "columns"
        ))
        rooms = list(Room.objects.filter(floor__hotel=hotel).order_by("floor__number", "number").values(
            "id", "floor_id", "number", "kind", "description", "price", "capacity",
            "beds", "area", "row", "column", "active", "floor__number"
        ))
        photos_by_room = {}
        for photo in RoomPhoto.objects.filter(room__floor__hotel=hotel).values(
            "room_id", "image", "caption"
        ):
            photos_by_room.setdefault(photo["room_id"], []).append({
                "image": request.build_absolute_uri(f"/media/{photo['image']}"),
                "caption": photo["caption"],
            })
        for room in rooms:
            room["photos"] = photos_by_room.get(room["id"], [])
        bookings = list(Booking.objects.filter(room__floor__hotel=hotel).order_by("-created_at").values(
            "id", "reference", "customer__username", "room_id", "room__number", "check_in",
            "check_out", "guests", "total", "status", "payment__status"
        ))
        return Response({
            "hotel": {
                "id": hotel.id, "name": hotel.name, "description": hotel.description,
                "owner": hotel.owner.username, "address": hotel.address, "city": hotel.city,
                "status": hotel.status, "stars": hotel.stars, "verification_note": hotel.verification_note,
            },
            "floors": floors,
            "rooms": rooms,
            "bookings": bookings,
        })
