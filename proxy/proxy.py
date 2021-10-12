#mitmdump -q -v -s proxy.py -R http://localhost:9200 -p 30001
#mitmdump -s proxy.py -p 30001 -> don't forget to configure the request sending tool

from operator import truediv
from pickletools import read_decimalnl_long
from mitmproxy import http
from subprocess import check_output
from urllib import parse
from nested_lookup import nested_lookup
import json
import copy
import networkx
import re


class Operation():
    def __init__(self, operationID, path, method, parameters, responses):
        self.operationID = operationID
        self.path = path
        self.method = method
        self.parameters = parameters
        self.responses = responses
#        self.responseSchemas = {}
#
#        for response, value in responses.items():
#            if "content" in value:
#                for content in value["content"]:
#                    if content == "application/json":
#                        if "schema" in value["content"]["application/json"]:
#                            self.responseSchemas[response] = value["content"]["application/json"]["schema"]

class Path():
    def __init__(self, path, operations=[]):
        self.path = path
        self.operations = operations

class Link:
    def __init__(self, originPath, originOperation, originResponse, targetOperation, parameters):
        self.originPath = originPath
        self.originOperation = originOperation
        self.originResponse = originResponse
        self.targetOperation = targetOperation
        self.parameters = parameters

class Api:
    def __init__(self, paths, links):
        self.paths = paths
        self.links = links

    def getOperationId(self, requestedPath, method):
        for path in self.paths:
            if (isValidPath(path.path, requestedPath)):
                for operation in path.operations:
                    if(operation.method.upper() == method.upper()):
                        return operation.operationID
        return None

    def getOperation(self, requestedPath, method):
        for path in self.paths:
            if (isValidPath(path.path, requestedPath)):
                for operation in path.operations:
                    if(operation.method.upper() == method.upper()):
                        return operation
        return None

    def findLinkForResponse(self, operationID, serverResponse):
        links = []
        for link in self.links:
            if link.originOperation.operationID == operationID:
                if link.originResponse == str(serverResponse):
                    links.append(link)
        return links

    def findTargetOperation(self, operationID):
        links = []
        for link in self.links:
            if link.targetOperation.operationID == operationID:
                links.append(link)
        return links

class ReturnedDataFromOriginCall:
    def __init__(self, link, parameters):
        self.link = link
        self.parameters = parameters

class Session:
    def __init__(self, data):
        self.diGraph = networkx.DiGraph()
        self.diGraph.add_edge(data.link.originOperation.operationID, data.link.targetOperation.operationID, data=data.parameters)
#        print(self.diGraph[data.link.originOperation.operationID][data.link.targetOperation.operationID]["data"])

    def updateData(self, data):

        if self.diGraph.has_edge(data.link.originOperation.operationID, data.link.targetOperation.operationID):
            oldData = self.diGraph[data.link.originOperation.operationID][data.link.targetOperation.operationID]["data"]
            for key, list in data.parameters.items():
                if key in oldData:
                    oldData[key].extend(list)
                else:
                    oldData[key] = list
        else:
            self.diGraph.add_edge(data.link.originOperation.operationID, data.link.targetOperation.operationID, data=data.parameters)


    def returnDataFromLink(self, link):
        if self.diGraph.has_edge(link.originOperation.operationID, link.targetOperation.operationID):
            return self.diGraph[link.originOperation.operationID][link.targetOperation.operationID]["data"]
        return {}

class AllowList:
    def __init__(self):
        self.sessionList = {}

    def addReturnedDataFromOriginCall(self, token, data):
        if token not in self.sessionList:
            self.sessionList[token] = Session(data)
        else:
            self.sessionList[token].updateData(data)

    def retrieveSessionDataForLink(self, token, link):
        if token in self.sessionList:
            return self.sessionList[token].returnDataFromLink(link)
        else:
            return {}

def parseAPI(jsonObj):
    jsonPaths = jsonObj['paths']
    jsonLinks = jsonObj['links']

    paths = []
    for path in jsonPaths:
        auxPath = Path(path['path'],[])
        for operation in path['operations']:
            auxOperation = Operation(**operation)
            auxPath.operations.append(copy.deepcopy(auxOperation))
        paths.append(copy.deepcopy(auxPath))

    links = []
    for link in jsonLinks:
        auxOriginPath = None
        auxOriginOperation = None
        for path in paths:
            if link['originPath']['path'] == path.path:
                auxOriginPath = path
                for operation in path.operations:
                    if operation.operationID == link['originOperation']['operationID']:
                        auxOriginOperation = operation
                        break
                break
        auxOriginResponse = link['originResponse']
        auxTargetOperation = Operation(**link['targetOperation'])
        auxOriginParameters = link['parameters']
        auxLink = Link(auxOriginPath,auxOriginOperation,auxOriginResponse,auxTargetOperation,auxOriginParameters)
        links.append(copy.deepcopy(auxLink))

    return Api(paths,links)

def isValidPath(pathTemplate,path):
    #print(pathTemplate)
    #print(path)
    nodeOutput = check_output(['node', '/home/marcelo/git/AntiBOLAMiddleware/isValidPath.js',pathTemplate,path])
    #print(json.loads(nodeOutput))
    return json.loads(nodeOutput)

#MAYBE IT CAN BE GENERALIZED FOR A LIST
def findParametersInResponse(link, flow):
    #response = str(responseFlow.status_code)
    parameters = {}
    #schema = None

    #if response in link.responseSquemas:
    #    schema = link.responseSquemas[response]

    for name, position in link.parameters.items():
        auxPosition = position.split("#/")
        if auxPosition[0] == "$response.body":
            parameters[name] = nested_lookup(auxPosition[1], flow.response.json())
        if auxPosition[0] == "$request.body":
            parameters[name] = nested_lookup(auxPosition[1], flow.request.json())
    
    #print(parameters)

    return parameters

