import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_422_UNPROCESSABLE_ENTITY
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView


class RouteRequestSerializer(serializers.Serializer):
    origin_latitude = serializers.FloatField(min_value=-90, max_value=90)
    origin_longitude = serializers.FloatField(min_value=-180, max_value=180)
    destination_latitude = serializers.FloatField(min_value=-90, max_value=90)
    destination_longitude = serializers.FloatField(min_value=-180, max_value=180)
    profile = serializers.ChoiceField(
        choices=("driving-car", "foot-walking", "cycling-regular"),
        default="driving-car",
    )


class NavigationRouteView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "navigation"

    def post(self, request):
        serializer = RouteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        api_key = getattr(settings, "ORS_API_KEY", "").strip()
        if not api_key:
            return Response(
                {"detail": "Route service is not configured on the server."},
                status=503,
            )

        payload = {
            "coordinates": [
                [values["origin_longitude"], values["origin_latitude"]],
                [values["destination_longitude"], values["destination_latitude"]],
            ],
            "instructions": True,
            "language": "en",
            "units": "m",
        }
        endpoint = (
            "https://api.heigit.org/openrouteservice/v2/directions/"
            f"{values['profile']}/geojson"
        )
        upstream = Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json",
                "Accept": "application/geo+json",
            },
            method="POST",
        )
        try:
            with urlopen(upstream, timeout=20) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429:
                return Response(
                    {"detail": "The route service limit was reached. Try again later."},
                    status=429,
                )
            return Response(
                {"detail": "The route service could not calculate this route."},
                status=502,
            )
        except (TimeoutError, URLError, OSError):
            return Response(
                {"detail": "Could not reach the route service. Check the connection and retry."},
                status=502,
            )
        except (ValueError, TypeError):
            return Response(
                {"detail": "The route service returned an unreadable response."},
                status=502,
            )

        features = result.get("features") or []
        if not features:
            return Response(
                {"detail": "No road route was found between these locations."},
                status=HTTP_422_UNPROCESSABLE_ENTITY,
            )
        feature = features[0]
        properties = feature.get("properties") or {}
        summary = properties.get("summary") or {}
        steps = [
            step
            for segment in properties.get("segments", [])
            for step in segment.get("steps", [])
        ]
        return Response(
            {
                "route": feature,
                "distance_meters": summary.get("distance"),
                "duration_seconds": summary.get("duration"),
                "steps": steps,
                "profile": values["profile"],
            }
        )
