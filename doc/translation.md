From: https://pythonhosted.org/Flask-Babel/

Translating Applications¶

First you need to mark all the strings you want to translate in your application with gettext() or ngettext(). After that, it’s time to create a .pot file. A .pot file contains all the strings and is the template for a .po file which contains the translated strings. Babel can do all that for you.

First of all you have to get into the folder where you have your application and create a mapping file. For typical Flask applications, this is what you want in there:

[python: **.py]
[jinja2: **/templates/**.html]
extensions=jinja2.ext.autoescape,jinja2.ext.with_

Save it as babel.cfg or something similar next to your application. Then it’s time to run the pybabel command that comes with Babel to extract your strings:

$ pybabel extract -F babel.cfg -o messages.pot .

If you are using the lazy_gettext() function you should tell pybabel that it should also look for such function calls:

$ pybabel extract -F babel.cfg -k lazy_gettext -o messages.pot .

If you get an Error: "pybabel: error: no input files or directories specified"
Add the following Parameter to extract call " --input-dirs=."

This will use the mapping from the babel.cfg file and store the generated template in messages.pot. Now we can create the first translation. For example to translate to German use this command:

$ pybabel init -i messages.pot -d translations -l de

-d translations tells pybabel to store the translations in this folder. This is where Flask-Babel will look for translations. Put it next to your template folder.

Now edit the translations/de/LC_MESSAGES/messages.po file as needed. Check out some gettext tutorials if you feel lost.

To compile the translations for use, pybabel helps again:

$ pybabel compile -d translations

What if the strings change? Create a new messages.pot like above and then let pybabel merge the changes:

$ pybabel update -i messages.pot -d translations

Afterwards some strings might be marked as fuzzy (where it tried to figure out if a translation matched a changed key). If you have fuzzy entries, make sure to check them by hand and remove the fuzzy flag before compiling.

Language gets selected on Request Header: Accept-Language

