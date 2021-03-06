# -*- coding: utf-8 -*-

"""
    conpaas.core.git
    ================

    ConPaaS core: GIT support.

    :copyright: (C) 2010-2013 by Contrail Consortium.
"""

import os
import tempfile

from conpaas.core.misc import run_cmd

GIT_HOME           = "/home/git"
AUTH_KEYS_FILENAME = os.path.join(GIT_HOME, ".ssh", "authorized_keys")
DEFAULT_CODE_REPO  = os.path.join(GIT_HOME, "code")

def __filter_authorized_keys(keys):
    return [ k for k in keys if k and not k.startswith('#') ]

def get_authorized_keys():
    """Return the list of public keys contained in AUTH_KEYS_FILENAME"""
    authorized_keys = [ line.rstrip() for line in open(AUTH_KEYS_FILENAME) ]
    return __filter_authorized_keys(authorized_keys)

def add_authorized_keys(keys):
    """Add the public keys given in the 'keys' collection to authorized_keys. Do
    not insert the same key twice. Return the number of newly added keys."""
    new_auth_keys = [ key.rstrip() for key in __filter_authorized_keys(keys) ]
    cur_auth_keys = get_authorized_keys()

    added = 0
    for key in new_auth_keys:
        if key not in cur_auth_keys:
            authorized_keys = open(AUTH_KEYS_FILENAME, "a")
            authorized_keys.writelines([ key + "\n" ])
            authorized_keys.close()
            added += 1

    return added

def remove_authorized_keys(keys):
    """Remove the public keys given in the 'keys' collection from
    authorized_keys. Return the number of keys left in authorized_keys."""
    del_auth_keys = __filter_authorized_keys(keys)
    cur_auth_keys = get_authorized_keys()

    to_add_auth_keys = [ key + "\n" for key in cur_auth_keys 
        if key not in del_auth_keys ]

    authorized_keys = open(AUTH_KEYS_FILENAME, "w")
    authorized_keys.writelines(to_add_auth_keys)
    return len(to_add_auth_keys)

def git_push(repo, destination_ip):
    """Push repository contents to the given destination_ip"""
    cmd = 'git push git@%s:%s master' % (destination_ip, DEFAULT_CODE_REPO)
    return run_cmd(cmd, repo)

def git_create_tmp_repo():
    """Create a temporary git repository with a pseudo-random name.
    Return the repository absolute path as a string.

    This function is useful for automated testing purposes."""
    repo_path = tempfile.mkdtemp()

    cmd = 'git init %s' % repo_path
    run_cmd(cmd, repo_path)

    cmd = 'git add %s' % tempfile.mkstemp(dir=repo_path)[1]
    run_cmd(cmd, repo_path)

    cmd = 'git config user.email "info@conpaas.eu"'
    run_cmd(cmd, repo_path)

    cmd = 'git config user.name "ConPaaS"'
    run_cmd(cmd, repo_path)

    cmd = 'git commit -am "Initial commit"' 
    run_cmd(cmd, repo_path)

    return repo_path

def git_code_version(repo):
    """Get the abbreviated commit hash of the last commit performed in the
    specified repository.

    The return value is a string matching the following regular expression:

      /^[a-z0-9]{7,7}$/

    """
    cmd = 'git log -1 --pretty=oneline --format="%h"'
    res = run_cmd(cmd, repo)

    return res[0].rstrip()

def git_last_description(repo):
    """Return a string containing the subject line of the last commit performed
    in the specified repository."""
    cmd = 'git log -1 --pretty=oneline --format="%s"'
    return run_cmd(cmd, repo)[0].rstrip()

def git_enable_revision(target_dir, repo, rev):
    """This function clones a local git repository into target_dir/rev.
    It then performs a git-checkout of the specified revision.

    As an example, the following invocation:

      git_enable_revision("/var/www", "/home/git/code", "8d3b8a6")

    is roughly equivalent to these shell commands:

      git clone /home/git/code /var/www/8d3b8a6
      cd /var/www/8d3b8a6
      git checkout 8d3b8a6

    As a result, a directory is created containing the specified revision of the
    given repository, and its absolute pathname is returned as a string.
    """
    dest_dir = os.path.join(target_dir, rev)

    run_cmd(cmd='git clone %s %s' % (repo, rev), directory=target_dir)
    run_cmd(cmd='git checkout %s' % rev, directory=dest_dir)

    return dest_dir
