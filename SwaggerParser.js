class Operation
{
    constructor(operationID, path, method, parameters, responses)
    {
        this.operationID = operationID;
        this.path = path;
        this.method = method;
        this.parameters = parameters;
        this.responses = responses;
    }
}

class Path
{
    constructor(path)
    {
        this.path = path;
        this.operations = [];
    }
}

class Link
{
    constructor(originPath, originOperation, originResponse, targetOperation, parameters)
    {
        this.originPath = originPath;
        this.originOperation = originOperation;
        this.originResponse = originResponse;
        this.targetOperation = targetOperation;
        this.parameters = parameters;
    }
}

class Api
{
    constructor(paths,links)
    {
        this.paths = paths;
        this.links = links;
    }
}

const SwaggerParser = require("@apidevtools/swagger-parser");
//const apiFilename = "Pixi.yaml"
//const apiFilename = "linkExample.yaml"
//const apiFilename = "vapi.yaml"
//const apiFilename = "vampi.yaml"
const apiFilename = "crAPI.yaml"

const checkCircular = async function()
{
    let parser = new SwaggerParser();
    await parser.dereference(apiFilename);

    if (parser.$refs.circular) {
    console.log('The API contains circular references');
    }
    else{
        console.log('The API do not contain circular references');
    }

}

const iterateAll = (obj) =>
{   
    Object.keys(obj).forEach(key => {
        
        if (typeof obj[key] === 'object')
        {
            console.log("")
        }
        console.log(`key: ${key}, value: ${obj[key]}`)
    
        if (typeof obj[key] === 'object')
        {
            iterateAll(obj[key])
        }
    })
}

var n = 0
var m =0

const iterate = (obj) => {
    
    Object.keys(obj).forEach(key => {

        if(key === 'links')
        {
            n++
            console.log("")
            console.log(`LINK ${n}`)
            iterateAll(obj[key])
        }
        else if (typeof obj[key] === 'object')
        {
            m++
            iterate(obj[key])
        }
    })
}

const describeAPI = async function()
{
    let $refs = await SwaggerParser.parse(apiFilename);

    // Get the paths of ALL files in the API
    var n = 0;
    Object.entries($refs['paths']).forEach(([key, value]) => {
        console.log(`${key}: ${value}`);
        n++;
      });
      console.log(n);
    // Get the paths of local files only
    //$refs.paths("fs");

    // Get all URLs
    //$refs.paths("http", "https");
}

const getLinksfromAPI = async function()
{
    let $refs = await SwaggerParser.parse(apiFilename);

    console.log("");

    n = 0
    console.log("LINKS IN RESPONSES")
    iterate($refs.paths);
    console.log("")
    n=0
    console.log("REUSABLES");
    iterate($refs.components);

    
/*
    // Get the paths of ALL files in the API
    var n = 0;
    Object.entries($refs['paths']).forEach(([key, value]) => {
        console.log(`${key}: ${value}`);
        n++;
      });
      console.log(n);
    // Get the paths of local files only
    //$refs.paths("fs");

    // Get all URLs
    //$refs.paths("http", "https");
*/
}
/*
checkCircular();

getLinksfromAPI();
*/
///////////////////////////////////////////////////////////////////////

var apiPaths = [];
var apiLinks = [];

const parseEndpoints = async function()
{
    let $refs = await SwaggerParser.dereference(apiFilename);

    Object.entries($refs['paths']).forEach(([key, value]) => {
        let thisPath = new Path(key);
        apiPaths.push(thisPath);
    });
    
    apiPaths.forEach( function(entry) {
        Object.entries($refs['paths'][entry.path]).forEach(([method, value]) => {
            let auxOperationId = ""
            if (value.hasOwnProperty('operationId'))
            {
                auxOperationId = value["operationId"]
            }
            else
            {
                auxOperationId = entry.path + method
            }

            let auxParameters = {}
            if (value.hasOwnProperty('parameters'))
            {
                auxParameters = value["parameters"]
            }

            let auxResponses = {}
            if (value.hasOwnProperty('responses'))
            {
                auxResponses = value["responses"]
            }

            let thisOperation = new Operation(auxOperationId,
                                              entry.path,
                                              method,
                                              auxParameters,
                                              auxResponses);
            entry.operations.push(thisOperation);
        });
    });
}

const writeEndpoints = async function()
{
    await parseEndpoints();

    console.log(`API has ${apiPaths.length} Paths:`);

    apiPaths.forEach(function(entry) {
        console.log(entry.path);
    });
}

//writeEndpoints();

const parseLinks = async function()
{
    let $refs = await SwaggerParser.dereference(apiFilename);

    Object.entries($refs['paths']).forEach(([key, value]) => {
        let thisPath = key;
        Object.entries($refs['paths'][thisPath]).forEach(([key, value]) => {
            let thisMethod = key;
            Object.entries($refs['paths'][thisPath][thisMethod]["responses"]).forEach(([key, value]) => {
                let thisResponse = key;
                if(value.hasOwnProperty("links"))
                {
                    Object.entries($refs['paths'][thisPath][thisMethod]["responses"][thisResponse]["links"]).forEach(([key, value]) => {
                        let thisLinkOriginOp;
                        let thisLinkTargetOp;
                        let thisLinkPath;
                        apiPaths.forEach(function(path) {
                            path.operations.forEach(function(operation) {
                                if (operation.operationID == value["operationId"])
                                {
                                    thisLinkTargetOp = operation;
                                }

                                if (operation.operationID == $refs['paths'][thisPath][thisMethod]["operationId"])
                                {
                                    thisLinkOriginOp = operation;
                                    thisLinkPath = path;
                                }
                            });
                        });

                        if(thisLinkOriginOp && thisLinkTargetOp)
                        {
                            apiLinks.push(new Link(thisLinkPath,thisLinkOriginOp,thisResponse,thisLinkTargetOp,value["parameters"]));
                        }
                    });
                }
            });
        });
    });
}

const findLinks = async function()
{
    await parseEndpoints();
    await parseLinks();   
}

const writeApiLinksDescription = async function()
{
    await findLinks();
    console.log(JSON.stringify(new Api(apiPaths,apiLinks)));
}

writeApiLinksDescription();