def checkParameterInRequest(requestFlow, parameter, valueList, inField, operation):
    if inField == "header":
        for item in valueList:
            if str(requestFlow.headers[parameter]) == str(item):
                print("- PARAMETER " + parameter + " : " + str(item) + " FOUND IN SESSION RECORDS")
                return True
    
    if inField == "path":
        templatePathParameters = operation.path.split("/")
        realPathParameters = requestFlow.path.split("?")[0].split("/")
        matchedParameters = {}

        i = 0
        for item in templatePathParameters:
            if item:
                if item[0] == '{' and item[len(item)-1] == '}':
                    auxItem = item.strip("{}")
                    matchedParameters[auxItem] = realPathParameters[i]
            i += 1
        if parameter in matchedParameters:
            for item in valueList:
                if matchedParameters[parameter] == str(item):
                    print("- PARAMETER " + parameter + " : " + str(item) + " FOUND IN SESSION RECORDS")
                    return True

    if inField == "query":
        for item in valueList:
            if str(requestFlow.query[parameter]) == str(item):
                print("- PARAMETER " + parameter + " : " + str(item) + " FOUND IN SESSION RECORDS")
                return True

    return False

def findTokens(flow):
    tokens = []

    for key, value in flow.request.headers.items():
        if re.search('token', key, re.IGNORECASE):
            tokens.append(value)
        if re.search('auth', key, re.IGNORECASE):
            if re.search('bearer', value, re.IGNORECASE):
                tokens.append(value)
    
    for key, value in flow.request.cookies.items():
        if re.search('token', key, re.IGNORECASE):
            tokens.append(value)
        if re.search('auth', key, re.IGNORECASE):
            if re.search('bearer', value, re.IGNORECASE):
                tokens.append(value)

    if flow.response:
        if isinstance(flow.response.json(), dict):
            for key, value in flow.response.json().items():
                if re.search('token', key, re.IGNORECASE):
                    tokens.append(value)

            for key, value in flow.response.headers.items():
                if re.search('token', key, re.IGNORECASE):
                    tokens.append(value)

    #print(tokens)

    return tokens

class Printer:
    def __init__(self):
        nodeOutput = check_output(['node', '/home/marcelo/git/AntiBOLAMiddleware/SwaggerParser.js'])
        self.api = parseAPI(json.loads(nodeOutput))
        self.allowList = AllowList()

    def request(self, flow: http.HTTPFlow):
        print("="*50)
        print("REQUEST")
        print(flow.request.method + " " + flow.request.path)
        print("")
        #print("-"*50 + "request headers:")
        #for k, v in flow.request.headers.items():
        #    print("%-20s: %s" % (k.upper(), v))

        path = flow.request.path.split('?')[0]

        operation = self.api.getOperation(path, flow.request.method)
        if not operation:
            print("Path/Method isn't listed on API")
            return

        links = self.api.findTargetOperation(operation.operationID)
        block = False

        if len(links) > 0:
            block = True
            tokens = findTokens(flow)
            for token in tokens:
                #print(token)
                for link in links:
                    print("- LINK FOUND - CONSUMER")
                    print("- ORIGIN OP: " + link.originOperation.operationID + " - RESPONSE: " + link.originResponse)
                    print("- TARGET OP: " + link.targetOperation.operationID)
                    data = self.allowList.retrieveSessionDataForLink(token, link)
                    if data:
                        parameterCount = 0
                        for parameter, value in link.parameters.items():
                            print("SEARCHING PARAMETER " + parameter + " VALUE IN SESSION RECORDS")
                            parameterCount += 1
                            if parameter in data:
                                for targetParameter in link.targetOperation.parameters:
                                    if targetParameter['name'] == parameter:
                                        if checkParameterInRequest(flow.request, parameter, data[parameter], targetParameter['in'], operation):
                                            parameterCount -= 1
                            else:
                                print("- PARAMETER VALUE NOT FOUND IN SESSION RECORDS")
                        if parameterCount == 0:
                            block = False
                    else:
                        print("- NO DATA FOUND FOR THE LINK IN SESSION RECORDS")
                #break
        
        if block:
            print("")
            print("BOLA EXPLOIT ATTEMPT DETECTED - REQUEST BLOCKED")
            flow.response = http.Response.make(401)#UNAUTH
        
        print("")

    def response(self, flow: http.HTTPFlow):
        print("="*50)
        print("RESPONSE")
        if flow.response.reason:
            print(str(flow.response.status_code) + " - " + flow.response.reason)
        else:
            print(str(flow.response.status_code))
        print("")
        #print(json.loads(flow.response.content))
        #print("-"*50 + "response headers:")
        #for k, v in flow.response.headers.items():
        #    print("%-20s: %s" % (k.upper(), v))
        #    print("-"*50 + "response headers:")
        #print(flow.response.json())

        path = flow.request.path.split('?')[0]

        operationID = self.api.getOperationId(path, flow.request.method)
        if not operationID:
            return

        for link in self.api.findLinkForResponse(operationID, flow.response.status_code):
            print("LINK FOUND - PRODUCTOR")
            print("- ORIGIN OP: " + link.originOperation.operationID + " - RESPONSE: " + link.originResponse)
            print("- TARGET OP: " + link.targetOperation.operationID)
            returnedParameters = ReturnedDataFromOriginCall(link,findParametersInResponse(link, flow))
            print("- DATA RECORDED: " + str(returnedParameters.parameters))
            print("")
            tokens = findTokens(flow)
            for token in tokens:
                #print(returnedParameters)
                self.allowList.addReturnedDataFromOriginCall(token, copy.deepcopy(returnedParameters))

addons = [
    Printer()
]