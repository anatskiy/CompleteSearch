from flask import render_template, jsonify
from app import app

import os
import json


@app.route('/')
def index():
    """ Show index page. """

    # If facets file exists, show Search View. Otherwise, show Upload View
    facets_file = os.path.join(app.config['BASE_DIR'], 'data/facets.json')
    uploaded = os.path.isfile(facets_file)

    return render_template(
        'index.html',
        DATABASE_UPLOADED=uploaded,
        DEBUG=app.config['DEBUG']
    )


@app.route('/get_facets/', methods=['GET'])
def get_facets():
    """ Return all facets. """
    facets_file = os.path.join(app.config['BASE_DIR'], 'data/facets.json')
    with open(facets_file, 'r') as f:
        facets = json.loads(f.read())['facets']
    return jsonify(facets)
