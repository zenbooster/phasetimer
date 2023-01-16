const pavlok = require('pavlok')
const express = require('express')
//const logger = require('express-logger')
const path = require('path')

//CLIENT_ID = ""
//CLIENT_SECRET = ""

pavlok.init(CLIENT_ID, CLIENT_SECRET)
pavlok.login(function (result, code) {
  if (result) {
    console.log("Code is " + code)
    //pavlok.vibrate({value: 13})
	pavlok.vibrate({value: 50})
    console.log("Let's go!")

	var app = express();
	//app.use(logger('dev')); // выводим все запросы со статусами в консоль
	//app.use(express.bodyParser()); // стандартный модуль, для парсинга JSON в запросах
	//app.use(express.methodOverride()); // поддержка put и delete
	//app.use(app.router); // модуль для простого задания обработчиков путей

	app.get('/vibe/:lvl', function (req, res) {
		var lvl = parseInt(req.params.lvl, 10);
		console.log(lvl);
		pavlok.vibrate({value: lvl})
		res.send('ok');
	});
	app.get('/zap/:lvl', function (req, res) {
		var lvl = parseInt(req.params.lvl, 10);
		console.log(lvl);
		pavlok.zap({value: lvl})
		res.send('ok');
	});

	app.listen(1337, function(){
		console.log('Express server listening on port 1337');
	});
  }
})
