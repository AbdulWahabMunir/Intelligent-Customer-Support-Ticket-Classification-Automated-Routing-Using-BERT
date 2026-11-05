"""Classify a ticket and apply the configured routing policy locally."""

import argparse
import json

from src.inference import TicketClassifier
from src.routing import TicketService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text")
    parser.add_argument("--model", choices=["distilbert", "logistic_regression"], default="distilbert")
    args = parser.parse_args()
    try:
        service = TicketService(TicketClassifier(args.model))
        result = service.classify_and_route(args.text)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
