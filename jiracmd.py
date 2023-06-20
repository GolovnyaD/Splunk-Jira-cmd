import json
from urllib import request, parse
import base64

import os, sys
import time
import re

import requests

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'searchcommands_app', 'lib'))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from splunklib.six.moves import range

usr = "CHANGEME"
pswd = "CHANGEME"
url = "https://jira.ringcentral.com:443"
b64auth = str(base64.urlsafe_b64encode(f"{usr}:{pswd}".encode('utf-8')),'utf-8')
headers = {"Authorization": f"Basic {b64auth}"}


def cleanNullTerms(d):
   clean = {}
   for k, v in d.items():
      if isinstance(v, dict):
         nested = cleanNullTerms(v)
         if len(nested.keys()) > 0:
            clean[k] = nested
      elif v is not None:
         clean[k] = v
   return clean


@Configuration()
class GenerateHelloCommand(GeneratingCommand):
    project = Option()
    #project = Option(require=True)
    query = Option()
    query_fields = Option()
    startfrom = Option(validate=validators.Integer(0))
    limit = Option(validate=validators.Integer(0))



    def generate(self):
        #query = f'project = "{self.project}"'
        #if self.query:
        #    query = query + " AND " + self.query
        #q = parse.quote_plus(query)
        if self.project and self.query:
            q = f'project = "{self.project}" AND {self.query}'
        elif self.query:
            q = self.query
        elif self.project:
            q = f'project = "{self.project}"'
        else:
            yield {'_raw': 'no project or query parameter was set'}
            exit(-1)

        if self.query_fields:
            qf = "&fields=" + parse.quote_plus(str(self.query_fields))
        else:
            qf = ''

        if self.startfrom and int(self.startfrom) > 0:
            st = '&startAt=' + str(self.startfrom)
        else:
            st = ''

        if self.limit and int(self.limit) > 0:
            lim = '&maxResults=' + str(self.limit)
        else:
            lim = '&maxResults=1000'


        page = 0
        while True:
            try:
                response = requests.get(url=f"{url}/rest/api/2/search?jql={q}{qf}{st}{lim}", auth=(usr, pswd),
                                        headers=headers)
            except requests.exceptions.RequestException as e:
                yield {'_raw': "Exception: " + str(e)}
                break

            if response.status_code != 200:
                yield {'_raw': 'Response status_conde not 200 ' + response.text}
                break

            ans = json.loads(response.text)
            # yield {'_time': time.time(), '_raw': ans, 'sourcetype': "jira:json", "info": len(ans['issues'])}

            for issue in ans['issues']:
                issue = cleanNullTerms(issue)
                yield {'_time': time.time(), '_raw': json.dumps(issue), 'sourcetype': "_json"}

            if not self.limit and not self.startfrom and len(ans['issues']) == 1000:
                page = page + 1
                st = '&startAt=' + str(1000 * page)
                req = request.Request(url=f"{url}/rest/api/2/search?jql={q}{qf}{st}{lim}", headers=headers, method="GET")
            else:
                break




dispatch(GenerateHelloCommand, sys.argv, sys.stdin, sys.stdout, __name__)
