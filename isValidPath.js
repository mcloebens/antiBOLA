const myArgs = process.argv.slice(2);
const { match } = require('node-match-path')

if (myArgs.length != 2)
{
    console.log(JSON.stringify(false));
}
else
{
    var pathTemplate = myArgs[0]
    var path = myArgs[1]

    var replaced = pathTemplate.replace(/\{(.*?)\}/g,":$1")
    if(match(replaced,path).matches)
    {
        console.log(JSON.stringify(true));
    }
    else
    {
        console.log(JSON.stringify(false));
    }
}