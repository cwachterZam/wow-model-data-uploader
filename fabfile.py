import getpass
import json
import multiprocessing.dummy as dummy
import os
import requests
import sys
import time

from fabric.api import local, lcd, cd, env, run, put, task, sudo

env.hosts = ['static02b.wowhead.com']
REMOTE_ROOT = '/data01/www/static/modelviewer'
AKAMAI_ROOT = 'http://wow.zamimg.com/modelviewer'
MAX_THREADS = 1 # 8
RETRY_DELAY_IN_S = 30

def where_validate(where):
    where = os.path.expanduser(where)
    assert os.path.isdir(where)
    return where


@task
def generic_package(what, where):
    where = where_validate(where)
    with lcd(where):
        local('tar -czf {t} {w}'.format(t='{w}.tar.gz'.format(w=what), w=what))


@task
def generic_upload(what, where):
    where = where_validate(where)
    with lcd(where):
        with cd(REMOTE_ROOT):
            this = '{w}.tar.gz'.format(w=what)
            put(local_path=this, remote_path=this)


@task
def generic_update(what):
    with cd(REMOTE_ROOT):
        sudo('tar -xzf {t}'.format(t='{w}.tar.gz'.format(w=what)))
        sudo('chmod -R 775 {w}'.format(w=what))
        sudo('find {w} -type d -exec chmod 777 {{}} \;'.format(w=what))


@task
def generic_cleanup(what, where):
    where = where_validate(where)
    with cd(REMOTE_ROOT):
        run('rm -fv {t}'.format(t='{w}.tar.gz'.format(w=what)))
    with lcd(where):
        local('rm -fv {t}'.format(t='{w}.tar.gz'.format(w=what)))

@task
def akamai_purge(where, user=None, passwd=None):
    """
    Akamai hard limits:

    A single POST request: 50,000 bytes

    Maximum purge queue length: 10,000 pending URLs

    N.B.: For simplicity, this assumes that you want to invalidate every file in the local extraction.

    """
    if user is None and passwd is None:
        user, passwd = get_akamai_creds()

    MAX_CONTENT_SIZE = 45000
    where = where_validate(where)
    bins = []
    with lcd(where):
        output = local('find . -type f'.format(), capture=True)
        files = output.stdout.split()
        current_size = 0
        current_bin = []
        for f in files:
            full_f = '{r}/{f}'.format(r=AKAMAI_ROOT, f=f[2:])  # rm the './'
            if len(full_f) + current_size > MAX_CONTENT_SIZE:
                bins.append(current_bin)
                current_bin = []
                current_size = 0
            current_bin.append(full_f)
            current_size += len(full_f)

    pool = dummy.Pool(MAX_THREADS)
    results = pool.map(invalidate, [(b, user, passwd) for b in bins])
    pool.close()
    pool.join()

    nSuccesses = len([x for x in results if x == True])
    nFails = len([x for x in results if x == False])
    print("\n---------\nAkamai cache invalidation submission summary:\n\t{s} successful chunks, {f} unsuccessful chunks.\n".format(
        s=nSuccesses, f=nFails))


def invalidate(args):
    urls = args[0]
    user = args[1]
    passwd = args[2]
    endpoint = 'https://api.ccu.akamai.com/ccu/v2/queues/default'
    while True:
        r = requests.post(endpoint, auth=(user, passwd), json={'objects': urls, 'action': 'invalidate'})
        if r.status_code == 507:
            r2 = requests.get('https://api.ccu.akamai.com/ccu/v2/queues/default', auth=(user, passwd))
            backlog = r2.json()['queueLength']
            sys.stderr.write("[INFO] Akamai purge request pool is full ({n} items/max 10000); waiting...\n".format(
                n=backlog))
            sys.stderr.flush()
            time.sleep(RETRY_DELAY_IN_S)
            continue
        elif r.status_code == 401:
            sys.stderr.write("Request denied - unauthorized.")
            sys.stderr.flush()
            break
        elif r.status_code == 415:
            sys.stderr.write("Something(s) in the following chunk is/are not a valid purgeable? \
(WARN: The invalidation of this chunk failed - forging ahead.)\n{c}\n".format(c='\n'.join(urls)))
            sys.stderr.flush()
            break
        elif r.status_code == 201:
            when = r.json()['pingAfterSeconds']
            where = "https://api.ccu.akamai.com{s}".format(s=r.json()['progressUri'])
            sys.stdout.write("[INFO] Chunk accepted; you may check this URL for status {e}:\n\t{u}\n".format(
                e="in ~{t} seconds".format(t=when), u=where))
            sys.stdout.flush()
            return True
        else:
            break
    return False


def get_akamai_creds():
    u = getpass.getpass('Enter Akamai username:')
    p = getpass.getpass('Enter Akamai password:')
    return u, p


########


def do_everything(what, where):
    generic_package(what, where)
    generic_upload(what, where)
    generic_update(what)
    generic_cleanup(what, where)


@task
def do_meta(where):
    what = 'meta'
    do_everything(what, where)


@task
def do_mo3(where):
    what = 'mo3'
    do_everything(what, where)


@task
def do_textures(where):
    what = 'textures'
    do_everything(what, where)


#### Probably just want to do this (meta)task:


@task
def do_all(where):
    user, passwd = get_akamai_creds()
    do_meta(where)
    do_mo3(where)
    do_textures(where)
    akamai_purge(where, user=user, passwd=passwd)
