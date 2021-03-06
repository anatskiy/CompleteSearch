import json
import subprocess

from flask import Blueprint, request, current_app as app, jsonify

bp = Blueprint('settings', __name__)


@bp.route('/get_settings/', methods=['GET'])
def get_settings():
    """
    GET /get_settings/
        Get a dictionary with all dataset settings.

    :returns: dictionary with dataset settings, e.g. facet/filter fields,
        which fields to use for the full-text search, etc.

    :rtype: JSON response
    """
    settings = app.settings.to_dict()

    data = {
        'title_field': settings['title_field'],
        'within_field_separator': settings['within_field_separator'],
        'all_fields': settings['all_fields'],
        'allow_multiple_items': settings['allow_multiple_items'],
        'facets': settings['facets'],
        'filter': settings['filter'],
        'full_text': settings['full_text'],
        'show': settings['show'],
    }

    return jsonify(data)


@bp.route('/configure_dataset/', methods=['POST'])
def configure_dataset():
    """
    POST /configure_dataset/
        Change dataset parameters and regenerate CompleteSearch's indices.

    :param title_field: which field to use as a hit's title

    :param allow_multiple_items: fields containing multiple terms per column,
        e.g. several authors per one document

    :param within_field_separator: a delimiter which is used in
        ``allow_multiple_items``

    :param full_text: which columns should be searched

    :param show: which fields should be returned on a hit

    :param filter: search in a specific column

    :param facets: restrict the search to specific columns and phrases

    :returns: dictionary with the ``success`` property and an ``error`` message

    :rtype: JSON response
    """
    settings = app.settings.to_dict()
    error = ''

    try:
        if not request.data:
            raise ValueError('Data is missing.')

        params = json.loads(str(request.data, 'utf-8'))

        if not params['full_text'] and not params['show']:
            raise ValueError('At least one field must be selected in both ' +
                             'Full Text and Show')

        settings.update(params)
        settings['within_field_separator'] = params['within_field_separator'] \
            if params['within_field_separator'] != '' else ';'
        app.settings.save()

        # Don't run this code with TestingConfig
        if not app.config['TESTING']:
            full_text = ','.join(settings['full_text'])
            allow_multiple_items = ','.join(settings['allow_multiple_items'])
            within_field_separator = settings['within_field_separator']
            show = ','.join(settings['show'])
            filters = ','.join(settings['filter'])
            facets = ','.join(settings['facets'])

            opts = '--within-field-separator=\\%s ' % \
                   within_field_separator + \
                   '--full-text=%s ' % full_text + \
                   '--allow-multiple-items=%s ' % allow_multiple_items + \
                   '--show=%s ' % show + \
                   '--filter=%s ' % filters + \
                   '--facets=%s' % facets

            command = 'make OPTIONS="%s" process_input start' % opts

            # Process the input
            out, err = subprocess.Popen(
                [command],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).communicate()

            cmd_error = str(err, 'utf-8')
            if '[process_input] Error' in cmd_error:
                app.settings.reset()
                app.logger.debug('[Process input]:\n%s' % cmd_error)
                errors = set()
                for err_line in cmd_error.split('\n'):
                    if err_line != '' and not err_line.startswith('make') \
                            and not err_line.startswith('sort'):
                        errors.add(err_line)
                error = '<br/>'.join(list(errors))
                error += '<br/><strong>Please re-upload the dataset.</strong>'

    except Exception as e:
        error = str(e)
        app.logger.exception(e)

    return jsonify(success=not error, error=error)


@bp.route('/delete_dataset/', methods=['POST'])
def delete_dataset():
    """
    POST /delete_dataset/
        Reset app's settings, delete the uploaded dataset and stop the
        CompleteSearch server.

    :returns: dictionary with the ``success`` property

    :rtype: JSON response
    """
    app.settings.reset()
    subprocess.Popen(['make stop pclean-all'], shell=True).communicate()
    return jsonify(success=True)
