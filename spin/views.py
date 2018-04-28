from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import OperationalError
from django.shortcuts import render, redirect
from django.views.generic import FormView

from spin.controller import GameWorkflowController, NoMoneyError, DepletedError
from spin.models import MoneyChange


@login_required
def index(request):
    ctl = GameWorkflowController(request.user)
    return render(request, 'spin/index.html', {
        'wallets': ctl.wallets,
        'changes': MoneyChange.objects.filter(wallet__owner_id=request.user.pk)[:100],
        'active_wallet': ctl.get_active_wallet(),
        'error': request.session.pop('error_money', None),
    })


@login_required
def deposit(request):
    val = Decimal(request.POST['amountInCents']) / 100
    GameWorkflowController(request.user).deposit(val)
    return redirect('/')


@login_required
def spin(request):
    ctl = GameWorkflowController(request.user)
    wallet = ctl.get_active_wallet()
    try:
        ctl.spin(wallet)
    except NoMoneyError as e:
        wallet.set_depleted()
        request.session['error_money'] = 'No money in current wallet, please charge your wallet using Deposit button'
    except DepletedError as e:
        request.session['error_money'] = 'Wallet can\'t be used again'
    except OperationalError as e:
        request.session['error_money'] = str(e)
    return redirect('/')


class RegistrationView(FormView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = '/login/'

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)
