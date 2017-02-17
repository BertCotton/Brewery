from flask import Flask, jsonify, request, send_file
from tinydb import TinyDB, Query
import requests
from StringIO import StringIO

app = Flask(__name__)

@app.route("/", methods=['GET'])
def index():
    return app.send_static_file('index.html')

@app.route('/Temp', methods=['GET'])
def getTemps():
    db = TinyDB("/mnt/scripts/RasPiBrew2/db.json")
    return jsonify(db.all())

@app.route('/Temp', methods=['POST'])
def setTemp():
    Id = int(request.form["Id"])
    Temp = request.form["SetTemp_F"]

    db = TinyDB("/mnt/scripts/RasPiBrew2/db.json")
    Record = Query()
    existing = db.search(Record.ID == Id)
    if len(existing) == 1:
        record = existing[0]
        record["SetTemp_F"] = int(Temp)

        db.update(record, Record.ID == record["ID"])

        existing = db.search(Record.ID == Id)
        return jsonify(existing[0])

    else:
        return "Not Found for Id %s Found %s records." % (Id, len(existing)), 404

@app.route('/Variance', methods=['POST'])
def setVariance():
    Id = int(request.form["Id"])
    Variance = request.form["Variance"]

    db = TinyDB("/mnt/scripts/RasPiBrew2/db.json")
    Record = Query()
    existing = db.search(Record.ID == Id)
    if len(existing) == 1:
        record = existing[0]
        record["Variance"] = int(Variance)

        db.update(record, Record.ID == record["ID"])

        existing = db.search(Record.ID == Id)
        return jsonify(existing[0])

    else:
        return "Not Found for Id %s Found %s records." % (Id, len(existing)), 404


@app.route("/Graph/Fermentation", methods=['GET'])
def getFermentationGraphImage():
    r = requests.get("http://192.168.0.101/render/?width=588&height=311&_salt=1486943807.735&target=brewery.fermentation.temp.fahrenheit")
    buffer_image = StringIO(r.content)
    buffer_image.seek(0)

    return send_file(buffer_image, mimetype='image/jpeg')

@app.route("/Graph/State", methods=['GET'])
def getStateGraphImage():
    r = requests.get("http://192.168.0.101/render/?width=588&height=311&_salt=1486965991.04&target=brewery.fermentation.state.cool&target=brewery.fermentation.state.heat&lineMode=connected&colorList=red%2Cblue&drawNullAsZero=true&connectedLimit=&areaMode=all")
    buffer_image = StringIO(r.content)
    buffer_image.seek(0)

    return send_file(buffer_image, mimetype='image/jpeg')

@app.route("/Graph/Ambient", methods=['GET'])
def getAmbientGraphImage():
    r = requests.get("http://192.168.0.101/render/?width=588&height=311&_salt=1486966099.936&target=brewery.ambient.temp.fahrenheit&drawNullAsZero=true")
    buffer_image = StringIO(r.content)
    buffer_image.seek(0)

    return send_file(buffer_image, mimetype='image/jpeg')


if __name__ == '__main__':

    app.debug = True
    app.run(use_reloader=False, host='0.0.0.0', port=5000)
