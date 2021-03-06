import httplib
import urllib2
import urllib
import xml.dom.minidom as dom
import json
import datetime as dt

def get_time_range():
    end = dt.datetime.utcnow().replace(microsecond=0)
    start = end - dt.timedelta(days=1)
    
    return (start, end)

def validate_dt_value(datetime):
    """
    Verify that the given datetime will not cause problems for the Open311 API.
    For the San Francisco Open311 API, start and end dates are ISO8601 strings,
    but they are expected to be a specific subset.
    """
    if datetime.microsecond != 0:
        raise ValueError('Microseconds on datetime must be 0: %s' % datetime)
    
    if datetime.tzinfo is not None:
        raise ValueError('Tzinfo on datetime must be None: %s' % datetime)

def get_requests_from_SF(start,end):
    """
    Retrieve the requests from the San Francisco 311 API within the time range
    specified by the dates start and end.
    
    Returns a stream containing the content from the API call.
    """
    
    validate_dt_value(start)
    validate_dt_value(end)
    
    url = r'https://open311.sfgov.org/dev/v2/requests.xml'
    query_data = {
        'start_date' : start.isoformat() + 'Z',
        'end_date' : end.isoformat() + 'Z',
        'jurisdiction_id' : 'sfgov.org'
    }
    query_str = urllib.urlencode(query_data)
    
    requests_stream = urllib2.urlopen(url + '?' + query_str)
    return requests_stream

def parse_requests_doc(stream):
    """
    Converts the given file-like object, which presumably contains a service
    requests document, into a list of request dictionaries.
    """
    import xml.dom
    
    requests = []
    requests_root = dom.parse(stream).documentElement
    
    for request_node in requests_root.childNodes:
        if request_node.nodeType != xml.dom.Node.ELEMENT_NODE:
            continue
        
        request = {}
        
        if request_node.tagName != 'request':
            raise Exception('Unexpected node: %s' % requests_root.toprettyxml())
        
        for request_attr in request_node.childNodes:
            if request_attr.childNodes:
                key = request_attr.tagName
                value = request_attr.childNodes[0].data
                request[key] = value
        requests.append(request)
    
    return requests

def upload_requests_to_couch(requests):
    """
    Send the given service request list to the couchdb.  Return the server 
    response.
    """
    couchdb_host = 'open311.couchone.com'
    couchdb_path = '/service-requests/_bulk_docs'
    docs = {'docs':requests}
    
    couchdb_conn = httplib.HTTPConnection(couchdb_host)
    upload_request = couchdb_conn.request(
        'POST', couchdb_path, json.dumps(docs),
        { 'Content-type' : 'application/json' })
    
    upload_response = couchdb_conn.getresponse()
    return upload_response.read()

if __name__ == '__main__':
    start, end = get_time_range()
    requests_stream = get_requests_from_SF(start, end)
    requests = parse_requests_doc(requests_stream)
    print upload_requests_to_couch(requests)
