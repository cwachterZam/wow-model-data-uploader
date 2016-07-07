# wow_uploader - Automates the nasty details of getting a model data extraction onto the site

## Prerequisites
You will need:

python (2.7.x)

requests (pip install requests...)

fabric (pip install fabric...)

Akamai credentials

VPN (i.e., wowhead server) access

(sudoers) permissions to change file permissions on that server


## Usage
This is a fab file (http://www.fabfile.org/) which has tasks to do all the needed tarring, untarring, uploading, permissions manipulation, cleanup, and Akamai cache invalidation. It also has metatasks for easily doing expected combinations of tasks.

The tasks are run in the usual (fabfile) way. You will typically have to pass in the location of your extraction using the standard fab argument passing syntax; the script will prompt you for any needed login type info.

The basic thing to know is the usage of the 'do_all' task which does everything:

```

FABFILE=/path/to/this/projects/fabfile.py
EXTRACTION_HOME=/wherever/your/model/extractor/dumped/stuff

fab -f $FABFILE do_all:where=$EXTRACTION_HOME

```
