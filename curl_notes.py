#!/usr/bin/env python

import argparse
import configparser
import glob
import os
import re
import requests
import subprocess

from jinja2 import Environment
from jinja2.loaders import FileSystemLoader
from bs4 import BeautifulSoup
from weasyprint import HTML, CSS

import lxml


class Configuration:
    def __init__(self, config_file):
        self.working_dir = os.path.dirname(os.path.realpath(__file__))

        config = configparser.ConfigParser()
        config.read(config_file)

        for name, value in config.items('defaults'):
            setattr(self, name, value)

        self.notes_dir = os.path.abspath(os.path.expanduser(self.notes_dir))
        self.output_dir = os.path.join(self.notes_dir, self.output_dir)
        self.jinja_env = Environment(loader=FileSystemLoader(self.jinja_env))
        self.jinja_template = self.jinja_env.get_template(self.jinja_template)
        self.css_file = os.path.join(self.working_dir, self.css_file)
        self.pdf_style = CSS(filename=self.css_file)
        self.landscape_style = CSS(string=self.landscape_style)


def convert_title(filename):
    path, _ = os.path.splitext(os.path.basename(filename))
    return re.sub('_', ' ', path).title()


def to_str(string):
    if isinstance(string, bytes):
        return string.decode('utf-8')
    else:
        return string


def get_modified_md_files(notes_dir):
    # git diff --name-only $(git log -n 1 --pretty=format:%H -- pdfs)
    # HEAD~ | grep \.md
    last_modified = to_str(subprocess.check_output(
        ['git', 'log', '-n', '1', '--pretty=format:%H', '--', 'pdfs'],
        cwd=notes_dir
    ).strip())
    all_modified_glob = subprocess.check_output(
        ['git', 'diff', '--name-only', last_modified, 'HEAD~'],
        cwd=notes_dir
    )
    all_modified = [to_str(filename)
                    for filename in all_modified_glob.splitlines()]

    return [filename for filename in all_modified
            if os.path.splitext(filename)[1] == '.md']


def get_all_md_files(notes_dir):
    notes_glob = notes_dir + '/**/*.md'
    return glob.iglob(notes_glob, recursive=True)


def get_notes_files(notes_dir, update_all=False, filters=('README', 'TODOS')):
    if update_all:
        md_files = get_all_md_files(notes_dir)
    else:
        md_files = get_modified_md_files(notes_dir)

    return [filename for filename in md_files
            if all(elem not in filename for elem in filters)]


def curl_markup_for_file(relative_filename, git_url):
    request = requests.get(git_url + relative_filename)
    if request.status_code != 200:
        raise Exception
    parsed_contents = BeautifulSoup(request.content, 'lxml')
    return parsed_contents.find('article', {'class': 'markdown-body'})


def generate_markup_from_template(title, markup, jinja_template):
    return BeautifulSoup(
        jinja_template.render(title=title, article=markup), 'lxml'
    ).prettify()


def write_pdf(
        note_file,
        markup,
        config
):
    basename = os.path.basename(note_file)
    root, _ = os.path.splitext(os.path.basename(note_file))
    output_file = os.path.join(config.output_dir, root + '.pdf')

    stylesheets = [config.pdf_style]
    if basename in getattr(config, 'landscape_files', []):
        stylesheets.append(config.landscape_style)

    HTML(string=markup).write_pdf(output_file, stylesheets=stylesheets)


def main():
    config_file = 'config.ini'
    config = Configuration(config_file)

    parser = argparse.ArgumentParser(
        description='Update PDFs in the programming_notes repo'
    )
    parser.add_argument(
        '--all',
        type=bool,
        default=False,
        help='update all PDFs (default is to only update PDFs with '
             'corresponding modified .md files'
    )
    args = vars(parser.parse_args())
    for note_file in get_notes_files(config.notes_dir, args['all']):
        markdown = curl_markup_for_file(note_file, getattr(config, 'git_url'))
        title = convert_title(note_file)
        full_markdown = generate_markup_from_template(
            title,
            markdown,
            config.jinja_template
        )
        write_pdf(
            note_file,
            full_markdown,
            config
        )


if __name__ == '__main__':
    main()
