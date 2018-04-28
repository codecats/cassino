import random
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils.functional import cached_property

from spin.models import MoneyChange, Bonus, Wallet


class GameMoneyError(BaseException):
    pass


class NoMoneyError(GameMoneyError):
    pass


class DepletedError(GameMoneyError):
    pass


class WalletController(object):
    def __init__(self, wallet):
        self.wallet = wallet

    def get_money(self):
        '''
        General money for wallet
        :return:
        '''
        return self.wallet.moneychange_set.exclude(type=MoneyChange.TYPE_BONUS_TAKEN).aggregate(Sum('money'))[
                   'money__sum'] or Decimal(0)

    def get_bonus_money(self):
        '''
        money from bonus
        :return:
        '''
        if not hasattr(self.wallet, 'bonus'):
            return Decimal(0)
        return self.wallet.bonus.money

    def get_play_money(self):
        '''
        amout that is allowed to play
        :return:
        '''
        return self.get_money() + self.get_bonus_money()

    def get_spend_money(self, after=None, add_real_wallet=False, add_bns_wallets=False):
        '''
        money that was spend from wallet(s) determined by given arguments
        :param after: all spends after given date
        :param add_real_wallet: to current wallet add real money wallet
        :param add_bns_wallets: to current wallet add all bonus money wallet (even depleted)
        :return: Decimal
        '''
        kwargs = {} if after is None else {'created__gt': after}
        wallets = self.wallet.owner.wallet_set.all()
        if add_real_wallet:
            wallets = wallets.filter(is_real=True)
        if add_bns_wallets:
            wallets = wallets.filter(is_real=False).exclude(pk=self.wallet.pk)
        wallets = list(wallets.values_list('id', flat=True)) + [self.wallet.pk]
        if not add_real_wallet and not add_bns_wallets:
            wallets = [self.wallet.pk]
        kwargs.update(dict(wallet_id__in=wallets, money__lt=Decimal(0)))
        return abs(MoneyChange.objects.filter(**kwargs).aggregate(Sum('money'))['money__sum'] or Decimal(0))

    def change_safe(self, money, type_=MoneyChange.TYPE_DEPOSIT):
        '''
        change money in current wallet, before change there is sanity checking
        :param money:
        :param type_:
        :return:
        '''
        money = Decimal(money)
        self.can_change(money)
        self.change(money, type_)

    def can_change(self, money):
        '''
        Sanity checking of change (check if change is allowed)
        :param money:
        :return:
        '''
        money = Decimal(money)
        if self.wallet.is_depleted:
            raise DepletedError()
        if money < 0:
            if self.get_play_money() < abs(money):
                raise NoMoneyError()

    def change(self, money: Decimal, type_=MoneyChange.TYPE_DEPOSIT):
        '''
        Change value without any checking, this method only change value in current wallet
        :param money:
        :param type_:
        :return:
        '''
        ch = MoneyChange(money=money, wallet=self.wallet, type=type_)
        ch.save()
        return ch

    def set_bonus(self, money: Decimal, wagering=2, type_=Bonus.TYPE_DEPOSIT):
        b = Bonus(money=money, wallet=self.wallet, wagering=wagering, type=type_)
        b.save()
        return b

    def can_convert(self):
        '''
        Proxy method that check if there is a bonus and it can be converted
        :return:
        '''
        if not hasattr(self.wallet, 'bonus'):
            return False
        return self.wallet.bonus.can_convert

    def set_depleted(self):
        '''
        Sets wallet in depleted state
        :return:
        '''
        if not self.wallet.is_real and self.get_play_money() < GameWorkflowController.DEPLETED:
            self.wallet.is_depleted = True
            self.wallet.save()


class GameWorkflowController(object):
    BET = Decimal(2)
    WIN = Decimal(2)
    DEPLETED = Decimal(2)  # under or equal this value wallet is depleted

    def __init__(self, user):
        self.user = user

    @cached_property
    def is_won(self):
        '''
        :return: bool - random result
        '''
        return bool(random.getrandbits(1))

    @cached_property
    def wallets(self):
        '''
        All wallets associated with user
        :return:
        '''
        return [WalletController(x) for x in self.user.wallet_set.all()]

    @cached_property
    def bns_convertable_wallets(self):
        '''
        Only convertable wallets
        :return:
        '''
        return [x for x in self.wallets
                if not x.wallet.is_real and not x.wallet.is_depleted and x.can_convert()]

    @cached_property
    def real_wallet(self):
        '''
        Real wallet (always should exists)
        :return:
        '''
        return next(filter(lambda x: x.wallet.is_real, self.wallets), None)

    def get_active_wallet(self):
        '''
        Real money wallet always is taken first, if there is no money on it BNS wallet is taken.
        If there is not BNS wallet method returns None
        :return:
        '''
        real_wallet = self.real_wallet
        if real_wallet.get_play_money() >= self.BET:
            return real_wallet
        for wallet in self.wallets:
            if not wallet.wallet.is_depleted and wallet.get_play_money() >= self.BET:
                return wallet

    def convert_bonuses(self):
        '''
        Convert all bonuses to real money wallet
        :return:
        '''
        for w in self.bns_convertable_wallets:
            self.convert_bonus(w)

    def convert_bonus(self, wallet:WalletController):
        '''
        Atomic convert bonus
        :param wallet:
        :return:
        '''
        money = wallet.get_play_money()
        with transaction.atomic():
            self.real_wallet.change(money, MoneyChange.TYPE_BONUS_CONVERTED)
            wallet.change(money * -1, MoneyChange.TYPE_BONUS_CONVERTED)
            wallet.wallet.is_depleted = True
            wallet.wallet.save()

    def deposit(self, value: Decimal):
        '''
        Pay user deposit, high level method
        :param value:
        :return:
        '''
        money_wallet = self.user.wallet_set.filter(is_real=True).first()
        # shadow condition for sanity check
        if money_wallet is None:
            raise RuntimeError('Missing real money wallet')
        money_wallet = WalletController(money_wallet)
        with transaction.atomic():
            money_wallet.change(value)
            self.deposit_bonus(value)

    def deposit_bonus(self, value: Decimal):
        '''
        Check and add bonus on deposit event
        :param value:
        :return:
        '''
        if value > Decimal(100):
            self._set_bonus(self.user, Decimal(20), 10)

    def login_bonus(self):
        '''
        check and add bonus on login event
        :return:
        '''
        if self.user.last_login is None:
            self._set_bonus(self.user, Decimal(100), 10)

    @classmethod
    def _set_bonus(cls, user, money: Decimal, wagering: int):
        '''
        Generic way to set a bonus
        :param user: User
        :param money:
        :param wagering:
        :return:
        '''
        wallet = WalletController(Wallet.objects.create(owner=user, is_real=False))
        wallet.set_bonus(money, wagering)

    def spin(self, wallet: WalletController):
        '''
        High level function to play a spin game
        :param wallet:
        :return:
        '''
        bet, win = self.BET * -1, self.WIN
        with transaction.atomic():
            wallet.change_safe(bet, MoneyChange.TYPE_BET)
            if self.is_won:
                wallet.change_safe(win + abs(bet), MoneyChange.TYPE_WIN)
            wallet.set_depleted()
            self.convert_bonuses()
