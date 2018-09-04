from flask import Flask, render_template, request
# TODO Can this be removed once the library is properly loaded?
from github import Github
# TODO Can this be removed once the library is properly loaded?
import re
import os
# FIXME Do this here
# from github_cff_extractor import GitHubCffGuesser

app = Flask(__name__)
app.config.from_object(__name__)


@app.teardown_appcontext
def tear_down(error):
    print("Tearing down app context.")


@app.route('/')
def show_form():
    # FIXME: This needs to be replaced with something useful, like a blank form
    cff = get_blank()
    return render_template('show_entries.html', cff=cff)


def get_blank():
    """
    This method returns an empty CFF dictionary,
    """
    cff = {'cff_version': '',
           'message': '',
           'authors': [{'given_names': '', 'family_names': ''}, {'name': ''}],
           'title': '',
           'version': '',
           'date_released': '',
           'repository_code': '',
           'commit': ''}
    return cff


@app.route('/', methods=['POST'])
def get_url():
    """
    TODO
    """
    repo = request.form['githuburl']
    cff = get_cff(repo)
    return render_template('show_entries.html', cff=cff)


# FIXME Introduce null checks and exclude fields if they're null
@app.route('/add', methods=['POST'])
def add_entry():
    """
    TODO
    """
    message = request.form['message']
    entity_authors = request.form.getlist('entity_author')
    authorsfn = request.form.getlist('author_fn')
    authorsgn = request.form.getlist('author_gn')

    title = request.form['title']
    version = request.form['version']
    date_released = request.form['date_released']
    repository_code = request.form['repository_code']
    commit = request.form['commit']
    # Build string
    s = "cff-version: 1.0.3\n"
    s = s + "message: " + message + "\n"
    s = s + "authors: " + "\n"
    for idx, val in enumerate(authorsfn):
        s = s + "  - family-names: " + val + "\n"
        s = s + "    given-names: " + authorsgn[idx] + "\n"
    for entity in entity_authors:
        s = s + "  - name: " + entity + "\n"
    s = s + "title: " + title + "\n"
    s = s + "version: " + version + "\n"
    s = s + "date-released: " + date_released + "\n"
    s = s + "repository-code: " + repository_code + "\n"
    s = s + "commit: " + commit + "\n"
    r = app.response_class(s, mimetype='text/plain')
    # Add the attachment header
    r.headers.set('Content-Disposition', 'attachment', filename='CITATION.cff')
    return r


def get_cff(repourl):
    # TODO Add URL check so that indices don't break
    split = repourl.split("/")
    input_username = str(split[3])
    input_reponame = str(split[4])

    # Read GitHub personal access token from local file called
    # auth_token.txt in the app root dir.
    # FIXME HIGHLY UNSAFE!
    app_root = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(app_root, 'auth_token.txt'), 'r') as tokenfile:
        token = tokenfile.readline()
    github = Github(token)
    user = github.get_user(input_username)
    repo = user.get_repo(input_reponame)
    github2cff = GitHubCffGuesser(repo)
    cff = github2cff.as_dict()
    return cff


class GitHubCffGuesser:
    """
    This class extracts (guesses?) CFF metadata from a Github repository
    object.
    """

    def __init__(self, repo):
        self.repo = repo
        self.parsed = None

    def run(self):
        """
        This method performs the data extraction, storing the results within
        this Object.

        There's no real need to call this explicitly as it will be called lazily
        via output methods.
        """
        result = dict()
        result['title'] = self.repo.name
        result['authors'] = self._extract_contributors()
        self._extract_release_info(result)
        self.parsed = result

    def _extract_release_info(self, result):
        """
        This tries to extract data from the best possible release information.
        """
        releases = list(self.repo.get_releases())
        tags = list(self.repo.get_tags())
        if len(releases):
            # Take most recent release
            latest_release = releases[0]
            result['version'] = latest_release.tag_name
            result['date_released'] = self.to_cff_date(latest_release.created_at)
        elif len(tags):
            # Take most recent tag
            latest_tag = tags[0]
            result['version'] = latest_tag.name
            result['date_released'] = self.to_cff_date(latest_tag.commit.commit.author.date)
        else:
            # No tags yet, so we'll take the last commit on the default branch
            branch = repo.get_branch(repo.default_branch)
            result['version'] = branch.commit.sha
            result['date_released'] = self.to_cff_date(branch.commit.commit.author.date)

    def _parse_human_name(self, name):
        """
        Attempts to parse a human name from GitHub, returning a 2-item tuple

        FIXME: This does not work for people like Neil Chue Hong...!
        """
        words = re.split(r'\s+', name)
        if len(words) == 1 and name.count('.') == 1:
            # Looks like a firstname.lastname person
            return name.split('.')
        else:
            return ' '.join(words[0:-1]), words[-1]

    def _extract_contributors(self):
        """
        Extracts contributor information from this repository
        """
        result = []
        for contributor in self.repo.get_contributors():
            name = contributor.name
            if contributor.type == 'User':
                # This is a real person
                first, last = self._parse_human_name(name)
                result.append({
                    'family_names': last,
                    'given_names': first,
                })
            else:
                # It's an organisation (I think...)
                result.append({
                    'name': name
                })
        return result

    def to_cff_date(self, datetime):
        """
        Transforms a GitHub YYYY-MM-DD HH:MM:SS into a CFF date string
        """
        return str(datetime)[0:10]

    def _ensure_run(self):
        if not self.parsed:
            self.run()

    def as_dict(self):
        """
        Returns a dictionary of extracted CFF metadata.

        Keys agree with the names in CFF, except that '-' characters have
        been converted to '_'.
        """
        self._ensure_run()
        return self.parsed

    def to_cff_string(self):
        """
        This returns a CFF string representation of the parsed data
        """
        parsed = self.as_dict()
        return '''
cff-version: 1.0.3
message: If you use this software, please cite it as below.
title: {title}
version: {version}
{authors_formatted}date-released: {date_released}
repository-code: {repo_url}'''.format(
            title=parsed['title'],
            version=parsed['version'],
            authors_formatted=self._format_authors(),
            date_released=parsed['release_date'],
            repo_url=self.repo.html_url,
                   )

    def _format_authors(self):
        formatted_items = []
        for a in self.as_dict()['authors']:
            if 'name' in a:
                # It's an organisation
                formatted_items.append('  - name: {}\n'.format(
                    a['name']))
            else:
                # It's a person
                formatted_items.append(
                    '  - family-names: {}\n    given-names: {}\n'.format(
                        a['family_names'], a['given_names']))
        return 'authors:\n' + ''.join(formatted_items)


# Example code
if __name__ == '__main__':
    # TODO: These would normally be user-selectable inputs
    input_username = 'codemeta'
    input_reponame = 'codemeta'

    # This has releases + a newer tag!
    # Here we'd expect to take the last release rather than the last branch
    #input_username = 'citation-file-to_cff_string'
    #input_reponame = 'cff-converter-python'

    # This has no releases, but lots of tags
    #input_username = 'davemckain'
    #input_reponame = 'jacomax'

    # This has no releases, no tags, just a branch
    #input_username = 'davemckain'
    #input_reponame = 'asciimath-parser'

    github = Github(auth_token)
    user = github.get_user(input_username)
    repo = user.get_repo(input_reponame)
    github2cff = GitHubCffGuesser(repo)
    print(github2cff.to_cff_string())
