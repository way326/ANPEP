from negotiation.session import NegotiationSession

def thread1(shared_string, results, index, thr_mutex):
    items = ["item1", "item2", "item3"]
    negotiation_session = NegotiationSession(items, num_sellers=3)
    negotiation_session.set_price_and_quantity_ranges(index, [(5, 15)] * 3, [(2, 8)] * 3)
    negotiation_session.set_seller_favor(index, [0.4, 0.3, 0.3])
    result = negotiation_session.run_negotiation(shared_string, results, index, thr_mutex)
    results[index] = result
