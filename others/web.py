from flask import Flask, request, jsonify
import random
import threading

app = Flask(__name__)

# Mockup storage for negotiation results
results_storage = {}

@app.route('/api/start_negotiation', methods=['POST'])
def start_negotiation():
    data = request.get_json()
    num_sellers = data.get("num_sellers", 3)
    items = data.get("items", ["item1", "item2", "item3"])
    
    # Initialize results
    results_storage["results"] = ["Pending"] * num_sellers

    # Simulate negotiation process (call your negotiation logic here)
    thread = threading.Thread(target=run_negotiation, args=(items, num_sellers))
    thread.start()

    return jsonify({"message": "Negotiation started", "status": "running"}), 202

def run_negotiation(items, num_sellers):
    # Simulate results
    for i in range(num_sellers):
        results_storage["results"][i] = f"Result for seller {i + 1}"

@app.route('/api/results', methods=['GET'])
def get_results():
    return jsonify({"results": results_storage.get("results", [])})

if __name__ == '__main__':
    app.run(debug=True)
