# Generated by Django 2.0.4 on 2018-04-25 16:21

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Bonus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('wagering', models.PositiveSmallIntegerField(default=20, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('money', models.DecimalField(db_index=True, decimal_places=2, default=100, max_digits=8)),
                ('type', models.CharField(choices=[('f', 'First login bonus'), ('d', 'Deposit of 100 euro')], default='d', max_length=1)),
            ],
            options={
                'ordering': ['money'],
            },
        ),
        migrations.CreateModel(
            name='MoneyChange',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('b', 'bonus'), ('t', 'money was taken from bonus'), ('d', 'deposit'), ('e', 'bet'), ('w', 'win the game'), ('c', 'bonus money converted to real wallet')], db_index=True, max_length=1)),
                ('created', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('money', models.DecimalField(db_index=True, decimal_places=2, max_digits=8)),
            ],
            options={
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_depleted', models.BooleanField(default=False)),
                ('is_real', models.BooleanField(default=False)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='moneychange',
            name='wallet',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='spin.Wallet'),
        ),
        migrations.AddField(
            model_name='bonus',
            name='wallet',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='spin.Wallet'),
        ),
    ]
