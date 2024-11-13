import random
import threading
from time import sleep

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

import tkinter as tk
from tkinter import scrolledtext

input_condition = threading.Condition()

def send_you_message():
    with input_condition:
        input_condition.notify()
    message = entry.get()
    if message:
        chat_area.config(state='normal')
        chat_area.insert(tk.END, f"You: {message}\n")
        #        entry.delete(0, tk.END)
        chat_area.config(state='disabled')

root = tk.Tk()
root.title("negotiation")
root.geometry("600x350")

chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, state='disabled', height=20, width=80)
chat_area.pack(pady=10)

entry = tk.Entry(root, width=70)
entry.pack(pady=10, padx=10, side=tk.LEFT)

send_button = tk.Button(root, text="发送", command=send_you_message)
send_button.pack(pady=10, padx=10, side=tk.LEFT)


class SmartAspirationNegotiator( SAONegotiator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = None
        self.chat_area = chat_area

    def set_helper(self,SAONegotiator ):
        self.helper = SAONegotiator

    def send_agent_message(self,message):
        chat_area.config(state='normal')
        chat_area.insert(tk.END, f"Agent: {message}\n")
        chat_area.config(state='disabled')


    def respond(self, state, source: str):
        offer = state.current_offer

        if offer is None:
            return ResponseType.REJECT_OFFER

        # 接收用户输入来决定是否接受报价
        self.send_agent_message(f"——————————当前轮数为{state.step}———————————")
        #print(f"上一轮出价 {state.current_proposer}")
        #print(f"收到报价 {offer}")
        self.send_agent_message(f"收到对手报价 {offer}。接受此报价吗？(y/n): ")
        with input_condition:
            input_condition.wait()
        user_input = entry.get()
        sleep(0.5)
        entry.delete(0, tk.END)
        if user_input.lower() == 'y':
            return ResponseType.ACCEPT_OFFER
        else:
            # 当用户拒绝时，返回一个新的报价
            self.helper.respond(state, "seller_{1}")
            suggestion =self.helper.propose(state)
            self.send_agent_message(f"agent:建议报价为{suggestion}")

            #print(my_offer)
            return ResponseType.REJECT_OFFER

    def user_propose(self):
        # 由用户输入新的报价
        self.send_agent_message("请输入您的报价（格式为逗号分隔的值，例如：1,2,3）: ")
        with input_condition:
            input_condition.wait()
        user_offer = entry.get()
        sleep(0.5)
        entry.delete(0, tk.END)
        #print(f"请输入您的报价{user_offer}")
        return tuple(map(float, user_offer.split(',')))

    def propose(self, state):
        # 使用父类方法提议报价
        my_offer = self.user_propose()
        #proposal = super().propose(state)
        self.send_agent_message(f"提议报价: {my_offer}")
        return my_offer



class NegotiationSession:
    def __init__(self, items, num_sellers):
        self.items = items
        self.num_sellers = num_sellers
        # 初始化价格和数量区间
        self.price_ranges = [[(1, 20)] * len(items) for _ in range(num_sellers)]
        self.quantity_ranges = [[(1, 10)] * len(items) for _ in range(num_sellers)]
        self.issues = [self.create_issues_with_ranges(i) for i in range(num_sellers)]
        self.favors = [None] * num_sellers

    def create_issues_with_ranges(self, seller_index):
        issues = []
        for i, item in enumerate(self.items):
            price_range = self.price_ranges[seller_index][i]
            quantity_range = self.quantity_ranges[seller_index][i]
            # 使用不同的键名与卖家索引相结合
            issues.append(make_issue(name=f"{item}_price_{seller_index}", values=(price_range[0], price_range[1])))
            issues.append(make_issue(name=f"{item}_quantity_{seller_index}", values=(quantity_range[0], quantity_range[1])))
        return issues

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

    def create_seller_utility(self, session, seller_index, utility_type, favor):
        values = {
            f"{item}_price_{seller_index}": AffineFun(1, bias=-5.0) for item in self.items
        }
        values.update({
            f"{item}_quantity_{seller_index}": LinearFun(1) for item in self.items
        })
        if utility_type == "no_favor":
            return NonLinearAggregationUtilityFunction(values=values,
                                                       f=lambda x: sum(x[i] * x[i + 1] for i in range(0, len(x), 2)),
                                                       outcome_space=session.outcome_space)
        elif utility_type == "no_quantity":
            return NonLinearAggregationUtilityFunction(values=values,
                                                       f=lambda x: x[0] * favor[0] + x[2] * favor[1] + x[4] * favor[2],
                                                       outcome_space=session.outcome_space)
        elif utility_type == "default":
            return NonLinearAggregationUtilityFunction(values=values,
                                                       f=lambda x: x[0] * x[1] * favor[0] + x[2] * x[3] * favor[1] + x[4] * x[5] * favor[2],
                                                       outcome_space=session.outcome_space)

    def set_seller_favor(self, seller_index, favor):
        """设置指定卖家的favor"""
        if seller_index < 0 or seller_index >= self.num_sellers:
            raise IndexError("Seller index out of range.")
        self.favors[seller_index] = favor

    def set_price_and_quantity_ranges(self, seller_index, price_ranges, quantity_ranges):
        """外部访问方法，用于设置指定卖家的所有物品的价格和数量区间"""
        if seller_index < 0 or seller_index >= self.num_sellers:
            raise IndexError("Seller index out of range.")
        if len(price_ranges) != len(self.items) or len(quantity_ranges) != len(self.items):
            raise ValueError("Price ranges and quantity ranges must match the number of items.")
        self.price_ranges[seller_index] = price_ranges
        self.quantity_ranges[seller_index] = quantity_ranges
        self.issues[seller_index] = self.create_issues_with_ranges(seller_index)  # 更新卖家的议题

    def run_negotiation(self, seller_index):
        session = SAOMechanism(issues=self.issues[seller_index], n_steps=30, step_time_limit=200,  # 设定每回合的最大时间为5秒
            end_on_no_response=False) # 如果没有响应，结束谈判)  #仅使用当前卖家的问题

        # 如果favor为None，随机生成favor
        if self.favors[seller_index] is None:
            a = random.uniform(0, 1)
            b = random.uniform(0, 1 - a)
            c = 1 - a - b
            self.favors[seller_index] = [a, b, c]  # 更新favor

        favor = self.favors[seller_index]

        buyer_utility = self.create_buyer_utility(session, seller_index)
        seller_utility = self.create_seller_utility(session, seller_index, "default", favor)

        #session.add(SmartAspirationNegotiator(name="buyer"), ufun=buyer_utility)
        if seller_index == 0:
            session.add(TimeBasedConcedingNegotiator(name=f"seller_{seller_index}"), ufun=seller_utility)
        elif seller_index == 1:
            session.add(LinearTBNegotiator(name=f"seller_{seller_index}"), ufun=seller_utility)
        elif seller_index == 2:
            session.add(FirstOfferOrientedTBNegotiator(name=f"seller_{seller_index}"), ufun=seller_utility)
        #session.add(TimeBasedConcedingNegotiator(name=f"seller_{seller_index}"), ufun=seller_utility)
        #session.add(LinearTBNegotiator(name=f"seller_{seller_index}"), ufun=seller_utility)
        #session.add(SmartAspirationNegotiator(name="buyer"), ufun=buyer_utility)
        Smart = SmartAspirationNegotiator(name="buyer", ufun=buyer_utility)
        helper = TimeBasedConcedingNegotiator(name="helper", ufun=buyer_utility)
        Smart.set_helper(helper)
        session.add(Smart)
        #session.add(TimeBasedConcedingNegotiator(name="buyer"), ufun=buyer_utility)

        result = session.run()
        print("谈判记录")
        print(session.extended_trace)
        session.plot()
        plt.show()
        return result

    def start_negotiations(self):

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(self.run_negotiation, range(self.num_sellers)))
        return results

    def start_negotiations_1(self):


        return self.run_negotiation(0)


