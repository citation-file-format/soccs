# soccs

"Software Citation Central Station" - prototype for a CFF-based [Flask](http://flask.pocoo.org/) app.

Current status: *very* early prototype, not functional.

Development on this had started at the [SSI Collaborations Workshop 2018](https://software.ac.uk/cw18)
hackathon.

To run, add a GitHub Personal Access token to a file called `auth_token.txt` and
place that in the app root (`./cffapp/`).

Also, run `export FLASK_APP=./cffapp/cffapp.py`, and then `flask run`.