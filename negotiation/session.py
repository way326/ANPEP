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
from negotiation.negotiators import SmartAspirationNegotiator
class NegotiationSession:
    def __init__(self, items, num_sellers):
        self.items = items
        self.num_sellers = num_sellers
        # 初始化价格和数量区间
        self.price_ranges = [[(1, 20)] * len(items) for _ in range(num_sellers)]
        self.quantity_ranges = [[(1, 10)] * len(items) for _ in range(num_sellers)]
        self.issues = [self.create_issues_with_ranges(i) for i in range(num_sellers)]
        self.favors = [None] * num_sellers

    # 创建议题
    def create_issues_with_ranges(self, seller_index):
        issues = []
        for i, item in enumerate(self.items):
            price_range = self.price_ranges[seller_index][i]
            quantity_range = self.quantity_ranges[seller_index][i]
            issues.append(make_issue(name=f"{item}_price_{seller_index}", values=(price_range[0], price_range[1])))
            issues.append(make_issue(name=f"{item}_quantity_{seller_index}", values=(quantity_range[0], quantity_range[1])))
        return issues


    # 创建卖家效用函数
    def create_seller_utility(self, session, seller_index, favor):
        values = {
            f"{item}_price_{seller_index}": AffineFun(1, bias=-5.0) for item in self.items
        }
        values.update({
            f"{item}_quantity_{seller_index}": LinearFun(1) for item in self.items
        })
        return NonLinearAggregationUtilityFunction(
            values=values,
            f=lambda x: x[0] * x[1] * favor[0] + x[2] * x[3] * favor[1] + x[4] * x[5] * favor[2],
            outcome_space=session.outcome_space
        )

    # 创建买家效用函数
    def create_buyer_utility(self, session, seller_index):
        values = {
            f"{item}_price_{seller_index}": AffineFun(-1, bias=20.0) for item in self.items
        }
        values.update({
            f"{item}_quantity_{seller_index}": LinearFun(1) for item in self.items
        })
        return NonLinearAggregationUtilityFunction(
            values=values,
            f=lambda x: sum(x[i] * x[i + 1] for i in range(0, len(x), 2)),
            outcome_space=session.outcome_space
        )
    # 设置卖家favor
    def set_seller_favor(self, seller_index, favor):
        if seller_index < 0 or seller_index >= self.num_sellers:
            raise IndexError("Seller index out of range.")
        self.favors[seller_index] = favor

    # 设置价格和数量区间
    def set_price_and_quantity_ranges(self, seller_index, price_ranges, quantity_ranges):
        if seller_index < 0 or seller_index >= self.num_sellers:
            raise IndexError("Seller index out of range.")
        if len(price_ranges) != len(self.items) or len(quantity_ranges) != len(self.items):
            raise ValueError("Price ranges and quantity ranges must match the number of items.")
        self.price_ranges[seller_index] = price_ranges
        self.quantity_ranges[seller_index] = quantity_ranges
        self.issues[seller_index] = self.create_issues_with_ranges(seller_index)  # 更新卖家的议题

    # 运行谈判
    def run_negotiation(self, shared_string, results, index, thr_mutex):
        session = SAOMechanism(
            issues=self.issues[index],
            n_steps=30,
            step_time_limit=200,  # 每回合最大时间（毫秒）
            end_on_no_response=False  # 如果无响应则不结束
        )

        # 如果 favor 未设置，随机生成
        if self.favors[index] is None:
            a = random.uniform(0, 1)
            b = random.uniform(0, 1 - a)
            c = 1 - a - b
            self.favors[index] = [a, b, c]  # 更新 favor

        favor = self.favors[index]

        # 创建买家和卖家效用函数
        seller_utility = self.create_seller_utility(session, index, favor)
        buyer_utility = self.create_buyer_utility(session, index)

        # 添加卖家谈判者
        if index == 0:
            session.add(TimeBasedConcedingNegotiator(name=f"seller_{index}"), ufun=seller_utility)
        elif index == 1:
            session.add(LinearTBNegotiator(name=f"seller_{index}"), ufun=seller_utility)
        elif index == 2:
            session.add(FirstOfferOrientedTBNegotiator(name=f"seller_{index}"), ufun=seller_utility)

        # 添加买家谈判者
        buyer = SmartAspirationNegotiator(name="buyer", ufun=buyer_utility)
        buyer.set_parameter(shared_string, results, index, thr_mutex)

        # 配置助手谈判者
        helper = TimeBasedConcedingNegotiator(name="helper", ufun=buyer_utility)
        buyer.set_helper(helper)
        session.add(buyer)

        # 运行谈判
        result = session.run()

        # 输出结果
        print(f"谈判记录 (卖家 {index}):")
        print(session.extended_trace)
        session.plot()
        plt.show()
        return result