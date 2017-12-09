# coding:utf-8

from flask import Flask
from flask_restful import Resource, Api, reqparse
from flask_cors import CORS

import urllib

app = Flask(__name__)
CORS(app)
api = Api(app)

class HelloWorld(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('idd', type=str, help='Rate to charge for this resource')
        args = parser.parse_args()
        return {'hello': urllib.unquote(args['idd'])}


api.add_resource(HelloWorld, '/')

if __name__ == '__main__':
    app.run(debug=True)
