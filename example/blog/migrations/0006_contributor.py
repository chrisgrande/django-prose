from django.db import migrations, models


def seed_contributors(apps, schema_editor):
    Contributor = apps.get_model("blog", "Contributor")
    contributors = [
        ("Jane Doe", "JD"),
        ("Alex Kim", "AK"),
        ("Sam Rivera", "SR"),
    ]
    for name, initials in contributors:
        Contributor.objects.get_or_create(name=name, defaults={"initials": initials})


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0005_alter_article_excerpt_comment"),
    ]

    operations = [
        migrations.CreateModel(
            name="Contributor",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("initials", models.CharField(blank=True, max_length=10)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.RunPython(seed_contributors, migrations.RunPython.noop),
    ]
