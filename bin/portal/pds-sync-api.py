# encoding: utf-8
#
#
# Sync ESA PSA products to Search API by first downloading their XML files
#
# Usage:
#
# python3 -m venv .venv
# . .venv/bin/activate
# pip install --quiet --requirement requirements.txt
# python3 bin/portal/pds-sync-api.py


import logging, argparse, requests, os, hashlib, urllib
from typing import Generator
from lxml import etree
from http import HTTPStatus


PDS_XSD_URL = 'https://github.com/NASA-PDS/harvest/blob/main/src/main/resources/conf/configuration.xsd'
PROD_SEARCH_API_URL = 'https://pds.mcp.nasa.gov/api/search/1/products'
XML_SCHEMA_INSTANCE_URI = 'http://www.w3.org/2001/XMLSchema-instance'
NS_MAP = {'xsi': XML_SCHEMA_INSTANCE_URI}

_logger = logging.getLogger(__name__)
_search_key = 'ops:Harvest_Info.ops:harvest_date_time'
_query_page_size = 50
_psa_query = '(product_class eq "Product_Context" and ops:Harvest_Info.ops:node_name like "PSA")'
_bufsiz = 512


def _get_lidvid(product: dict) -> str:
    '''Get the LIDVID from a `product`.'''
    try:
        return product['properties']['lidvid']
    except KeyError:
        return product['id']


def _get_esa_psa_products(url: str) -> Generator[str, str, None]:
    '''Query the ESA PSA ("easy peasy") products from the registry.'''
    params = {'sort': _search_key, 'limit': _query_page_size, 'q': _psa_query}
    _logger.info('Generating ESA-PSA products from %s', url)
    while True:
        _logger.debug('Making request to %s with params %r', url, params)
        r = requests.get(url, params=params)
        matches = r.json()["data"]
        num_matches = len(matches)
        for i in matches:
            yield i
        if num_matches < _query_page_size:
            break
        params["search-after"] = matches[-1]["properties"][_search_key]


def _write_harvest_config(node_name: str, download_path: str, config: str):
    '''Create the harvest config file.'''
    root = etree.Element(
        'harvest', nsmap=NS_MAP,
        attrib={f'{{{XML_SCHEMA_INSTANCE_URI}}}schemaLocation': PDS_XSD_URL},
    )
    download_path = os.path.abspath(download_path)
    etree.SubElement(root, 'registry', auth='/path/to/auth/file').text = 'app://localhost.xml'
    load = etree.SubElement(root, 'load')
    dirs = etree.SubElement(load, 'directories')
    etree.SubElement(dirs, 'path').text = download_path
    file_info = etree.SubElement(root, 'fileInfo', processDataFiles='true', storeLabels='true')
    attrs = {'replacePrefix': download_path, 'with': 'https://url/to/archive'}
    etree.SubElement(file_info, 'fileRef', attrib=attrs)
    etree.SubElement(root, 'autoGenFields')
    _logger.info('Writing harvest XML config to %s', config)
    etree.ElementTree(root).write(config, pretty_print=True, xml_declaration=True, encoding='UTF-8')


def _exists_in_registry(lidvid: str, url: str) -> bool:
    '''Tell (true or false) if the given `lidvid` exists in the registry at `url`.'''
    _logger.debug('Checking if lidvid %s is already in the registry', lidvid)
    url = f'{url}{lidvid}'
    response = requests.head(url)
    if response.status_code == HTTPStatus.OK:
        return True
    elif response.status_code == HTTPStatus.NOT_FOUND:
        return False
    else:
        raise ValueError(f'Unexpected {response.status_code} while checking for existence of {lidvid}')


def _already_downloaded(label_file: str, md5: str) -> bool:
    '''Tell if we've downloaded the `label_file` or not.

    Return True if it exists and it has the expected `md5`; false otherwise.
    '''
    _logger.debug('Checking if label file %s is already intact', label_file)
    if os.path.isfile(label_file):
        digest = hashlib.md5(usedforsecurity=False)
        with open(label_file, 'rb') as io:
            while buf := io.read(_bufsiz):
                digest.update(buf)
        return digest.hexdigest() == md5
    return False


def _download(product: dict, download_path: str):
    '''Download the XML label for the given `product` to `download_path`.

    Note that this'll skip labels that have already been downloaded.
    '''
    props = product['properties']
    label_url, md5 = props['ops:Label_File_Info.ops:file_ref'][0], props['ops:Label_File_Info.ops:md5_checksum'][0]
    label_file = os.path.join(download_path, urllib.parse.urlparse(label_url).path[1:])
    if _already_downloaded(label_file, md5):
        _logger.debug("Already downloaded %s and it's intact, so skipping it", label_file)
        return

    _logger.debug('Downloading label %s', label_url)
    response = requests.get(label_url)
    if response.status_code != HTTPStatus.OK:
        _logger.warning('Unexpected status %d while trying to download %s; skipping', response.status_code, label_url)
        return
    os.makedirs(os.path.dirname(label_file), exist_ok=True)
    with open(label_file, 'wb') as io:
        for buf in response.iter_content(chunk_size=_bufsiz):
            io.write(buf)


def _download_labels(download_path: str, url: str):
    '''Query the API at `url` and create matching XML labels in `download_path`.

    This follows Jordan's algorithm in NASA-PDS/registry-legacy-solr#135, namely:

    1.  Check if the lidvid is in the registry already
    2.  If not, check if we already downloaded an XML file for in in `download_path`
        -   Use the filename and ops:Label_File_Info.ops:md5_checksum
    3.  If not, then download to `download_path`
    '''
    _logger.info('Downloading labels from %s to %s', url, download_path)
    for product in _get_esa_psa_products(url):
        lidvid = _get_lidvid(product)
        if _exists_in_registry(lidvid, url): continue
        _download(product, download_path)


def easy_peasy(node_name: str, download_path: str, url: str, config: str):
    '''Download ESA-PSA ("easy peasy") harvest XML files and a harvest cfg file.'''
    _logger.debug('Making output directory %s as needed', download_path)
    os.makedirs(download_path, exist_ok=True)

    _write_harvest_config(node_name, download_path, config)    
    _download_labels(download_path, url)


def main():
    '''Here we go.'''
    parser = argparse.ArgumentParser(description='Download ESA PSA product XML files from search API')
    parser.add_argument(
        '-n', '--node-name', default='psa', help='Name of the node (default %(default)s)'
    )
    parser.add_argument(
        '-p', '--download-path', default='download', help='Where to create the XML files (default %(default)s)'
    )
    parser.add_argument(
        '-u', '--url', default=PROD_SEARCH_API_URL, help='URL of the PDS product search API (default %(default)s)',
    )
    parser.add_argument(
        '-c', '--config', default='harvest.cfg',
        help='What to call the harvest XML config output (default %(default)s)'
    )
    args = parser.parse_args()

    # If this were a "real program", we'd let logging be configurable
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')

    # The PDS API is really finicky about trailing slashes
    url = args.url[0:-1] if args.url.endswith('/') else args.url

    easy_peasy(args.node_name, args.download_path, url, args.config)


if __name__ == '__main__':
    main()
