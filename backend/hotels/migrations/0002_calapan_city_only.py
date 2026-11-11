from django.db import migrations, models

# Freeze the original demonstration records, without touching user-created hotels.
SAMPLE_CHANGES = [
    {
        "before": {
            "name": "The Verde House",
            "city": "Tagaytay",
            "address": "Ridge Road, Barangay Maharlika",
            "latitude": 14.1153,
            "longitude": 120.9621,
            "description": "A quiet retreat above the ridge. Slow mornings, garden views, and thoughtfully designed rooms make space for a different pace.",
        },
        "after": {
            "name": "The Verde House",
            "city": "Calapan City",
            "description": "A peaceful Calapan City escape with garden views, thoughtfully designed rooms, and warm Mindoreno hospitality.",
            "latitude": 13.405,
            "longitude": 121.18,
            "address": "Sample Garden Lane, Calapan City, Oriental Mindoro",
        },
    },
    {
        "before": {
            "name": "Casa Amihan",
            "city": "Batangas",
            "address": "24 Mabini Avenue",
            "latitude": 13.7565,
            "longitude": 121.0583,
            "description": "Coastal simplicity, warm hospitality. Wake to sea breezes and spend your afternoons by our courtyard pool.",
        },
        "after": {
            "name": "Casa Amihan",
            "city": "Calapan City",
            "description": "A welcoming Calapan City retreat with a courtyard pool and comfortable rooms for your Oriental Mindoro visit.",
            "latitude": 13.411,
            "longitude": 121.185,
            "address": "Sample Courtyard Road, Calapan City, Oriental Mindoro",
        },
    },
    {
        "before": {
            "name": "The Escolta Rooms",
            "city": "Manila",
            "address": "18 Escolta Street, Binondo",
            "latitude": 14.5995,
            "longitude": 120.9842,
            "description": "A contemporary city hideaway with heritage details, a rooftop lounge, and the city at your doorstep.",
        },
        "after": {
            "name": "The Calapan Rooms",
            "city": "Calapan City",
            "description": "A contemporary city hideaway in Calapan with comfortable rooms and easy access to your Oriental Mindoro plans.",
            "latitude": 13.401,
            "longitude": 121.181,
            "address": "Sample City Center Lane, Calapan City, Oriental Mindoro",
        },
    },
    {
        "before": {
            "name": "Luntian Garden Stay",
            "city": "Los Banos",
            "address": "8 Makiling Road",
            "latitude": 14.1699,
            "longitude": 121.2441,
            "description": "A garden escape at the foot of Mount Makiling, with generous rooms and a locally inspired breakfast.",
        },
        "after": {
            "name": "Luntian Garden Stay",
            "city": "Calapan City",
            "description": "A relaxing garden stay in Calapan City with generous rooms and a locally inspired Mindoro breakfast.",
            "latitude": 13.397,
            "longitude": 121.177,
            "address": "Sample Greenway Road, Calapan City, Oriental Mindoro",
        },
    },
]


def localize_samples(apps, schema_editor):
    Hotel = apps.get_model("hotels", "Hotel")
    Photo = apps.get_model("hotels", "HotelPhoto")
    hotels = Hotel.objects.using(schema_editor.connection.alias)
    photos = Photo.objects.using(schema_editor.connection.alias)
    changes = []
    for change in SAMPLE_CHANGES:
        before = change["before"]
        ids = list(
            hotels.filter(
                owner__username="hotelowner",
                name=before["name"],
                city=before["city"],
                address=before["address"],
            ).values_list("pk", flat=True)
        )
        changes.append((change, ids))
    matched_ids = [pk for _, ids in changes for pk in ids]
    # Refuse to relabel a real, non-sample hotel as if it were in Calapan.
    aliases = ["Calapan", "Calapan City", "Calapan City, Oriental Mindoro"]
    if hotels.exclude(pk__in=matched_ids).exclude(city__in=aliases).exists():
        raise RuntimeError(
            "Non-sample properties outside Calapan exist. Review their actual locations before applying the Calapan-only constraint; no sample locations have been changed."
        )
    hotels.filter(city__in=aliases).update(city="Calapan City")
    for change, ids in changes:
        hotels.filter(pk__in=ids).update(**change["after"])
        photos.filter(hotel_id__in=ids, caption=change["before"]["name"]).update(
            caption=change["after"]["name"]
        )


def restore_samples(apps, schema_editor):
    Hotel = apps.get_model("hotels", "Hotel")
    Photo = apps.get_model("hotels", "HotelPhoto")
    hotels = Hotel.objects.using(schema_editor.connection.alias)
    for change in SAMPLE_CHANGES:
        after = change["after"]
        ids = list(
            hotels.filter(
                owner__username="hotelowner",
                name=after["name"],
                city=after["city"],
                address=after["address"],
            ).values_list("pk", flat=True)
        )
        hotels.filter(pk__in=ids).update(**change["before"])
        Photo.objects.using(schema_editor.connection.alias).filter(
            hotel_id__in=ids, caption=after["name"]
        ).update(caption=change["before"]["name"])


class Migration(migrations.Migration):
    dependencies = [("hotels", "0001_initial")]
    operations = [
        migrations.RunPython(localize_samples, restore_samples, atomic=True),
        migrations.AlterField(
            model_name="hotel",
            name="city",
            field=models.CharField(
                choices=[("Calapan City", "Calapan City")],
                default="Calapan City",
                help_text="RoomFinder serves Calapan City, Oriental Mindoro only.",
                max_length=80,
            ),
        ),
        migrations.AddConstraint(
            model_name="hotel",
            constraint=models.CheckConstraint(
                check=models.Q(city="Calapan City"), name="hotel_city_calapan_only"
            ),
        ),
    ]
