# !/opt/tinker/env/bin/python
# python
import os.path
import logging
import re
import requests
from datetime import date

# Packages
from github_connection import GH
from paramiko import RSAKey, SFTPClient, Transport
from paramiko.hostkeys import HostKeyEntry

# local
from web_services import *
import config

from raven import Client

client = Client(config.SENTRY_URL)

# todo Add logic for index pages


# Just putting this here to work on it. Move out of tinker once the Cascade stuff is more portable
def inspect_folder(folder_id):
    folder = read(folder_id, type="folder")
    if not folder:
        # typically a permision denied error from the Web Services read call.
        return
    try:
        md = folder.asset.folder.metadata.dynamicFields
    except AttributeError:
        # folder has been deleted
        return
    md = get_md_dict(md)

    if 'hide-from-sitemap' in md.keys() and md['hide-from-sitemap'] == "Hide":
        return

    if 'require-authentication' in md.keys() and md['require-authentication'] == "Yes":
        return

    children = folder.asset.folder.children
    if not children:
        logging.info("folder has no children %s" % folder.asset.folder.path)
        yield
    else:
        for child in children['child']:
            if child['type'] == 'page':
                for item in inspect_page(child['id']):
                    yield item
            elif child['type'] == 'folder':
                logging.info("looking in folder %s" % child.path.path)
                for item in inspect_folder(child['id']):
                    yield item


def get_md_dict(md):
    data = {}
    if not md:
        return data
    for field in md.dynamicField:
        try:
            data[field.name] = field.fieldValues.fieldValue[0].value
        except:
            data[field.name] = None
    return data


def inspect_page(page_id):
    page = None
    for i in range(1, 10):
        try:
            page = read(page_id)
            break
        except:
            i += 1

    if not page:
        return

    try:
        md = page.asset.page.metadata.dynamicFields
        md = get_md_dict(md)
        path = page.asset.page.path

        if 'hide-from-sitemap' in md.keys() and md['hide-from-sitemap'] == "Hide":
            return

        if 'require-authentication' in md.keys() and md['require-authentication'] == "Yes":
            return

    except AttributeError:
        # page was deleted
        if 'You do not have read permissions for the requested asset' in page.message:
            return
        else:
            client.captureException()
            return

    # check for index page
    if path.endswith('index'):
        path = path.replace('index', '')

    # We know its published to prod on the filesystem, but does the page not return 200?
    r = requests.get('https://www.bethel.edu/%s' % path, allow_redirects=False)
    if r.status_code != 200:
        if r.status_code == 302:
            # just checks auth, doesn't require, so don't alert
            return
        # from sitemap_cron import log_sentry
        # log_sentry("Page in Cascade does not return 200: %s (%s)" % (path, str(r.status_code)))
        return


    # todo check for location, events in the past have lower priority.

    ret = ["<url>"]
    ret.append("<loc>https://www.bethel.edu/%s</loc>" % path)
    date = page.asset.page.lastModifiedDate

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
                client.extra_context({
                    'base_folder': base_folder,
                    'item': item,
                })
                client.captureMessage("Failed to write item to sitemap. Typically from bad unicode in path.")
                client.captureException()

        file.write('</urlset>')

    gh = GH(config.GH_LOGIN)
    txt = gh.get_humans_text()

    with open(config.HUMANS_FILE, "w") as text_file:
        text_file.write(txt)

    write_files_to_sftp()


def write_files_to_sftp():
    try:
        ssh_key_object = RSAKey(filename=config.SFTP_SSH_KEY_PATH,
                                password=config.SFTP_SSH_KEY_PASSPHRASE)

        remote_server_public_key = HostKeyEntry.from_line(config.SFTP_REMOTE_HOST_PUBLIC_KEY).key
        # This will throw a warning, but the (string, int) tuple will automatically be parsed into a Socket object
        remote_server = Transport((config.SFTP_REMOTE_HOST, 22))
        remote_server.connect(hostkey=remote_server_public_key, username=config.SFTP_USERNAME, pkey=ssh_key_object)

        sftp = SFTPClient.from_transport(remote_server)

        # Because of how SFTP is set up on wlp-fn2187, all these paths will be automatically prefixed with /var/www
        sftp.put(config.SITEMAP_FILE, 'cms.pub/sitemap.xml')
        sftp.put(config.ROBOTS_FILE, 'cms.pub/robots.txt')
        sftp.put(config.HUMANS_FILE, 'cms.pub/humans.txt')

        return 'SFTP publish of redirects.txt succeeded'
    except:
        return 'SFTP publish of redirects.txt failed'
