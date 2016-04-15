from github import Github
from jinja2 import Template

template = """/* TEAM */
{% for member in members %}{% if member['name'] %}{{ member['name'] }}{% else %}{{ member['login'] }}{% endif %}
{% endfor %}

/* SITE */
Bethel University
https://www.bethel.edu
Language: English
Twitter: @BethelU
"""


class GH:
    def __init__(self, login):
        self.username = login[0]
        self.password = login[1]
        self.g = Github(self.username, self.password)
        self.organization = self.g.get_organization("betheluniversity")

    def get_members(self):
        list_of_members = list(self.organization.get_members())
        member_list = []
        for member in list_of_members:
            member_list.append({'login': member.login, 'name': member.name})
        return member_list

    def get_humans_text(self):
        members = self.get_members()
        t = Template(template)
        return t.render(members=members)