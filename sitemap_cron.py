# local
import sitemap
import config
from raven import Client
from github_connection import GH


client = Client(config.SENTRY_URL)


def sitemap_cron():
    gh = GH(config.GH_LOGIN)
    txt = gh.get_humans_text()

    with open(config.HUMANS_PRODUCTION_FILE, "w") as text_file:
        text_file.write(txt)

    # 1. fix up robots.txt and site-index.xml (remove system-region)
    # robots.txt and sitemap-index.xml published at midnight,
    with open(config.ROBOTS_FILE) as file:
        lines = file.read().splitlines()
    with open(config.ROBOTS_PRODUCTION_FILE, 'w') as file:
        file.write("\n".join(lines))

    try:
        sitemap.sitemap()
    except:
        client.captureException()

    # # 2. Move the new sitemap to replace the old one. Can't replace the old one right away
    # # because it is a generator, so it would be incomplete while it runs.
    # with open(config.SITEMAP_INDEX_PRODUCTION_FILE, 'w') as file:
    #     file.write("\n".join(lines))
    with open(config.SITEMAP_FILE) as file:
        lines = file.read().splitlines()
    with open(config.SITEMAP_PRODUCTION_FILE, 'w') as file:
        file.write("\n".join(lines))


# This is used by cron to create the sitemap
sitemap_cron()
