# https://github.com/NASA-PDS/operations/issues/378
# enhance PDS sitemap with data set landing page URLs (results for ds-view)
# written May 2023 by csuh (with minor contributions by kelly)
from datetime import datetime
from git import Repo
import os
import requests
import time
import previous_run
import logging
import shutil
import pathlib


increment_slash_number_of_rows = 1000
total_number_of_docs = None
parsed_response = {}
repo_path = os.environ.get('HTDOCS_HOME')
target = os.path.join(repo_path, 'sitemap.xml')
_logger = logging.getLogger(__name__)


def do_git_stuff():
    """Move the new sitemap to the repo. Update timestamp of local, partial
    sitemap. (In that order.) Then do git stuff.
    """
    _logger.info('Moving complete sitemap to repository')

    # Subprocess-free "mv"
    if os.path.isfile(target):
        os.remove(target)
    shutil.move('sitemap.xml', repo_path)

    # Subprocess-free "touch"
    partial = pathlib.Path('sitemap-partial.xml')
    partial.touch()

    # Get the repository and see if we need to do anything
    repo = Repo(repo_path)
    if not repo.is_dirty():
        _logger.info('The %s repo is currently clean, so no updates to commit',
                     repo_path)
        return

    # Okay, the repository has unstaged files… is the sitemap one of them?
    changed = [i.a_path for i in repo.index.diff(None)]
    if 'sitemap.xml' not in changed:
        _logger.info('The sitemap.xml hasn\'t been updated this time, '
                     'so no changes to commit')
        return

    # Can't use the `add` API provided by GitPython since it doesn't support
    # the version of the repository in /data/www/pds/htdocs; but it does
    # provide a "git" object that calls `git` directly
    _logger.info('Committing and pushing changes to sitemap.xml')
    git = repo.git
    git.add('sitemap.xml')
    git.commit('-m', 'Sitemap updated with PDS products')
    git.push()


def write_parsed_response():
    """Append parsed response to copy of partial sitemap.
    """
    _logger.info('Appending results to make a complete sitemap')

    # Subprocess-free "copy"
    shutil.copy('sitemap-partial.xml', 'sitemap.xml')

    with open('sitemap.xml', 'a') as writer:
        for location, lastmod in parsed_response.items():
            writer.write('  <url>\n')
            writer.write(f'    <loc>{location}</loc>\n')
            if lastmod is not None:
                writer.write(f'    <lastmod>{lastmod}</lastmod>\n')
            writer.write('  </url>\n')
        writer.write('</urlset>\n')


def delete_last_line(w):
    """Delete last line of a file and leave a newline

    :param w: file writer
    """
    pos = w.tell() - 1
    while pos > 0 and w.read(1) != '\n':
        pos -= 1
        w.seek(pos, os.SEEK_SET)
    if pos > 0:
        w.seek(pos, os.SEEK_SET)
        w.truncate()
        w.write('\n')


def recreate_partial_sitemap(recreate_callback):
    """Recreate local, partial sitemap from repository's full sitemap.
    Sitemap is partial in that it has existing ds-view URLs removed. Closing
    `urlset` tag is also removed.

    :param recreate_callback: after this function is complete, calls
    `write_parsed_response` to append the new ds-view URLs
    """
    # Subprocess-free "copy"?
    shutil.copy(target, os.getcwd())

    with open('sitemap.xml', 'r') as reader:
        # There are already some ds-view results in the sitemap
        # e.g. https://pds.nasa.gov/ds-view/pds/viewCollection.jsp?identifier=urn%3Anasa%3Apds%3Amaven.lpw.raw%3Adata.act&amp;version=2.5
        # The URL specifies an older version while the page reflects the
        # (supposably) most recent version. The query returns the (supposably)
        # most recent version --> delete these from the sitemap; the query
        # results have the latest version
        ds_view_item = False
        with open('sitemap-partial.xml', 'r+') as writer:
            for line in reader:
                if 'https://pds.nasa.gov/ds-view' in line:
                    ds_view_item = True
                if not ds_view_item:
                    writer.write(line)
                else:
                    if '<url>' in line:
                        ds_view_item = False
            delete_last_line(writer)

    recreate_callback()


def get_file_modification_time(filepath):
    """Get a file's modification time

    :param filepath:
    :return: seconds between epoch and file modification time.
    bigger number = more recently modified. float.
    """
    modified_file = pathlib.Path(filepath)
    return modified_file.stat().st_mtime


def was_repo_sitemap_modified():
    """Compare modification timestamps of local, partial sitemap to
    repository's full sitemap. If repository's sitemap timestamp is longer (
    more recent), it has been modified since this script was last run and
    the local, partial sitemap must be recreated.

    :return: True if repository sitemap has been modified since this script
    was last run. False if otherwise. boolean
    """
    repo_sitemap_modification_time = get_file_modification_time(target)
    local_sitemap_modification_time = \
        get_file_modification_time('sitemap-partial.xml')

    if repo_sitemap_modification_time < local_sitemap_modification_time:
        _logger.info('Repository\'s sitemap hasn\'t changed since last run. '
                     'Continuing from the existing local, partial sitemap.')
        return False
    else:
        _logger.info('Repository\'s sitemap has changed since last run. '
                     'Recreating the local, partial sitemap.')
        return True


def prepare_to_write_parsed_response(write_callback):
    """Check if repository's sitemap has been modified since this script was
    last run. If yes, recreate the local, partial sitemap before writing the
    parsed response to create the full sitemap. If no, proceed directly to
    writing the parsed response to create the full sitemap.

    :param write_callback: after this function is complete, calls
    `do_git_stuff` for last steps
    """
    if was_repo_sitemap_modified():
        recreate_partial_sitemap(write_parsed_response)
    else:
        write_parsed_response()

    write_callback()


