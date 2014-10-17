#!/opt/tinker/env/bin/python
#python
import os.path
import logging

#local
from web_services import *
import config

##todo Add logic for index pages

###Just putting this here to work on it. Move out of tinker once the Cascade stuff is more portable
def inspect_folder(folder_id):
    folder = read(folder_id, type="folder")
    if not folder:
        #typically a permision denied error from the Web Services read call.
        return
    md = folder.asset.folder.metadata.dynamicFields
    md = get_md_dict(md)
    if ('hide-from-sitemap' in md.keys() and md['hide-from-sitemap'] == "Do not hide") or 'hide-from-sitemap' not in md.keys():
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
    for i in range(1, 10):
        try:
            page = read(page_id)
            break
        except:
            i += 1

    md = page.asset.page.metadata.dynamicFields
    md = get_md_dict(md)
    if 'hide-from-sitemap' in md.keys() and md['hide-from-sitemap'] == "Hide":
        return
    path = page.asset.page.path

    ##Is this page currently published to production?
    if not os.path.exists('/var/www/cms.pub/%s.php' % path):
        return

    #check for index page
    if path.endswith('index'):
        path = path.replace('index', '')

    ret = ["<url>"]
    ret.append("<loc>https://www.bethel.edu/%s</loc>" % path)
    date = page.asset.page.lastModifiedDate

    ret.append("<lastmod>%s-%s-%s</lastmod>" % (date.year, date.month, date.day))
    ret.append("</url>")
    yield "\n".join(ret)


def sitemap():
    base_folder = config.SITEMAP_BASE_FOLDER_ID
    with open(config.SITEMAP_FILE, 'w') as file:
        file.write('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
        for item in inspect_folder(base_folder):
            if item:
                file.write(item)
        file.write('</urlset>')