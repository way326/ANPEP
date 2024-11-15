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

def send_agent_message(message):
    chat_area.config(state='normal')
    chat_area.insert(tk.END, f"Agent: {message}\n")
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



def print_i(string, results, index, thr_mutex):
    while(1):
        time.sleep(0.5)
        if(thr_mutex[index] == True):
            results[index] = string
            thr_mutex[index] = False
        else:
            pass

def input_i(string, results, index, thr_mutex):
    while(1):
        time.sleep(0.5)
        if(thr_mutex[index] == False):
            time.sleep(0.5)
        else:
            thr_mutex[index] = False
            return string[index]

class SmartAspirationNegotiator(SAONegotiator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = None
        self.chat_area = chat_area

    def set_helper(self,SAONegotiator):
        self.helper = SAONegotiator

    def send_agent_message(self,message):
        chat_area.config(state='normal')
        chat_area.insert(tk.END, f"Agent: {message}\n")
        chat_area.config(state='disabled')

    def set_parameter(self,shared_string, results, index, thr_mutex):
        self.shared_string = shared_string
        self.results = results
        self.index = index
        self.thr_mutex = thr_mutex

    def respond(self, state, source: str):
        offer = state.current_offer

        if offer is None:
            return ResponseType.REJECT_OFFER

        # 接收用户输入来决定是否接受报价
        #print(f"——————————当前轮数为{state.step}———————————")
        if(self.index == 0):
            self.send_agent_message(f"——————————当前轮数为{state.step}———————————")

        #print(f"上一轮出价 {state.current_proposer}")
        #print(f"收到报价 {offer}")
        self.send_agent_message(f"收到对手报价 {offer}。接受此报价吗？(y/n): ")
        user_input = input_i(self.shared_string, self.results, self.index, self.thr_mutex)
        #user_input = 'n'
        if user_input.lower() == 'y':
            return ResponseType.ACCEPT_OFFER
        else:
            # 当用户拒绝时，返回一个新的报价
            self.helper.respond(state, "seller_{1}")
            suggestion =self.helper.propose(state)
            #print(f"建议报价为{suggestion}")
            self.send_agent_message(f"建议报价为{suggestion}")

            #print(my_offer)
            return ResponseType.REJECT_OFFER

    def user_propose(self):
        # 由用户输入新的报价
        #user_offer = input("请输入您的报价（格式为逗号分隔的值，例如：1,2,3）: ")
        if(self.index == 0):
            self.send_agent_message(f"请输入您的报价")
        user_offer = input_i(self.shared_string, self.results, self.index, self.thr_mutex)

        #user_offer = "10, 8, 12, 10, 11, 7"
        #print(f"请输入您的报价{user_offer}")
        return tuple(map(float, user_offer.split(',')))

    def propose(self, state):
        # 使用父类方法提议报价
        my_offer = self.user_propose()
        #proposal = super().propose(state)
        self.send_agent_message(f"提议报价: {my_offer}")
        return my_offer
class NegotiationSession:
    def __init__(self, items, num_sellers, shared_string, results, index, thr_mutex):
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

    def run_negotiation(self,shared_string, results, index, thr_mutex):
        session = SAOMechanism(issues=self.issues[index], n_steps=30, step_time_limit=200,  # 设定每回合的最大时间为5秒
            end_on_no_response=False) # 如果没有响应，结束谈判)  #仅使用当前卖家的问题

        # 如果favor为None，随机生成favor
        if self.favors[index] is None:
            a = random.uniform(0, 1)
            b = random.uniform(0, 1 - a)
            c = 1 - a - b
            self.favors[index] = [a, b, c]  # 更新favor

        favor = self.favors[index]

        buyer_utility = self.create_buyer_utility(session, index)
        seller_utility = self.create_seller_utility(session, index, "default", favor)

        #session.add(SmartAspirationNegotiator(name="buyer"), ufun=buyer_utility)
        if index == 0:
            session.add(TimeBasedConcedingNegotiator(name=f"seller_{index}"), ufun=seller_utility)
        elif index == 1:
            session.add(LinearTBNegotiator(name=f"seller_{index}"), ufun=seller_utility)
        elif index == 2:
            session.add(FirstOfferOrientedTBNegotiator(name=f"seller_{index}"), ufun=seller_utility)
        #session.add(TimeBasedConcedingNegotiator(name=f"seller_{seller_index}"), ufun=seller_utility)
        #session.add(LinearTBNegotiator(name=f"seller_{seller_index}"), ufun=seller_utility)
        #session.add(SmartAspirationNegotiator(name="buyer"), ufun=buyer_utility)
        Smart = SmartAspirationNegotiator(name="buyer", ufun=buyer_utility)
        Smart.set_parameter(shared_string, results, index, thr_mutex)
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


def thread1(shared_string, results, index, thr_mutex):
    # 实例化并运行谈判
    items = ["item1", "item2", "item3"]
    num_sellers = 3
    negotiation_session = NegotiationSession(items, num_sellers, shared_string, results, index, thr_mutex)

    # 设置卖家的价格与数量区间
    negotiation_session.set_price_and_quantity_ranges(0, [(5, 15), (10, 20), (8, 18)], [(2, 8), (1, 10), (3, 7)])
    negotiation_session.set_price_and_quantity_ranges(1, [(5, 15), (10, 20), (8, 18)], [(2, 8), (1, 10), (3, 7)])
    negotiation_session.set_price_and_quantity_ranges(2, [(5, 15), (10, 20), (8, 18)], [(2, 8), (1, 10), (3, 7)])

    # 设置卖家的favor
    negotiation_session.set_seller_favor(0, [0.4, 0.3, 0.3])
    negotiation_session.set_seller_favor(1, [0.2, 0.5, 0.3])
    negotiation_session.set_seller_favor(2, [0.1, 0.4, 0.5])

    results = negotiation_session.run_negotiation(shared_string, results, index, thr_mutex)
    f = lambda x: sum(x[i] * x[i + 1] for i in range(0, len(x), 2))
    fit = f(results.agreement)
    print(f"Negotiation result with seller : {results.agreement}"+f"最终效益为{fit}")


def append_id(shared_string, results, index, thr_mutex):
    while(1):
        time.sleep(0.5)
        if(thr_mutex[index] == True):
            modified_string = f"{shared_string[0]} from thread {index}"
            results[index] = modified_string
            thr_mutex[index] = False
        else:
            pass

def input_thread(shared_string, results ,thr_mutex):
    while (1):
        time.sleep(0.5)
        if (thr_mutex[0] == False | thr_mutex[1] == False | thr_mutex[2] == False):
            send_agent_message("对第0个线程：")
            with input_condition:
                input_condition.wait()
            shared_string[0] = entry.get()
            time.sleep(0.5)
            entry.delete(0, tk.END)
            send_agent_message("对第1个线程：")
            with input_condition:
                input_condition.wait()
            shared_string[1] = entry.get()
            time.sleep(0.5)
            send_agent_message("对第2个线程：")
            with input_condition:
                input_condition.wait()
            shared_string[2] = entry.get()
            time.sleep(0.5)
            send_agent_message(f"buffer内字符串：{shared_string}")

            thr_mutex[0] = True
            thr_mutex[1] = True
            thr_mutex[2] = True
            # 输出结果
            if (thr_mutex[0] == True | thr_mutex[1] == True | thr_mutex[2] == True):
                time.sleep(0.5)

            if (results[0] != None):
                send_agent_message("0:", results[0])
            if (results[1] != None):
                send_agent_message("1:", results[1])
            if (results[2] != None):
                send_agent_message("2:", results[2])

# 主函数
def main():

    results = [None] * 3
    threads = []
    shared_string = [None] * 3

    thr_mutex = [False] * 3

    # 创建并启动三个线程
    for i in range(3):
        thread = threading.Thread(target=thread1, args=(shared_string, results, i, thr_mutex))
        threads.append(thread)
        thread.start()

    threading.Thread(target=input_thread, args=(shared_string, results, thr_mutex) ,daemon=True).start()

    root.mainloop()



if __name__ == "__main__":
    main()


