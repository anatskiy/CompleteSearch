from http.client import RemoteDisconnected

from flask import Blueprint, request, current_app as app, jsonify

from urllib.request import urlopen
from urllib.error import URLError
import json

bp = Blueprint('search', __name__)


@bp.route('/get_facets_list/', methods=['GET'])
def get_facets_list():
    """ Return the list of facets. """
    settings = app.settings.to_dict()
    facets_list = [{'name': facet} for facet in settings['facets']]
    return jsonify(facets_list)


@bp.route('/get_facets/', methods=['GET'])
def get_facets():
    """ Return all facets for a given field name. """
    error = ''
    facets = []
    completions = None

    name = request.args.get('name', '')
    if name != '':
        query = ':facet:%s:' % name
        url = 'http://0.0.0.0:8888/?q=%s*&format=json' % query

        try:
            response = urlopen(url)
            content = str(response.read(), 'utf-8').replace('\r\n', '')
            result = json.loads(content)['result']
            completions = result['completions']
        except (URLError, RemoteDisconnected) as e:
            error = 'CompleteSearch server is not running or responding.'
            app.logger.exception(e)
    else:
        error = 'Search query is empty.'

    # status = result['status']['@code']  # TODO@me: check status
    if error == '' and completions and int(completions['@total']) > 0:
        facets = [{
            # TODO@me: strip, trim and filter js/html code
            'name': c['text'].replace(query, ''),
            'count': c['@oc'],
        } for c in completions['c']]

    return jsonify(facets)


@bp.route('/search/', methods=['GET'])
def search():
    """ Perform search using CompleteSearch. """
    error = ''
    data = []
    settings = app.settings.to_dict()

    query = request.args.get('query')
    url = 'http://0.0.0.0:8888/?q=%s&format=json' % query

    try:
        response = urlopen(url)
        content = str(response.read(), 'utf-8').replace('\r\n', '')
        result = json.loads(content)['result']
        hits = result['hits']

        if int(hits['@total']) > 0:
            for hit in result['hits']['hit']:
                fields = [
                    {
                        'name': field,
                        'value':
                            hit['info'][field]
                            if field in hit['info'].keys()
                            else ''
                    }
                    for field in settings['show']
                ]

                hit_data = {
                    'titleField': settings['title_field'],
                    'fields': fields
                }

                data.append(hit_data)

        # XML response
        # root = ET.fromstring(content)
        # hits = root.find('hits')
        #
        # for hit in hits.iter('hit'):
        #     info = hit.find('info').text
        #     # excerpt = hit.find('excerpt').text
        #     data.append({
        #        'title': ET.fromstring(info).text,
        #        'description': '...'
        #     })

    except Exception as e:
        if e.__class__ == URLError:
            error = 'CompleteSearch server is not running or responding.'
        else:
            error = str(e)
        app.logger.exception(e)

    return jsonify({
        'success': not error,
        'error': error,
        'data': data
    })
