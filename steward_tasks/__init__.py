""" Steward tool for running tasks """
import logging.config

class InternalAdminAuthPolicy(object):
    """
    Specialized auth policy for internal requests

    This allows us to make calls to Steward, from Steward with admin privileges

    """
    def __init__(self, token):
        self._token = token

    def authenticated_userid(self, request):
        """ Return the authenticated userid or ``None`` if no
        authenticated userid can be found. This method of the policy
        should ensure that a record exists in whatever persistent store is
        used related to the user (the user should not have been deleted);
        if a record associated with the current id does not exist in a
        persistent store, it should return ``None``."""
        if request.cookies.get('__token', None) == self._token:
            return 'admin'

    def unauthenticated_userid(self, request):
        """ Return the *unauthenticated* userid.  This method performs the
        same duty as ``authenticated_userid`` but is permitted to return the
        userid based only on data present in the request; it needn't (and
        shouldn't) check any persistent store to ensure that the user record
        related to the request userid exists."""
        if request.cookies.get('__token', None) == self._token:
            return 'admin'

    def effective_principals(self, request):
        """ Return a sequence representing the effective principals
        including the userid and any groups belonged to by the current
        user, including 'system' groups such as
        ``pyramid.security.Everyone`` and
        ``pyramid.security.Authenticated``. """
        if request.cookies.get('__token', None) == self._token:
            return ['admin']
        return []

    def remember(self, request, principal, **kw):
        """ Return a set of headers suitable for 'remembering' the
        principal named ``principal`` when set in a response.  An
        individual authentication policy and its consumers can decide
        on the composition and meaning of **kw. """
        return []

    def forget(self, request):
        """ Return a set of headers suitable for 'forgetting' the
        current user on subsequent requests. """
        return []


def includeme(config):
    """ Configure the app """
    settings = config.get_settings()
    config.add_authentication_policy(InternalAdminAuthPolicy(
        settings['tasks.token']))

def main():
    """ Start running Steward tasks """
    import argparse
    from ConfigParser import ConfigParser
    import importlib
    import yaml
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('config_uri', help='The same ini file used by the '
            'Steward server')
    args = vars(parser.parse_args())

    config = ConfigParser(defaults={
        'tasks.pool_size': '10',
    })
    config.read(args['config_uri'])
    log_config = config.get('app:steward', 'tasks.log_config')

    with open(log_config, 'r') as infile:
        logging.config.dictConfig(yaml.load(infile))

    from .tasks import TaskList
    tasklist = TaskList(config)
    includes = config.get('app:steward', 'pyramid.includes').split()
    for package in includes:
        mod = importlib.import_module(package)
        if hasattr(mod, 'include_tasks'):
            mod.include_tasks(config, tasklist)

    tasklist.run()
