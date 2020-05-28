# !/opt/tinker/env/bin/python
# python
import os.path
import logging
import re
import requests
from datetime import date, datetime, timedelta

# local
import config

import sentry_sdk
from sentry_sdk import configure_scope
from bu_cascade.cascade_connector import Cascade
from bu_cascade.asset_tools import find

hidden_pages = ""
hidden_folders = ""

if config.SENTRY_URL:
    from sentry_sdk.integrations.flask import FlaskIntegration
    sentry_sdk.init(dsn=config.SENTRY_URL, integrations=[FlaskIntegration()])

# todo Add logic for index pages

cascade_api = Cascade(config.SOAP_URL, config.CASCADE_LOGIN, config.SITE_ID, config.STAGING_DESTINATION_ID)


# Just putting this here to work on it. Move out of tinker once the Cascade stuff is more portable
def inspect_folder(folder_id):
    global hidden_folders
    folder = cascade_api.read(folder_id, asset_type="folder")
    if not folder:
        # typically a permision denied error from the Web Services read call.
        return
    try:
        md = folder['asset']['folder']['metadata']['dynamicFields']
        path = folder['asset']['folder']['path']
    except KeyError:
        # folder has been deleted
        return
    md = get_md_dict(md)

    if 'hide-from-sitemap' in list(md.keys()) and md['hide-from-sitemap'] == "Hide":
        hidden_folders = hidden_folders + ("https://www.bethel.edu/" + path + ",")
        return

    if 'require-authentication' in list(md.keys()) and md['require-authentication'] == "Yes":
        return

    # This block of code is used to skip any OLD event folders that are 2+ years old. We check more specifically in the
    # inspect_page function for events that are 1.5 years or older.
    folder_path = folder['asset']['folder']['path']
    split_folder = folder_path.split('/')
    cutoff_date = datetime.now() - timedelta(weeks=78)
    if split_folder[0] == 'events':
        try:
            # we except on this, as the ValueError is when non year folder names are used
            if (split_folder and len(split_folder) == 2 and int(split_folder[1]) <= int(cutoff_date.year)):
                return

            if len(split_folder) == 4 and ('events/arts/music/' in folder_path or 'events/arts/theatre/' in folder_path):
                if (int(split_folder[3]) <= int(cutoff_date.year)):
                    return
        except ValueError:
            pass

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

    # This block of code is used to check if event is older than a year and a half, based on the most recent event's end date.
    cutoff_date = (datetime.now() - timedelta(weeks=78)).timestamp() * 1000  # multiply by 1000 to fix it for cascade
    content_type_path = page['asset']['page']['contentTypePath']
    if content_type_path == 'Event':
        event_dates = find(page, 'event-dates')
        if isinstance(event_dates, list):
            event_dates = event_dates[-1]
        date_to_check = find(event_dates, 'end-date', False)
        if not date_to_check:
            date_to_check = find(event_dates, 'start-date', False)

        # if the event date is before the cutoff date, return
        if int(date_to_check) <= cutoff_date:
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


# Takes in a string containing the hidden files and folders and splits them based on commas.
# Writes them to the corresponding production and non-production .txt files from config
def hidden_files():
    hidden = hidden_pages.split(",")
    with open(config.HIDDEN_PAGES_FILE, 'w') as file:
        file.write("\n".join(hidden))
    with open(config.HIDDEN_PAGES_PRODUCTION_FILE, 'w') as file:
        file.write("\n".join(hidden))

    hidden = hidden_folders.split(",")
    with open(config.HIDDEN_FOLDERS_FILE, 'w') as file:
        file.write("\n".join(hidden))
    with open(config.HIDDEN_FOLDERS_PRODUCTION_FILE, 'w') as file:
        file.write("\n".join(hidden))


hidden_files()
