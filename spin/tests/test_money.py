from django.test import TestCase

from spin.controller import WalletController
from spin.models import *
from spin.tests import CleanMixin


class WalletTestCase(CleanMixin, TestCase):
    def test_change_real_wallet(self):
        user = User.objects.create_user('alex')
        wallet = Wallet.objects.create(owner=user, is_real=True)
        w1 = WalletController(wallet)
        w1.change(10)
        self.assertAlmostEqual(w1.get_money(), 10.)

        w1.change(-10)
        self.assertAlmostEqual(w1.get_money(), 0)

        for i in range(100):
            w1.change(Decimal(12.1131))
        self.assertAlmostEqual(w1.get_money(), Decimal(1211.00))
        w1.change(Decimal(-1211))
        self.assertAlmostEqual(w1.get_money(), 0.)
        self._clean_data()

    def test_change_bonus_wallet(self):
        user = User.objects.create_user('alex')
        wallet1 = Wallet.objects.create(owner=user, is_real=True)
        wallet2 = Wallet.objects.create(owner=user, is_real=False)
        w2 = WalletController(wallet2)
        w2.set_bonus(Decimal(2))

        self.assertAlmostEqual(w2.get_money(), Decimal(0))
        self.assertAlmostEqual(w2.get_play_money(), Decimal(2))
        self.assertAlmostEqual(w2.get_bonus_money(), Decimal(2))

        w2.change(Decimal(10))

        self.assertAlmostEqual(w2.get_money(), Decimal(10))
        self.assertAlmostEqual(w2.get_play_money(), Decimal(12))
        self.assertAlmostEqual(w2.get_bonus_money(), Decimal(2))

        WalletController(wallet1).change(100)

        w2.change(Decimal(-100))

        self.assertAlmostEqual(w2.get_money(), Decimal(-90))
        self.assertAlmostEqual(w2.get_play_money(), Decimal(-88))
        self.assertAlmostEqual(w2.get_bonus_money(), Decimal(2))
        self._clean_data()
