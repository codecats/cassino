from django.contrib.auth.models import User

from spin.models import Wallet


class CleanMixin():

    def _clean_data(self):
        Wallet.objects.all().delete()
        User.objects.all().delete()