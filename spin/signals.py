from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save

from spin.controller import GameWorkflowController
from spin.models import Wallet


def add_login_bonus(sender, user, request, **kwargs):
    GameWorkflowController(user).login_bonus()


def create_user_profile(sender, **kwargs):
    if kwargs.get('created'):
        Wallet(owner=kwargs.get('instance'), is_real=True).save()


post_save.connect(create_user_profile, sender=User, dispatch_uid="create_user_profile")

user_logged_in.connect(add_login_bonus)
