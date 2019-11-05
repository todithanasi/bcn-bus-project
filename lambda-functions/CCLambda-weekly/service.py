from requests.auth import HTTPBasicAuth  # or HTTPDigestAuth, or OAuth1, etc.
from requests import Session
from zeep import Client
from zeep.transports import Transport
from lxml import etree
import zeep
import json

history = zeep.plugins.HistoryPlugin()
import io
import xmltodict

def get_service(client, translation):
    service_binding = client.service._binding.name
    service_address = client.service._binding_options['address']
    return client.create_service(
        service_binding,
        service_address.replace(*translation, 1))

session = Session()
session.verify = False
session.auth = HTTPBasicAuth('upe00797', 'MbGi51')
client = Client('https://dades.tmb.cat/secure/ws-bus/LiniesBusService?wsdl',
                transport=Transport(session=session),
                plugins=[history])

service = get_service(client=client, translation=('172.28.112.81:8080', 'dades.tmb.cat'))

result = service.getBusLinesAndStops()
xmlresult = xmltodict.parse(etree.tounicode(history.last_received['envelope']))


with io.open('data2.json', 'w', encoding='utf-8') as f:
  f.write(json.dumps(xmlresult['env:Envelope']['env:Body']['ns2:getBusLinesAndStopsResponse']['return']))
