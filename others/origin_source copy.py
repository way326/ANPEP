from flask import Flask, request, jsonify, render_template
import threading
import time
from matplotlib import pyplot as plt
from concurrent.futures import ThreadPoolExecutor
from negmas import (
    make_issue,
    SAOMechanism,
    SAONegotiator,
    TimeBasedConcedingNegotiator,
    NonLinearAggregationUtilityFunction, LinearTBNegotiator
)
from negmas.preferences.value_fun import AffineFun, LinearFun

app = Flask(__name__)

# Global shared variables for threads
shared_string = [None] * 3
results = [None] * 3
thr_mutex = [False] * 3
negotiation_threads = []
negotiation_results = {}
round_info = [{"round": 0, "suggestion": None} for _ in range(3)]  # Store round and suggestion info

# Negotiation classes
class SmartAspirationNegotiator(SAONegotiator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = None

    def set_helper(self, SAONegotiator):
        self.helper = SAONegotiator

    def set_parameter(self, shared_string, results, index, thr_mutex):
        self.shared_string = shared_string
        self.results = results
        self.index = index
        self.thr_mutex = thr_mutex

    def respond(self, state, source: str):
        offer = state.current_offer
        if offer is None:
            return ResponseType.REJECT_OFFER

        # Update round info for front-end
        round_info[self.index]["round"] = state.step
        round_info[self.index]["suggestion"] = self.helper.propose(state)  # Get suggestion

        while not self.thr_mutex[self.index]:
            time.sleep(0.1)  # Wait for user input

        user_input = self.shared_string[self.index]
        self.thr_mutex[self.index] = False
        if user_input.lower() == 'y':  # Accept
            return ResponseType.ACCEPT_OFFER
        else:
            return ResponseType.REJECT_OFFER

    def user_propose(self):
        while not self.thr_mutex[self.index]:
            time.sleep(0.1)
        user_offer = self.shared_string[self.index]
        self.thr_mutex[self.index] = False
        return tuple(map(float, user_offer.split(',')))

    def propose(self, state):
        my_offer = self.user_propose()
        return my_offer

class NegotiationSession:
    def __init__(self, items, num_sellers, shared_string, results, index, thr_mutex):
        self.items = items
        self.num_sellers = num_sellers
        self.price_ranges = [[(1, 20)] * len(items) for _ in range(num_sellers)]
        self.quantity_ranges = [[(1, 10)] * len(items) for _ in range(num_sellers)]
        self.issues = [self.create_issues_with_ranges(i) for i in range(num_sellers)]

    def create_issues_with_ranges(self, seller_index):
        issues = []
        for i, item in enumerate(self.items):
            price_range = self.price_ranges[seller_index][i]
            quantity_range = self.quantity_ranges[seller_index][i]
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

    def create_seller_utility(self, session, seller_index):
        values = {
            f"{item}_price_{seller_index}": AffineFun(1, bias=-5.0) for item in self.items
        }
        values.update({
            f"{item}_quantity_{seller_index}": LinearFun(1) for item in self.items
        })
        return NonLinearAggregationUtilityFunction(
            values=values,
            f=lambda x: x[0] * x[1] + x[2] * x[3] + x[4] * x[5],
            outcome_space=session.outcome_space
        )

    def run_negotiation(self, shared_string, results, index, thr_mutex):
        session = SAOMechanism(issues=self.issues[index], n_steps=30)
        buyer_utility = self.create_buyer_utility(session, index)
        seller_utility = self.create_seller_utility(session, index)
        Smart = SmartAspirationNegotiator(name="buyer", ufun=buyer_utility)
        Smart.set_parameter(shared_string, results, index, thr_mutex)
        helper = TimeBasedConcedingNegotiator(name="helper", ufun=buyer_utility)
        Smart.set_helper(helper)
        session.add(Smart)
        session.add(TimeBasedConcedingNegotiator(name=f"seller_{index}", ufun=seller_utility))
        result = session.run()
        negotiation_results[index] = {
            "agreement": result.agreement,
            "trace": session.extended_trace
        }
        return result

def thread1(shared_string, results, index, thr_mutex):
    items = ["item1", "item2", "item3"]
    session = NegotiationSession(items, 3, shared_string, results, index, thr_mutex)
    session.run_negotiation(shared_string, results, index, thr_mutex)

# Flask Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_negotiation', methods=['POST'])
def start_negotiation():
    for i in range(3):
        thread = threading.Thread(target=thread1, args=(shared_string, results, i, thr_mutex))
        negotiation_threads.append(thread)
        thread.start()
    return jsonify({"status": "Negotiations started."})

@app.route('/send_input', methods=['POST'])
def send_input():
    data = request.json
    index = data['index']
    user_input = data['input']
    shared_string[index] = user_input
    thr_mutex[index] = True
    return jsonify({"status": "Input received."})

@app.route('/get_round_info', methods=['GET'])
def get_round_info():
    return jsonify(round_info)

@app.route('/get_results', methods=['GET'])
def get_results():
    return jsonify(negotiation_results)

if __name__ == "__main__":
    app.run(debug=True)