# 实例化并运行谈判
items = ["item1", "item2", "item3"]
num_sellers = 3
negotiation_session = NegotiationSession(items, num_sellers)

# 设置卖家的价格与数量区间
negotiation_session.set_price_and_quantity_ranges(0, [(5, 15), (10, 20), (8, 18)], [(2, 8), (1, 10), (3, 7)])
negotiation_session.set_price_and_quantity_ranges(1, [(5, 15), (10, 20), (8, 18)], [(2, 8), (1, 10), (3, 7)])
negotiation_session.set_price_and_quantity_ranges(2, [(5, 15), (10, 20), (8, 18)], [(2, 8), (1, 10), (3, 7)])

# 设置卖家的favor
negotiation_session.set_seller_favor(0, [0.4, 0.3, 0.3])
negotiation_session.set_seller_favor(1, [0.2, 0.5, 0.3])
negotiation_session.set_seller_favor(2, [0.1, 0.4, 0.5])

threading.Thread(target=negotiation_session.start_negotiations_1, daemon=True).start()

root.mainloop()

#f = lambda x: sum(x[i] * x[i + 1] for i in range(0, len(x), 2))
#fit = f(results.agreement)
#(f"Negotiation result with seller : {results.agreement}"+f"最终效益为{fit}")

# 输出每个谈判结果
#for i, result in enumerate(results):
#    f = lambda x: sum(x[i] * x[i + 1] for i in range(0, len(x), 2))
#    fit = f(result.agreement)
#    print(f"Negotiation result with seller {i}: {result.agreement}"+f"最终效益为{fit}")


