import argparse
import datetime
import json
import sys
import requests

# hardcoded passenger and currency settings.
passenger_info = {"title": "Mr", "firstName": "A", "documentID": "0", "birthday": "2016-05-20", "email": "a@a.com",
                  "lastName": "B"}
currency = "EUR"


def create_arg_parser():
    """
    Creates a parser and defines the arguments along with it, help messages, types etc.
    Returns the parser object.
    """
    parser = argparse.ArgumentParser()

    parser.add_argument("--date", dest="dateFrom", help="Enter date of departure as YYYY-MM-DD.", required=True)
    parser.add_argument("--from", dest="flyFrom", help="Departure airport. It is recommended to use the IATA codes,"
                                                       " however city names usually work as well.", required=True)
    parser.add_argument("--to", help="Destination airport. It is recommended to use the IATA codes, however city"
                                     " names usually work as well.", required=True)

    return_or_one_way = parser.add_mutually_exclusive_group()
    return_or_one_way.add_argument("--one-way", dest="typeFlight", help="(default) Use for one-way only flights",
                                   const="oneway", action="store_const")
    return_or_one_way.add_argument("--return", dest="daysInDestination", help="For a return flight enter the number"
                                                                              " of days in destination.", type=int)

    cheap_or_short = parser.add_mutually_exclusive_group()
    cheap_or_short.add_argument("--cheapest", dest="sort", help="(default) Books the cheapest flight", const="price",
                                default="price", action="store_const")
    cheap_or_short.add_argument("--shortest", dest="sort", help="Books the shortest flight.",  const="duration",
                                action="store_const")
    return parser


def format_payload_for_get_request(args):
    """
    Formats the arguments for the API. See http://docs.skypickerpublicapi.apiary.io/#reference/flights.
    Returns payload ready to be sent to server.
    """
    payload = vars(args)  # make dictionary out of the Namespace from arg parser

    # strip daysInDestination if not need or switch to return flight
    if args.daysInDestination is None:
        payload["typeFlight"] = "oneway"
        payload.pop("daysInDestination", None)
    else:
        payload["typeFlight"] = "return"

    # switch to different date format used by API and check input
    try:
        payload["dateFrom"] = datetime.datetime.strptime(payload["dateFrom"], '%Y-%m-%d').strftime(
            '%d/%m/%Y')
    except ValueError:
        print("Incorrect date format. Enter date of departure as YYYY-MM-DD.")
        sys.exit(2)

    return payload


def request_server_response(request, url, params=None, json_payload=None):
    """Sends a request to server and catches exceptions caused by no response, typically no internet connection."""
    try:
        return request(url, params=params, json=json_payload)
    except requests.exceptions.ConnectionError as err:
        print("No response from server. Check your internet connection.")
        print(err)
        sys.exit(1)


def parse_json(json_response):
    """Parses json response and catches exception caused by invalid response such as 502 or 503. """
    try:
        return json_response.json()
    except json.decoder.JSONDecodeError:
        print("Invalid response from server. Server is probably offline.\n"
              "Server responded with "+str(json_response))
        sys.exit(1)


def find_flight(payload):
    """
    Looks for a flight according to the payload parameter which has to comply
    with http://docs.skypickerpublicapi.apiary.io/#reference/flights
    It then selects the shortest or cheapest flight depending on payload[typeFlight].
    Returns the booking token of said flight
    """

    flight_search = request_server_response(requests.get, "https://api.skypicker.com/flights?", params=payload)

    flight_search_results = parse_json(flight_search)

    # if no results returned tell the user to fix the parameters
    if flight_search_results["_results"] == 0:
        print("No flights found. Check spelling of parameters. Use -h or --help for more information.")
        sys.exit(1)

    # book flight. Note that the results are already sorted by the desired property.
    # return booking token
    return flight_search_results["data"][0]["booking_token"]


def book_flight(token, pass_info, currency_name):
    """
    Books a flight based on booking token, currency and passenger info.
    Returns the PNR number of a successful booking
    """
    # request booking from server
    booking_payload = {'currency': currency_name, 'booking_token': token,
                       "passengers": pass_info,
                       }
    booking = request_server_response(requests.post, "http://37.139.6.125:8080/booking", json_payload=booking_payload)

    try:
        booking_confirmation = booking.json()
    except json.decoder.JSONDecodeError:
        print("Invalid response from booking server.\n"
              "Server responded with " + str(booking))
        sys.exit(1)

    if booking_confirmation["status"] == "confirmed":
        return booking.json()["pnr"]
    else:
        print("Booking not successful\n"+str(booking_confirmation))
        sys.exit(1)


def main():
    """
    Books a flight based on command line arguments.
    First defines arguments and flags for program.
    Then searches for a flight based on arguments.
    Finally books the best selected flight and returns the PNR number of said flight.
    """
    # parse arguments
    args = create_arg_parser().parse_args()

    # search for a flight
    search_payload = format_payload_for_get_request(args)
    booking_token = find_flight(search_payload)

    # book the selected flight
    pnr_number = book_flight(booking_token, passenger_info, currency)

    # print PNR number
    print(pnr_number)


if __name__ == "__main__":
    main()
