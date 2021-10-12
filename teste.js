
var path = "/2.0/repositories/{username}/name/{id}"

var path1 = "/2.0/repositories/name/name/id"

var path2 = "/2.0/repositories/name/name/name"

var query1 = "?d=1"


var replaced = path.replace(/\{(.*?)\}/g,":$1")

const { match } = require('node-match-path')

if(match(replaced,path1).matches)
{
    console.log("MATCH");
}
else
{
    console.log("DON'T MATCH");
}

console.log(match(replaced,path1));
console.log(match(replaced,path2));

const urlParams = new URLSearchParams(query1);

entries = urlParams.entries();

for(const entry of entries) {
    console.log(urlParams);
  }

//TODO > Strip '?' to retrieve query params