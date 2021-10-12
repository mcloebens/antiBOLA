const express = require('express')
const cors = require('cors')
const app = express()
const port = 3000

app.use(express.urlencoded({
    extended: true
  }));  

app.use(express.json());

const corsConfig = {
  credentials: true,
  origin: true,
};

app.use(cors(corsConfig));

app.get('/', (req, res) => {
  res.send('Hello World!\n')
  console.log(req.route)
})

app.listen(port, () => {
  console.log(`Example app listening at http://localhost:${port}\n`)
})