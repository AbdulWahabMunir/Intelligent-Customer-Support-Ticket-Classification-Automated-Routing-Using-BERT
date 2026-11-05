"""Create an agent-authored diagnostic set, explicitly pending human review."""

import json

from src.data.inspect import ROOT

# Authored independently of the held-out dataset. Do not alter after seeing scores.
EXAMPLES = {
    "cancel_order": ("Please cancel my order", "I no longer want my purchase; can you cancel it?"),
    "change_order": ("I need to change the items in my order", "Can you add another item to the order I already placed?"),
    "change_shipping_address": ("Change the shipping address for my order", "My order has the wrong destination; please update the delivery address"),
    "check_cancellation_fee": ("Is there a fee for cancelling my order?", "How much will you charge me if I cancel my purchase?"),
    "check_invoice": ("I think the total on my invoice is incorrect", "Could you check whether the charges on my bill are right?"),
    "check_payment_methods": ("What payment methods do you accept?", "Can I pay for my order with a credit card?"),
    "check_refund_policy": ("What is your refund policy?", "Under what conditions am I eligible for a refund?"),
    "complaint": ("I want to make a complaint about your service", "Your customer service was disappointing and I want to complain"),
    "contact_customer_service": ("How do I contact customer service?", "Where can I find the customer support phone number?"),
    "contact_human_agent": ("I want to speak to a human agent", "Please connect me to a real person rather than a chatbot"),
    "create_account": ("I want to create a new account", "How can I sign up for an account?"),
    "delete_account": ("Please delete my account permanently", "I would like to close my account and remove it"),
    "delivery_options": ("What delivery options are available?", "Do you offer express delivery or only standard delivery?"),
    "delivery_period": ("How long does delivery usually take?", "What is the usual delivery time after placing an order?"),
    "edit_account": ("I need to update my account details", "Where can I change the personal details on my profile?"),
    "get_invoice": ("Please send me a copy of my invoice", "How can I download the invoice for my purchase?"),
    "get_refund": ("I would like to request a refund", "Please return the money I paid for this purchase"),
    "newsletter_subscription": ("I want to subscribe to your newsletter", "How do I sign up to receive your email newsletter?"),
    "payment_issue": ("My payment failed when I tried to pay", "The checkout rejected my payment and I need help"),
    "place_order": ("I would like to place a new order", "How can I buy a product from your store?"),
    "recover_password": ("I forgot my password and need to reset it", "How can I recover access after losing my password?"),
    "registration_problems": ("I get an error when I try to register", "Your sign-up form will not let me create an account"),
    "review": ("Where can I leave a product review?", "I would like to post a review of the item I bought"),
    "set_up_shipping_address": ("I want to add a shipping address to my profile", "How do I save my first delivery address in my account?"),
    "switch_account": ("How do I switch to my other account?", "I want to sign out of this account and use another one"),
    "track_order": ("Where is the order I already placed?", "Can you check the current status of my package?"),
    "track_refund": ("What is the status of my existing refund?", "I already requested a refund; when will it arrive?"),
}


def typo(text):
    # One deterministic adjacent-letter swap in the first word of at least 5 letters.
    words = text.split(" ")
    for index, word in enumerate(words):
        if len(word) >= 5 and word[1].isalpha() and word[2].isalpha() and word[1] != word[2]:
            words[index] = word[0] + word[2] + word[1] + word[3:]
            return " ".join(words)
    raise ValueError("No suitable word for controlled typo")


def main():
    target = ROOT / "data/robustness/pilot.json"
    if target.exists():
        raise ValueError("Pilot already exists; keep authored examples fixed after evaluation")
    rows = []
    for intent, (anchor, paraphrase) in EXAMPLES.items():
        for condition, text in [("anchor", anchor), ("paraphrase", paraphrase),
                                ("spelling_swap", typo(anchor)), ("polite_wrapper", "Could you help me with this? " + anchor)]:
            rows.append({"id": f"{intent}:{condition}", "group": intent, "intent": intent, "condition": condition,
                         "text": text, "review_status": "draft"})
    payload = {"name": "Customer support robustness pilot v1", "source": "Agent-authored synthetic examples; not copied from dataset rows",
               "status": "Pending human linguistic/label review; diagnostic only, not an independent benchmark", "cases": rows}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Created {len(rows)} draft cases across {len(EXAMPLES)} intents: {target}")


if __name__ == "__main__":
    main()
