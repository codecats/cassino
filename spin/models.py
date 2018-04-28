from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Model, ForeignKey, PositiveSmallIntegerField, CASCADE, BooleanField, DateTimeField, \
    CharField, OneToOneField, DecimalField


class Wallet(Model):
    owner = ForeignKey(User, on_delete=CASCADE)
    is_depleted = BooleanField(default=False)
    is_real = BooleanField(default=False)


class MoneyChange(Model):
    class Meta:
        ordering = ['-created']

    TYPE_BONUS = 'b'
    TYPE_BONUS_TAKEN = 't'
    TYPE_DEPOSIT = 'd'
    TYPE_BET = 'e'
    TYPE_WIN = 'w'
    TYPE_BONUS_CONVERTED = 'c'

    TYPE_CHOICES = (
        (TYPE_BONUS, 'bonus'),
        (TYPE_BONUS_TAKEN, 'money was taken from bonus'),
        (TYPE_DEPOSIT, 'deposit'),
        (TYPE_BET, 'bet'),
        (TYPE_WIN, 'win the game'),
        (TYPE_BONUS_CONVERTED, 'bonus money converted to real wallet'),
    )
    type = CharField(choices=TYPE_CHOICES, max_length=1, db_index=True)
    created = DateTimeField(auto_now_add=True, blank=True, db_index=True)
    wallet = ForeignKey(Wallet, on_delete=CASCADE)
    money = DecimalField(max_digits=8, decimal_places=2, db_index=True)


class Bonus(Model):
    class Meta:
        ordering = ['money']

    TYPE_FIRST_LOGIN = 'f'
    TYPE_DEPOSIT = 'd'
    AMOUNT_DEPOSIT = 100
    TYPE_CHOICES = (
        (TYPE_FIRST_LOGIN, 'First login bonus'),
        (TYPE_DEPOSIT, 'Deposit of {} euro'.format(AMOUNT_DEPOSIT))
    )
    WAGERING_MIN = 0
    WAGERING_MAX = 100
    created = DateTimeField(auto_now_add=True, blank=True, db_index=True)
    wallet = OneToOneField(Wallet, on_delete=CASCADE)
    wagering = PositiveSmallIntegerField(default=20,
                                         validators=[MinValueValidator(WAGERING_MIN), MaxValueValidator(WAGERING_MAX)])
    money = DecimalField(default=100, max_digits=8, decimal_places=2,
                         db_index=True)
    type = CharField(choices=TYPE_CHOICES, default=TYPE_DEPOSIT, max_length=1)

    @property
    def wagering_required(self):
        return self.money * self.wagering

    @property
    def can_convert(self):
        return self.to_real.is_zero()

    @property
    def to_real(self):
        '''
        value need to spin to convert to real money
        wagering required - spend money from ALL wallets, If spend money is greater than wagering result will be 0
        :return:
        '''
        from spin.controller import WalletController
        wallet = WalletController(self.wallet)
        money = self.wagering_required - wallet.get_spend_money(self.created, add_real_wallet=True)
        # only negatives values was taken from ALL wallets, so in current wallet value could be lower than 0
        return money if money > 0 else Decimal(0)


# do not optimize import spin.signals
import spin.signals

_ = spin.signals
