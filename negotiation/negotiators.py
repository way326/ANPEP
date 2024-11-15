import random
import time
import threading
from matplotlib import pyplot as plt
from negmas import (
    make_issue,
    SAOMechanism,
    SAONegotiator,
    TimeBasedConcedingNegotiator,
    NonLinearAggregationUtilityFunction, GBNegotiator, LinearTBNegotiator, FirstOfferOrientedTBNegotiator,
    BoulwareTBNegotiator, ResponseType,
)
from negmas.preferences.value_fun import AffineFun, LinearFun
from concurrent.futures import ThreadPoolExecutor


class SmartAspirationNegotiator(SAONegotiator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = None
        self.shared_string = None
        self.results = None
        self.index = None
        self.thr_mutex = None

    def set_helper(self, helper_negotiator):
        """
        设置辅助 Negotiator。
        """
        self.helper = helper_negotiator

    def set_parameter(self, shared_string, results, index, thr_mutex):
        """
        设置用于线程交互的参数。
        """
        self.shared_string = shared_string
        self.results = results
        self.index = index
        self.thr_mutex = thr_mutex

    def respond(self, state, source: str):
        """
        响应对方的报价。
        """
        offer = state.current_offer

        if offer is None:
            return ResponseType.REJECT_OFFER

        # 打印当前轮数
        if self.index == 0:
            print(f"——————————当前轮数为 {state.step} ——————————")
        
        print(f"收到对手报价 {offer}。接受此报价吗？(y/n): ")
        user_input = self._get_user_input()

        if user_input.lower() == 'y':
            return ResponseType.ACCEPT_OFFER
        else:
            # 如果拒绝，使用助手生成建议报价
            if self.helper:
                self.helper.respond(state, "seller_{1}")
                suggestion = self.helper.propose(state)
                print(f"建议报价为: {suggestion}")
            return ResponseType.REJECT_OFFER

    def user_propose(self):
        """
        获取用户输入的报价。
        """
        if self.index == 0:
            print(f"请输入您的报价: ")

        user_offer = self._get_user_input()
        return tuple(map(float, user_offer.split(',')))

    def propose(self, state):
        """
        提议新的报价。
        """
        my_offer = self.user_propose()
        print(f"提议报价: {my_offer}")
        return my_offer

    def _get_user_input(self):
        """
        获取用户输入，确保线程安全。
        """
        while True:
            if self.thr_mutex[self.index]:
                self.thr_mutex[self.index] = False
                return self.shared_string[self.index]
