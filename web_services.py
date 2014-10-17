"""
Eventaully this is going to be in its own Package (once web services stuff is out of Tinker)
"""

#python
import datetime
import time

#modules
from suds.client import Client
from suds.transport import TransportError

#config
import config


def read(read_id, type="page"):
    client = get_client()

    identifier = {
        'id': read_id,
        'type': type
    }

    auth = config.CASCADE_LOGIN

    response = client.service.read(auth, identifier)
    return response


def get_client():
    try:
        client = Client(url=config.WSDL_URL, location=config.SOAP_URL)
        return client
    except TransportError:
        pass