def convert_string_to_date(timestamp_string):
    """Convert given timestamp string into a date

    :param timestamp_string:
    :return: date object
    """
    return datetime.strptime(timestamp_string, '%Y-%m-%dT%H:%M:%SZ').date()


def get_most_recent_lastmod_date(list_of_lastmod_dates):
    """Find most recent modification_date from list of string dates from a
    single response doc

    :param list_of_lastmod_dates: list of strings
    :return: max (aka most recent) modification_date as date object
    """
    date_objects = []
    for lastmod_date in list_of_lastmod_dates:
        date_objects.append(convert_string_to_date(lastmod_date))

    return max(date_objects)


def parse_response(list_of_docs):
    """Parse list of json objects from the query's response. Look for
    `resLocation` and most recent `modification_date`, which can have multiple
    dates. Ignore values of `resLocation` that are not from PDS site,
    e.g. https://archives.esac.esa.int/psa/pdap/metadata?DATA_SET_ID=MEX-M-MRS-1/2/3-PRM-0430-V1.0&RETURN_TYPE=HTML

    :param list_of_docs: query's json response's `docs`
    """
    for doc in list_of_docs:
        if doc['resLocation'].startswith('/ds-view'):
            location = 'https://pds.nasa.gov' + doc['resLocation'].replace(
                '&', '&amp;')
            if 'modification_date' not in doc:
                parsed_response[location] = None
            else:
                if len(doc['modification_date']) == 1:
                    parsed_response[location] = \
                        convert_string_to_date(doc['modification_date'][0])
                else:
                    parsed_response[location] = \
                        get_most_recent_lastmod_date(doc['modification_date'])


def set_total_number_of_docs(number):
    """Set global variable, `total_number_of_docs`, which determines when to
    stop querying. Also, overwrite this variable inside previous_run.py to
    reference for the next script run.

    :param number: query's json response's `numFound`. integer
    """
    global total_number_of_docs
    total_number_of_docs = number

    with open('previous_run.py', 'w') as writer:
        writer.write(f'total_number_of_docs = {number}\n')


def run_script_after_x_minutes(x):
    """Wait x number of minutes before running the script again. Used in the
    case of a requests exception or if the data is being re-indexed.

    :param x: number of minutes to wait before re-running the script. integer.
    """
    time.sleep(60 * x)
    do_query_and_parse_response(0, check_if_more_queries)


def compare_totals(current_total):
    """Compare the total number of results (aka docs) between the current
    script run and the last time the script was run. If the current total is
    less than the previous total, the data is being re-indexed.

    :param current_total: current number of results (aka docs). integer
    """
    _logger.info(f'This run\'s numFound is {current_total}')
    _logger.info(f'Last run\'s numFound is {previous_run.total_number_of_docs}')

    if current_total < previous_run.total_number_of_docs:
        run_script_after_x_minutes(60)
    else:
        set_total_number_of_docs(current_total)


def set_and_get_query_parameters(start_number):
    """Set `start` parameter and get rest of the query parameters

    :param start_number: for `start` parameter of query. integer
    :return: query parameters
    """
    return {
        'wt': 'json',
        'q': 'product_class:Product_Collection '
             'OR product_class:Product_Bundle '
             'OR product_class:Product_Data_Set_PDS3 '
             'OR product_class:Product_Document',
        'fl': 'resLocation,modification_date',
        'rows': increment_slash_number_of_rows,
        'start': start_number
    }


def do_query_with(start_number, query_callback):
    """Run query with specified number for the `start` parameter

    :param start_number: for `start` parameter of query. integer
    :param query_callback: after this function is complete, calls
    `parse_response` with the query's response
    """
    search_url = 'https://pds.nasa.gov/services/search/search'
    query_parameters = set_and_get_query_parameters(start_number)

    try:
        # ignoring responseHeader
        json_response = requests.get(search_url,
                                     params=query_parameters).json()['response']

        # This happens only with very first query. I am not tying it to
        # "start=0" in case we want that to be variable
        if total_number_of_docs is None:
            compare_totals(json_response['numFound'])

        query_callback(json_response['docs'])
    except requests.exceptions.Timeout:
        run_script_after_x_minutes(30)
    except requests.exceptions.RequestException as e:
        raise SystemExit(e)
        # TODO: send email notification?


def check_if_more_queries(new_start_parameter_value):
    """Check against global variable `total_number_of_docs` for more queries.
    If yes there's more, run them. If no, write parsed responses to XML format.

    :param new_start_parameter_value: the already-used `start` parameter plus
    the programmer-defined increment. integer
    """
    if new_start_parameter_value < total_number_of_docs:
        do_query_and_parse_response(new_start_parameter_value,
                                    check_if_more_queries)
    else:
        prepare_to_write_parsed_response(do_git_stuff)


def do_query_and_parse_response(start_parameter_value, looped_callback):
    """Run query then parse its json response

    :param start_parameter_value: the `start` parameter of the query. integer
    :param looped_callback: after this function is complete, calls
    `check_if_more_queries`, which calls this if needed
    """
    do_query_with(start_parameter_value, parse_response)

    looped_callback(start_parameter_value + increment_slash_number_of_rows)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    _logger.info(f'=== Starting update of sitemap.xml with ds-view pages on '
                 f'{datetime.now().strftime("%a %b %d, %Y at %H:%M:%S")}')
    do_query_and_parse_response(0, check_if_more_queries)
