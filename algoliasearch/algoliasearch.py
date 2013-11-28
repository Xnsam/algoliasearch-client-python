"""
Copyright (c) 2013 Algolia
http://www.algolia.com/
Thanks to Arthur Lenoir <arthur (at) lenoir.me> for the initial version.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
 
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
 
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""
import json
import random
import sys
if sys.version < '3':
  from urllib import quote
  from urllib import urlencode
else:
  from urllib.parse import quote
  from urllib.parse import urlencode
import urllib3
import time

POOL_MANAGER = urllib3.PoolManager()

# Exception launched by Algolia Client when an error occured
class AlgoliaException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

""" 
Entry point in the Python API.
You should instanciate a Client object with your ApplicationID, ApiKey and Hosts 
to start using Algolia Search API
"""
class Client:
    """
    Algolia Search library initialization
    @param applicationID the application ID you have in your admin interface
    @param apiKey a valid API key for the service
    @param hostsArray the list of hosts that you have received for the service
    """
    def __init__(self, applicationID, apiKey, hostsArray = None):
        if (hostsArray == None):
          self.hosts = ["%s-1.algolia.io" % applicationID, "%s-2.algolia.io" % applicationID, "%s-3.algolia.io" % applicationID]
        else:
          self.hosts = hostsArray
        random.shuffle(self.hosts)
        self.applicationID = applicationID
        self.apiKey = apiKey
        self.headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'X-Algolia-API-Key': self.apiKey,
            'X-Algolia-Application-Id': self.applicationID,
            'User-Agent': 'Algolia Search for python'
        }

    """
    List all existing indexes
    return an object of the form 
       {"items": [{ "name": "contacts", "createdAt": "2013-01-18T15:33:13.556Z"},
                  {"name": "notes", "createdAt": "2013-01-18T15:33:13.556Z"}]}
    """
    def listIndexes(self):
        return AlgoliaUtils_request(self.headers, self.hosts, "GET", "/1/indexes/")

    """
    Delete an index

    @param indexName the name of index to delete
    Return an object of the form {"deletedAt": "2013-01-18T15:33:13.556Z"}
    """
    def deleteIndex(self, indexName):
        return AlgoliaUtils_request(self.headers, self.hosts, "DELETE", "/1/indexes/%s" % quote(indexName.encode('utf8')))

    """
    Move an existing index.

    @param srcIndexName the name of index to copy.
    @param dstIndexName the new index name that will contains a copy of srcIndexName (destination will be overriten if it already exist).
    """
    def moveIndex(self, srcIndexName, dstIndexName):
        request = {"operation": "move", "destination": dstIndexName}
        return AlgoliaUtils_request(self.headers, self.hosts, "POST", "/1/indexes/%s/operation" % quote(srcIndexName.encode('utf8')), request)
    
    """
    Copy an existing index.

    @param srcIndexName the name of index to copy.
    @param dstIndexName the new index name that will contains a copy of srcIndexName (destination will be overriten if it already exist).
    """
    def copyIndex(self, srcIndexName, dstIndexName):
        request = {"operation": "copy", "destination": dstIndexName}
        return AlgoliaUtils_request(self.headers, self.hosts, "POST", "/1/indexes/%s/operation" % (quote(srcIndexName.encode('utf8'))), request)
    
    """
    Return last logs entries.

    @param offset Specify the first entry to retrieve (0-based, 0 is the most recent log entry).
    @param length Specify the maximum number of entries to retrieve starting at offset. Maximum allowed value: 1000.
    """
    def getLogs(self, offset = 0, length = 10):
        return AlgoliaUtils_request(self.headers, self.hosts, "GET", "/1/logs?offset=%d&length=%d" % (offset, length))

    """
    Get the index object initialized (no server call needed for initialization)

    @param indexName the name of index
    """
    def initIndex(self, indexName):
        return Index(self.headers, self.hosts, indexName)

    """
    List all existing user keys with their associated ACLs
    """
    def listUserKeys(self):
        return AlgoliaUtils_request(self.headers, self.hosts, "GET", "/1/keys")

    # Get ACL of a user key
    def getUserKeyACL(self, key):
        return AlgoliaUtils_request(self.headers, self.hosts, "GET", "/1/keys/%s" % key)

    # Delete an existing user key
    def deleteUserKey(self, key):
        return AlgoliaUtils_request(self.headers, self.hosts, "DELETE", "/1/keys/%s" % key)

    """
    Create a new user key

    @param acls the list of ACL for this key. Defined by an array of strings that 
           can contains the following values:
             - search: allow to search (https and http)
             - addObject: allows to add/update an object in the index (https only)
             - deleteObject : allows to delete an existing object (https only)
             - deleteIndex : allows to delete index content (https only)
             - settings : allows to get index settings (https only)
             - editSettings : allows to change index settings (https only)
    @param validity the number of seconds after which the key will be automatically removed (0 means no time limit for this key)
    @param maxQueriesPerIPPerHour Specify the maximum number of API calls allowed from an IP address per hour.  Defaults to 0 (no rate limit).
    @param maxHitsPerQuery Specify the maximum number of hits this API key can retrieve in one call. Defaults to 0 (unlimited) 
    """
    def addUserKey(self, acls, validity = 0, maxQueriesPerIPPerHour = 0, maxHitsPerQuery = 0):
        return AlgoliaUtils_request(self.headers, self.hosts, "POST", "/1/keys", {"acl": acls, "validity": validity, "maxQueriesPerIPPerHour": maxQueriesPerIPPerHour, "maxHitsPerQuery": maxHitsPerQuery} )

"""
Contains all the functions related to one index
You should use Client.initIndex(indexName) to retrieve this object
"""
class Index:
    def __init__(self, headers, hosts, indexName):
        self.hosts = hosts
        self.headers = headers
        self.indexName = indexName
        self.urlIndexName = quote(self.indexName.encode('utf8'))

    """
    Add an object in this index
     
    @param content contains the object to add inside the index. 
      The object is represented by an associative array
    @param objectID (optional) an objectID you want to attribute to this object 
      (if the attribute already exist the old object will be overwrite)
    """
    def addObject(self, content, objectID = None):
        if objectID is None:
            return AlgoliaUtils_request(self.headers, self.hosts, "POST", "/1/indexes/%s" % self.urlIndexName, content)
        else:
            return AlgoliaUtils_request(self.headers, self.hosts, "PUT", "/1/indexes/%s/%s" % (self.urlIndexName, quote(objectID.encode('utf8'))), content)


    """
    Add several objects

    @param objects contains an array of objects to add
    """
    def addObjects(self, objects):
        requests = []
        for obj in objects:
            requests.append({"action": "addObject", "body": obj})
        request = {"requests": requests}
        return AlgoliaUtils_request(self.headers, self.hosts, "POST", "/1/indexes/%s/batch" % self.urlIndexName, request)

    """
    Get an object from this index

    @param objectID the unique identifier of the object to retrieve
    @param attributesToRetrieve (optional) if set, contains the list of attributes to retrieve as a string separated by a comma
    """
    def getObject(self, objectID, attributesToRetrieve = None):
        objID = quote(objectID.encode('utf8'))
        if (attributesToRetrieve == None):
            return AlgoliaUtils_request(self.headers, self.hosts, "GET", "/1/indexes/%s/%s" % (self.urlIndexName, objID))
        else:
            return AlgoliaUtils_request(self.headers, self.hosts, "GET", "/1/indexes/%s/%s?attributes=%s" % (self.urlIndexName, objID, attributesToRetrieve))

    """
    Update partially an object (only update attributes passed in argument)
    
    @param partialObject contains the object attributes to override, the 
           object must contains an objectID attribute
    """
    def partialUpdateObject(self, partialObject):
        return AlgoliaUtils_request(self.headers, self.hosts, "POST", "/1/indexes/%s/%s/partial" % (self.urlIndexName, quote(partialObject["objectID"].encode('utf8'))), partialObject)

    """
    Override the content of object
    
    @param object contains the object to save, the object must contains an objectID attribute
    """
    def saveObject(self, obj):
        return AlgoliaUtils_request(self.headers, self.hosts, "PUT", "/1/indexes/%s/%s" % (self.urlIndexName, quote(obj["objectID"].encode('utf8'))), obj)

    """
    Override the content of several objects

    @param objects contains an array of objects to update (each object must contains a objectID attribute)
    """
    def saveObjects(self, objects):
        requests = []
        for obj in objects:
            requests.append({"action": "updateObject", "objectID": obj["objectID"], "body": obj})
        request = {"requests": requests}
        return AlgoliaUtils_request(self.headers, self.hosts, "POST", "/1/indexes/%s/batch" % self.urlIndexName, request)

    """
    Delete an object from the index 

    @param objectID the unique identifier of object to delete
    """
    def deleteObject(self, objectID):
        if (len(objectID) == 0):
            raise AlgoliaException("objectID is required")
        return AlgoliaUtils_request(self.headers, self.hosts, "DELETE", "/1/indexes/%s/%s" % (self.urlIndexName, quote(objectID.encode('utf8'))))

    """
    Search inside the index
    
    @param query the full text query
    @param args (optional) if set, contains an associative array with query parameters:
      - page: (integer) Pagination parameter used to select the page to retrieve.
                        Page is zero-based and defaults to 0. Thus, to retrieve the 10th page you need to set page=9
      - hitsPerPage: (integer) Pagination parameter used to select the number of hits per page. Defaults to 20.
      - attributesToRetrieve: a string that contains the list of object attributes you want to retrieve (let you minimize the answer size).
        Attributes are separated with a comma (for example "name,address").
        You can also use a string array encoding (for example ["name","address"]). 
        By default, all attributes are retrieved. You can also use '*' to retrieve all values when an attributesToRetrieve setting is specified for your index.
      - attributesToHighlight: a string that contains the list of attributes you want to highlight according to the query. 
        Attributes are separated by a comma. You can also use a string array encoding (for example ["name","address"]). 
        If an attribute has no match for the query, the raw value is returned. By default all indexed text attributes are highlighted. 
        You can use `*` if you want to highlight all textual attributes. Numerical attributes are not highlighted. 
        A matchLevel is returned for each highlighted attribute and can contain:
           - full: if all the query terms were found in the attribute,
           - partial: if only some of the query terms were found,
           - none: if none of the query terms were found.
      - attributesToSnippet: a string that contains the list of attributes to snippet alongside the number of words to return (syntax is `attributeName:nbWords`). 
         Attributes are separated by a comma (Example: attributesToSnippet=name:10,content:10).
         You can also use a string array encoding (Example: attributesToSnippet: ["name:10","content:10"]). By default no snippet is computed.
      - minWordSizefor1Typo: the minimum number of characters in a query word to accept one typo in this word. Defaults to 3.
      - minWordSizefor2Typos: the minimum number of characters in a query word to accept two typos in this word. Defaults to 7.
      - getRankingInfo: if set to 1, the result hits will contain ranking information in _rankingInfo attribute.
      - aroundLatLng: search for entries around a given latitude/longitude (specified as two floats separated by a comma).
        For example aroundLatLng=47.316669,5.016670). 
        You can specify the maximum distance in meters with the aroundRadius parameter (in meters) and the precision for ranking with aroundPrecision
        (for example if you set aroundPrecision=100, two objects that are distant of less than 100m will be considered as identical for "geo" ranking parameter).
        At indexing, you should specify geoloc of an object with the _geoloc attribute (in the form {"_geoloc":{"lat":48.853409, "lng":2.348800}})
      - insideBoundingBox: search entries inside a given area defined by the two extreme points of a rectangle (defined by 4 floats: p1Lat,p1Lng,p2Lat,p2Lng).
        For example insideBoundingBox=47.3165,4.9665,47.3424,5.0201).
        At indexing, you should specify geoloc of an object with the _geoloc attribute (in the form {"_geoloc":{"lat":48.853409, "lng":2.348800}})
      - numericFilters: a string that contains the list of numeric filters you want to apply separated by a comma. 
        The syntax of one filter is `attributeName` followed by `operand` followed by `value`. Supported operands are `<`, `<=`, `=`, `>` and `>=`. 
        You can have multiple conditions on one attribute like for example numericFilters=price>100,price<1000. 
        You can also use a string array encoding (for example numericFilters: ["price>100","price<1000"]).
      - tagFilters: filter the query by a set of tags. You can AND tags by separating them by commas. 
        To OR tags, you must add parentheses. For example, tags=tag1,(tag2,tag3) means tag1 AND (tag2 OR tag3).
        You can also use a string array encoding, for example tagFilters: ["tag1",["tag2","tag3"]] means tag1 AND (tag2 OR tag3).
        At indexing, tags should be added in the _tags** attribute of objects (for example {"_tags":["tag1","tag2"]}). 
      - facetFilters: filter the query by a list of facets. 
        Facets are separated by commas and each facet is encoded as `attributeName:value`. 
        For example: `facetFilters=category:Book,author:John%20Doe`. 
        You can also use a string array encoding (for example `["category:Book","author:John%20Doe"]`).
      - facets: List of object attributes that you want to use for faceting. 
        Attributes are separated with a comma (for example `"category,author"` ). 
        You can also use a JSON string array encoding (for example ["category","author"]).
        Only attributes that have been added in **attributesForFaceting** index setting can be used in this parameter. 
        You can also use `*` to perform faceting on all attributes specified in **attributesForFaceting**.
      - queryType: select how the query words are interpreted, it can be one of the following value:
         - prefixAll: all query words are interpreted as prefixes,
         - prefixLast: only the last word is interpreted as a prefix (default behavior),
         - prefixNone: no query word is interpreted as a prefix. This option is not recommended.
      - optionalWords: a string that contains the list of words that should be considered as optional when found in the query. 
        The list of words is comma separated.
    """
    def search(self, query, args = None):
        if args == None:
            return AlgoliaUtils_request(self.headers, self.hosts, "GET", "/1/indexes/%s?query=%s" % (self.urlIndexName, quote(query.encode('utf8'))))
        else:
            for k, v in args.iteritems():
                if isinstance(v, (list, tuple)):
                    args[k] = json.dumps(v)
                else:
                    args[k] = v
            return AlgoliaUtils_request(self.headers, self.hosts, "GET", "/1/indexes/%s?query=%s&%s" % (self.urlIndexName, quote(query.encode('utf8')), urlencode(args)))

    """
    Wait the publication of a task on the server. 
    All server task are asynchronous and you can check with this method that the task is published.

    @param taskID the id of the task returned by server
    @param timeBeforeRetry the time in milliseconds before retry (default = 100ms)
    """
    def waitTask(self, taskID, timeBeforeRetry = 100):
        while True:
            res = AlgoliaUtils_request(self.headers, self.hosts, "GET", "/1/indexes/%s/task/%d/" % (self.urlIndexName, taskID))
            if (res["status"] == "published"):
                return res
            time.sleep(timeBeforeRetry / 1000)

    # Get settings of this index
    def getSettings(self):
        return AlgoliaUtils_request(self.headers, self.hosts, "GET", "/1/indexes/%s/settings" % self.urlIndexName)
  
    # This function deletes the index content. Settings and index specific API keys are kept untouched.
    def clearIndex(self):
        return AlgoliaUtils_request(self.headers, self.hosts, "POST", "/1/indexes/%s/clear" % self.urlIndexName)

    """
      Set settings for this index
      
      @param settigns the settings object that can contains :
       - minWordSizefor1Typo: (integer) the minimum number of characters to accept one typo (default = 3).
       - minWordSizefor2Typos: (integer) the minimum number of characters to accept two typos (default = 7).
       - hitsPerPage: (integer) the number of hits per page (default = 10).
       - attributesToRetrieve: (array of strings) default list of attributes to retrieve in objects. 
         If set to null, all attributes are retrieved.
       - attributesToHighlight: (array of strings) default list of attributes to highlight. 
         If set to null, all indexed attributes are highlighted.
       - attributesToSnippet**: (array of strings) default list of attributes to snippet alongside the number of words to return (syntax is attributeName:nbWords).
         By default no snippet is computed. If set to null, no snippet is computed.
       - attributesToIndex: (array of strings) the list of fields you want to index.
         If set to null, all textual and numerical attributes of your objects are indexed, but you should update it to get optimal results.
         This parameter has two important uses:
           - Limit the attributes to index: For example if you store a binary image in base64, you want to store it and be able to 
             retrieve it but you don't want to search in the base64 string.
           - Control part of the ranking*: (see the ranking parameter for full explanation) Matches in attributes at the beginning of 
             the list will be considered more important than matches in attributes further down the list. 
             In one attribute, matching text at the beginning of the attribute will be considered more important than text after, you can disable 
             this behavior if you add your attribute inside `unordered(AttributeName)`, for example attributesToIndex: ["title", "unordered(text)"].
       - attributesForFaceting: (array of strings) The list of fields you want to use for faceting. 
         All strings in the attribute selected for faceting are extracted and added as a facet. If set to null, no attribute is used for faceting.
       - ranking: (array of strings) controls the way results are sorted.
         We have six available criteria: 
          - typo: sort according to number of typos,
          - geo: sort according to decreassing distance when performing a geo-location based search,
          - proximity: sort according to the proximity of query words in hits,
          - attribute: sort according to the order of attributes defined by attributesToIndex,
          - exact: sort according to the number of words that are matched identical to query word (and not as a prefix),
          - custom: sort according to a user defined formula set in **customRanking** attribute.
         The standard order is ["typo", "geo", "proximity", "attribute", "exact", "custom"]
       - customRanking: (array of strings) lets you specify part of the ranking.
         The syntax of this condition is an array of strings containing attributes prefixed by asc (ascending order) or desc (descending order) operator.
         For example `"customRanking" => ["desc(population)", "asc(name)"]`  
       - queryType: Select how the query words are interpreted, it can be one of the following value:
         - prefixAll: all query words are interpreted as prefixes,
         - prefixLast: only the last word is interpreted as a prefix (default behavior),
         - prefixNone: no query word is interpreted as a prefix. This option is not recommended.
       - highlightPreTag: (string) Specify the string that is inserted before the highlighted parts in the query result (default to "<em>").
       - highlightPostTag: (string) Specify the string that is inserted after the highlighted parts in the query result (default to "</em>").
       - optionalWords: (array of strings) Specify a list of words that should be considered as optional when found in the query.
 
     """
    def setSettings(self, settings):
        return AlgoliaUtils_request(self.headers, self.hosts, "PUT", "/1/indexes/%s/settings" % self.urlIndexName, settings)

    """
    List all existing user keys of this index with their associated ACLs
    """
    def listUserKeys(self):
        return AlgoliaUtils_request(self.headers, self.hosts, "GET", "/1/indexes/%s/keys" % self.urlIndexName)

    # Get ACL of a user key associated to this index
    def getUserKeyACL(self, key):
        return AlgoliaUtils_request(self.headers, self.hosts, "GET", "/1/indexes/%s/keys/%s" % (self.urlIndexName, key))

    # Delete an existing user key associated to this index
    def deleteUserKey(self, key):
        return AlgoliaUtils_request(self.headers, self.hosts, "DELETE", "/1/indexes/%s/keys/%s" % (self.urlIndexName, key))

    """
    Create a new user key associated to this index (can only access to this index)

    @param acls the list of ACL for this key. Defined by an array of strings that 
           can contains the following values:
             - search: allow to search (https and http)
             - addObject: allows to add/update an object in the index (https only)
             - deleteObject : allows to delete an existing object (https only)
             - deleteIndex : allows to delete index content (https only)
             - settings : allows to get index settings (https only)
             - editSettings : allows to change index settings (https only)
    @param validity the number of seconds after which the key will be automatically removed (0 means no time limit for this key)
    @param maxQueriesPerIPPerHour Specify the maximum number of API calls allowed from an IP address per hour.  Defaults to 0 (no rate limit).
    @param maxHitsPerQuery Specify the maximum number of hits this API key can retrieve in one call. Defaults to 0 (unlimited) 
    """
    def addUserKey(self, acls, validity = 0, maxQueriesPerIPPerHour = 0, maxHitsPerQuery = 0):
        return AlgoliaUtils_request(self.headers, self.hosts, "POST", "/1/indexes/%s/keys" % self.urlIndexName, {"acl": acls, "validity": validity, "maxQueriesPerIPPerHour": maxQueriesPerIPPerHour, "maxHitsPerQuery": maxHitsPerQuery} )

# Util function used to send request
def AlgoliaUtils_request(headers, hosts, method, request, body = None):
    for host in hosts:
        try:
            obj = None
            if body != None:
                obj = json.dumps(body)
            conn = POOL_MANAGER.connection_from_host(host, scheme = 'https')
            answer  = conn.urlopen(method, request, headers = headers, body = obj)
            content = json.loads(answer.data.decode('utf-8'))
            if answer.status == 400:
                raise AlgoliaException(content["message"])
            elif answer.status == 403:
                raise AlgoliaException("Invalid Application-ID or API-Key")
            elif answer.status == 404:
                raise AlgoliaException("Resource does not exist")
            elif answer.status == 200 or answer.status == 201:
                return content
        except AlgoliaException as e:
            raise e
        except Exception as e:
            print (e)
            pass
    raise AlgoliaException("Unreachable host")

