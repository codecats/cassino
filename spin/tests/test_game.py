from django.test import TestCase

from spin.controller import WalletController, GameWorkflowController, GameMoneyError, DepletedError, NoMoneyError
from spin.models import *
from spin.tests import CleanMixin


class GameLostController(GameWorkflowController):
    @property
    def is_won(self):
        return False


class GameWonController(GameWorkflowController):
    @property
    def is_won(self):
        return True


class GameWonUnconvert(GameWonController):
    def convert_bonuses(self): pass


class GameTest(CleanMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user('lisa')

    def test_after_login_user_lost_all_money(self):
        self.user.last_login = None
        ctl = GameLostController(self.user)
        ctl.login_bonus()
        self.assertEqual(2, Wallet.objects.filter(is_depleted=False).count())  # BNS + real wallet
        real = ctl.real_wallet
        bns = ctl.get_active_wallet()
        self.assertNotEqual(bns.wallet.pk, real.wallet.pk)
        self.assertFalse(bns.wallet.is_real)
        with self.assertRaises(GameMoneyError):
            while True:
                ctl.spin(bns)

        bns = WalletController(Wallet.objects.get(is_real=False))
        self.assertTrue(bns.get_play_money().is_zero())
        self.assertTrue(real.get_play_money().is_zero())

        active = ctl.get_active_wallet()
        self.assertEqual(active, None)
        with self.assertRaises(NoMoneyError):
            ctl.spin(ctl.real_wallet)
        with self.assertRaises(DepletedError):
            ctl.spin(bns)

    def test_after_login_user_won_and_can_convert_bonus(self):
        self.user.last_login = None
        ctl = GameWonUnconvert(self.user)
        ctl.login_bonus()
        self.assertEqual(2, Wallet.objects.filter(is_depleted=False).count())
        real = ctl.real_wallet
        bns = ctl.get_active_wallet()
        self.assertNotEqual(bns.wallet.pk, real.wallet.pk)
        self.assertFalse(bns.wallet.is_real)

        wagering = bns.wallet.bonus.wagering_required
        spend = bns.get_spend_money()
        self.assertFalse(bns.can_convert())
        while wagering > spend:
            ctl.spin(bns)
            spend = bns.get_spend_money()
        self.assertTrue(bns.can_convert())
        # clean
        bns.wallet.is_depleted = True
        bns.wallet.save()

    def test_user_has_login_and_deposit_bonuses_then_he_converts(self):
        self.user.last_login = None
        ctl = GameWonController(self.user)
        ctl.login_bonus()
        login_bns = WalletController(Wallet.objects.get(is_depleted=False, is_real=False))
        ctl.deposit_bonus(Decimal(99999))
        deposit_bns = next(
            filter(lambda x: x.wallet.is_real == False and x.wallet.pk != login_bns.wallet.pk, ctl.wallets))
        self.assertFalse(login_bns.can_convert())
        self.assertFalse(deposit_bns.can_convert())

        for wallet_ctl in (login_bns, deposit_bns):
            MoneyChange.objects.all().delete()
            amount = wallet_ctl.wallet.bonus.wagering_required
            ctl.real_wallet.change(amount)  # fist add money then spend all
            self.assertFalse(wallet_ctl.can_convert())
            ctl.real_wallet.change(amount * -1)
            self.assertTrue(wallet_ctl.can_convert())
            self.assertTrue(ctl.real_wallet.get_play_money().is_zero())
            ctl.convert_bonus(wallet_ctl)
            play_money = ctl.real_wallet.get_play_money()
            self.assertAlmostEqual(play_money, wallet_ctl.wallet.bonus.money)

    def test_user_has_login_and_deposit_bonuses_then_he_lost_all(self):
        self.user.last_login = None
        ctl = GameLostController(self.user)
        ctl.login_bonus()
        login_bns = WalletController(Wallet.objects.get(is_depleted=False, is_real=False))
        ctl.deposit_bonus(Decimal(99999))
        deposit_bns = next(
            filter(lambda x: x.wallet.is_real == False and x.wallet.pk != login_bns.wallet.pk, ctl.wallets))
        wallet = ctl.get_active_wallet()
        while wallet is not None:
            ctl.spin(wallet)
            wallet = ctl.get_active_wallet()
        self.assertAlmostEqual(0, ctl.real_wallet.get_play_money())
        self.assertAlmostEqual(0, login_bns.get_play_money())
        self.assertAlmostEqual(0, deposit_bns.get_play_money())

    def test_deposit(self):
        MoneyChange.objects.all().delete()
        ctl = GameWonController(self.user)
        self.assertEqual(ctl.get_active_wallet(), None)
        ctl.deposit(10)
        self.assertNotEqual(ctl.get_active_wallet(), None)
        wctl = ctl.get_active_wallet()
        Wallet.objects.filter().delete()
        with self.assertRaises(RuntimeError):
            ctl.deposit(10)
        wctl.wallet.save()
