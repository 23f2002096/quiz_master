from flask import Flask,render_template
from config import SECRET_KEY,SQLALCHEMY_DATABASE_URI,SQLALCHEMY_TRACK_MODIFICATIONS
app = Flask(__name__)

app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS


import routes

import models


if __name__ == '__main__':
    app.run(debug=True)

