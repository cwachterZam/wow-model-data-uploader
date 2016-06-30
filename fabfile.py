import os

from fabric.api import local, lcd, cd, env, run, put, task, sudo

env.hosts = ['static02b.wowhead.com']
REMOTE_ROOT = '/data01/www/static/modelviewer'


def where_vaildate(where):
    assert os.path.isdir(where)


@task
def generic_package(what, where):
    where_vaildate(where)
    with lcd(where):
        local('tar -czf {t} {w}'.format(t='{w}.tar.gz'.format(w=what), w=what))


@task
def generic_upload(what, where):
    where_vaildate(where)
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
    where_vaildate(where)
    with cd(REMOTE_ROOT):
        run('rm -fv {t}'.format(t='{w}.tar.gz'.format(w=what)))
    with lcd(where):
        local('rm -fv {t}'.format(t='{w}.tar.gz'.format(w=what)))


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


@task
def do_all(where):
    do_meta(where)
    do_mo3(where)
    do_textures(where)
