# !/opt/tinker/env/bin/python
# python
import os.path
import logging
import re
import requests
from datetime import date

# local
import config

import sentry_sdk
from sentry_sdk import configure_scope
from bu_cascade.cascade_connector import Cascade

hidden_pages = ""

if config.SENTRY_URL:
    from sentry_sdk.integrations.flask import FlaskIntegration
    sentry_sdk.init(dsn=config.SENTRY_URL, integrations=[FlaskIntegration()])

# todo Add logic for index pages

cascade_api = Cascade(config.SOAP_URL, config.CASCADE_LOGIN, config.SITE_ID, config.STAGING_DESTINATION_ID)


# Just putting this here to work on it. Move out of tinker once the Cascade stuff is more portable
def inspect_folder(folder_id):
    folder = cascade_api.read(folder_id, asset_type="folder")
    if not folder:
        # typically a permision denied error from the Web Services read call.
        return
    try:
        md = folder['asset']['folder']['metadata']['dynamicFields']
    except KeyError:
        # folder has been deleted
        return
    md = get_md_dict(md)

    if 'hide-from-sitemap' in list(md.keys()) and md['hide-from-sitemap'] == "Hide":
        return

    if 'require-authentication' in list(md.keys()) and md['require-authentication'] == "Yes":
        return

    if 'children' in folder['asset']['folder']:
        children = folder['asset']['folder']['children']
        for child in children['child']:
            if child['type'] == 'page':
                for item in inspect_page(child['id']):
                    yield item
            elif child['type'] == 'folder':
                logging.info("looking in folder %s" % child['path']['path'])
                for item in inspect_folder(child['id']):
                    yield item
    else:
        logging.info("folder has no children %s" % folder['asset']['folder'])
        yield


def get_md_dict(md):
    data = {}
    if not md:
        return data
    for field in md['dynamicField']:
        try:
            data[field['name']] = field['fieldValues']['fieldValue'][0]['value']
        except:
            data[field['name']] = None
    return data


def inspect_page(page_id):
    global hidden_pages
    page = None
    for i in range(1, 10):
        try:
            page = cascade_api.read(page_id, 'page')
            break
        except:
            i += 1

    if not page:
        return

    try:
        path = None
        md = page['asset']['page']['metadata']['dynamicFields']
        md = get_md_dict(md)
        path = page['asset']['page']['path']

        if 'hide-from-sitemap' in list(md.keys()) and md['hide-from-sitemap'] == "Hide":
            hidden_pages = hidden_pages + ("https://www.bethel.edu/" + path + ",")
            return

        if 'require-authentication' in list(md.keys()) and md['require-authentication'] == "Yes":
            return

    except (KeyError, AttributeError):
        # page was deleted or page is a draft
        if 'message' in page and ('You do not have read permissions for the requested asset' in page['message'] or 'No configuration could be found' in page['message']):
            return
        # I don't think we need to capture the exception. It doesn't do much for us.
        # else:
        #     client.captureException()
        return

    # Is this page currently published to production? TODO cleanup?
    if not os.path.exists('/var/www/cms.pub/%s.php' % path) and not config.TEST:
        return

    # check for index page
    try:
        if path.endswith('index'):
            path = path.replace('index', '')

    except:
        return

    # We know its published to prod on the filesystem, but does the page not return 200?
    r = requests.get('https://www.bethel.edu/%s' % path, allow_redirects=False)
    if r.status_code != 200:
        if r.status_code == 302 or r.status_code == 301:
            # just checks auth, doesn't require, so don't alert
            return
        # from sitemap_cron import log_sentry
        # log_sentry("Page in Cascade does not return 200: %s (%s)" % (path, str(r.status_code)))
        return


    # todo check for location, events in the past have lower priority.

    ret = ["<url>"]
    ret.append("<loc>https://www.bethel.edu/%s</loc>" % path)
    date = page['asset']['page']['lastModifiedDate']

    priority = None
    if "events" in path:
        priority = get_event_page_priority(path)

    if priority:
        ret.append("<priority>%s</priority>" % priority)

    ret.append("<lastmod>%02d-%02d-%02d</lastmod>" % (date.year, date.month, date.day))
    ret.append("</url>")
    yield "\n".join(ret)


def get_event_page_priority(path):
    try:
        search = re.search("events/.*(\d{4})", path)
        year = search.group(1)
        current_year = date.today().year
        if int(year) < current_year:
            return '0.2'
        return '0.7'
    except AttributeError:
        return None


def sitemap():
    base_folder = config.SITEMAP_BASE_FOLDER_ID
    with open(config.SITEMAP_FILE, 'w') as file:
        file.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        for item in inspect_folder(base_folder):
            try:
                if item:
                    file.write(item)
            except:
                with configure_scope() as scope:
                    scope.set_tag('base_folder', base_folder)
                    scope.set_tag('item', item)
                sentry_sdk.capture_message("Failed to write item to sitemap. Typically from bad unicode in path.")
                sentry_sdk.capture_exception()

        file.write('</urlset>')


sitemap()

# Takes in a string containing the hidden files and splits them based on commas.
# Writes them to HIDDEN_FILE and HIDDEN_PRODUCTION_FILE
def hidden_files():
    hidden = hidden_pages.split(",")
    with open(config.HIDDEN_FILE, 'w') as file:
        file.write("\n".join(hidden))
    with open(config.HIDDEN_PRODUCTION_FILE, 'w') as file:
        file.write("\n".join(hidden))


hidden_files()
