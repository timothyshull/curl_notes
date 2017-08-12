#!/usr/bin/env python

import os
import glob
import re
import requests
from jinja2 import Environment
from jinja2.loaders import FileSystemLoader
from bs4 import BeautifulSoup
from weasyprint import HTML, CSS

import lxml

current_dir = os.path.dirname(os.path.realpath(__file__))
notes_dir = '/Users/tskull/Documents/Programming/Notes'
git_url = 'https://github.com/timothyshull/programming_notes/blob/master/'
output_dir = current_dir + '/notes/'
jinja_env = Environment(loader=FileSystemLoader(''))
jinja_template = jinja_env.get_template('template.html')
css_file = current_dir + '/github-markdown.css'
pdf_style = CSS(filename=css_file)
landscape = CSS(string='@media print{@page {size: landscape}}')


def convert_title(filename):
    return re.sub('_', ' ', filename).title()


def get_all_notes_files():
    global notes_dir
    notes_glob = notes_dir + '/**/*.md'
    all_files = glob.iglob(notes_glob, recursive=True)
    return [os.path.relpath(filename, notes_dir) for filename in all_files
            if 'README' not in filename and 'TODOS' not in filename]


def curl_markdown_for_file(relative_filename):
    global git_url
    request = requests.get(git_url + relative_filename)
    if request.status_code != 200:
        raise Exception
    parsed_contents = BeautifulSoup(request.content, 'lxml')
    return parsed_contents.find('article', {'class': 'markdown-body'})


def generate_markdown_from_template(title, markdown):
    return BeautifulSoup(jinja_template.render(title=title, article=markdown), 'lxml').prettify()


def write_markdown_file(note_file, markdown):
    global output_dir
    root, _ = os.path.splitext(os.path.basename(note_file))
    filename = output_dir + root + '.pdf'
    stylesheets = [pdf_style]
    if 'pseudo_code' in note_file:
        stylesheets.append(landscape)
    HTML(string=markdown).write_pdf(filename, stylesheets=stylesheets)


def main():
    all_notes = get_all_notes_files()
    for note_file in all_notes:
        markdown = curl_markdown_for_file(note_file)
        title = convert_title(note_file)
        full_markdown = generate_markdown_from_template(title, markdown)
        write_markdown_file(note_file, full_markdown)


if __name__ == '__main__':
    main()
