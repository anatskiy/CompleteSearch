import os
import csv
import pandas as pd
import subprocess

from flask import Blueprint, request, current_app as app, jsonify

bp = Blueprint('upload', __name__)


@bp.route('/upload_file/', methods=['POST'])
def upload_file():
    """
    Upload a file, validate and process it, and "feed" it to CompleteSearch.
    """
    settings = app.settings.to_dict()
    dialect = None
    error = ''

    try:
        if 'file' not in request.files:
            raise ValueError('You did not select any file.')

        csv_file = request.files['file']
        if not allowed_file(csv_file.filename):
            raise ValueError('Wrong file type.')

        # Read first three lines
        temp_lines = ''
        for _ in range(3):
            temp_lines += str(csv_file.readline(), 'utf-8') + '\n'
        csv_file.seek(0)

        if temp_lines == '\n\n\n':
            raise ValueError('The file is empty.')

        # Define the delimiter
        dialect = csv.Sniffer().sniff(
            temp_lines,
            delimiters=',;#$|\t',
        )

        data, facets_fields = process_csv(csv_file, dialect.delimiter)
        facets_fields_str = ','.join(facets_fields)
        all_fields = data.columns.values.tolist()
        all_fields_str = ','.join(all_fields)

        # Update settings
        settings['database_uploaded'] = True
        settings['all_fields'] = all_fields
        settings['facets'] = facets_fields
        settings['full_text'] = all_fields
        settings['show'] = facets_fields
        settings['filter'] = facets_fields
        app.settings.save()

        # Save the processed file
        data.to_csv(
            app.config['OUTPUT_PATH'],
            sep='\t',
            escapechar='\\',  # test this
            index=False
        )

        # Don't run this code with TestingConfig
        if not app.config['TESTING']:
            # TODO@me: define allow-multiple-items automatically
            opts = "--within-field-separator=';' " + \
                    '--full-text=%s ' % all_fields_str + \
                    '--allow-multiple-items=Autor ' + \
                    '--show=%s ' % facets_fields_str + \
                    '--filter=%s ' % facets_fields_str + \
                    '--facets=%s' % facets_fields_str

            command = 'make OPTIONS="%s" prepare_input' % opts

            # Directory with the Makefile
            os.chdir('../completesearch')

            # Generate necessary files
            output1, err1 = subprocess.Popen(
                [command],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).communicate()
            app.logger.debug('Prepare input:\n%s' % err1)

            # Start CompleteSearch server
            output2, err2 = subprocess.Popen(
                ['make start_server'],
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).communicate()
            app.logger.debug('Start CS server:\n%s' % output2)

    except (ValueError, csv.Error) as e:
        error = str(e)
        app.logger.exception(e)

    return jsonify(success=not error, error=error)


def allowed_file(filename):
    """ Check if a file type is allowed. """
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in app.config['ALLOWED_EXTENSIONS']


def process_csv(csv_file, delimiter):
    """ Check the uploaded file (skip bad rows) and define facets. """
    data = pd.read_csv(
        csv_file,
        delimiter=delimiter,
        error_bad_lines=False,
        dtype=object,
    )

    # Number of non-NaN rows in each column
    non_nan_rows = data.count()

    # Define good facets (columns which have more than one occurrence)
    facets = [
        column
        for column in data
        if data[column].value_counts().size < non_nan_rows[column]
    ]

    return data, facets
