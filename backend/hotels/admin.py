from django.contrib import admin
from .models import Hotel, HotelPhoto


@admin.register(Hotel)
class HotelAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "owner", "status")
    list_filter = ("status",)
    search_fields = ("name", "address", "owner__username")
    readonly_fields = ("city",)


admin.site.register(HotelPhoto)
