# ReXML
RElnotes to MW (probably should call it ReMW but I already started the project when I envisioned DITA not MW...)

Translate Release note output from Jira to MediaWiki markup/tables, at least...

Usage:

1. Have Python and Pip. If you don't yet, get it from [python.org](https://www.python.org/downloads/) then proceed to the next step.

1. From Terminal, validate your Python and Pip configuration:

```bash
% python --version
Python 3.12.0
% pip --version
pip 25.0 from /Library/Frameworks/Python.framework/Versions/3.12/lib/python3.12/site-packages/pip (python 3.12)
% 
```

Any versions should work. Once you've validated your set up by successfully checking versions, proceed to the next step.

3. Download this repo. Lots of ways to do this, including **Code > Download Zip** then extract.

4. From Terminal, install [pandas](https://pypi.org/project/pandas/) and [openai](https://pypi.org/project/openai/) by entering:

```bash
% pip install pandas
% pip install openai
```

You only must do this once; if you want to check whether you already have them, you could enter `pip show pandas` then `pip show openai` first.

5. Translate a specific jira file (named Jira.csv) file from your downloaded, extracted ReXML directory. In Terminal, from the directory containing prompt.py, enter:

```bash
% python3 prompt.py <Jira.csv>
```
To call openai and output its response as response.mw.

6. Because I'm burning thru tokens like kindling, you can also translate a specific jira file (named Jira.csv) file from the ReXML directory via an offline translator, no openai prompt/call. In Terminal, from the ReXML directory containing both prompt.py and Jira.csv, enter:

```bash
% python3 noprompt.py <Jira.csv>
```
To munge the csv to mw locally, no REST API, no tokens. Whether its any good or not is a good question. It outputs output.mw.
