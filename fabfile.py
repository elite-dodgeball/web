"""
.. module:: fabfile
   :platform: Unix
   :synopsis: Functions for Fabric

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

from fabric import api
from fabric import context_managers

REPO_DIRECTORY = '/home5/elitedod/elite/'
FCGI_DIRECTORY = '/home5/elitedod/public_html/'
STATIC_DIRECTORY = '/home5/elitedod/public_html/beta/static/'

def deploy(do_tests=False):
	""" Wrangle up code deployment

	:param do_tests: Whether to run tests
	:type do_tests: bool

	"""
	if do_tests:
		run_tests()

	git_pull()
	pip_install()
	copy_static()
	update_database()
	touch_cgi()

def git_pull(remote='origin', branch='master'):
	""" Pull in git code

	:param remote: Remote name to pull from
	:type remote: str
	:param branch: Branch name to pull
	:type branch: str

	"""
	if not isinstance(remote, basestring):
		raise TypeError('Remote name must be a string')
	if not isinstance(branch, basestring):
		raise TypeError('Branch name must be a string')

	print 'PULLING {remote} {branch}'.format(remote=remote, branch=branch)
	with api.cd(REPO_DIRECTORY):
		api.run('git pull {remote} {branch}'.format(remote=remote, branch=branch))

def pip_install(req_file='requirements.txt', env='env'):
	""" Run pip install to update requirements

	:param req_file: Requirements file to install against
	:type req_file: str
	:param env: virtualenv directory
	:type env: str

	"""
	if not isinstance(req_file, basestring):
		raise TypeError('Requirements file must be a string')
	if not isinstance(env, basestring):
		raise TypeError('virtualenv source must be a string')

	print 'PIP INSTALLING {req_file}'.format(req_file=req_file)
	with api.cd(REPO_DIRECTORY):
		with context_managers.prefix('source {env}/bin/activate'.format(env=env)):
			api.run('pip install -r {req_file}').format(req_file=req_file)

def copy_static(source='static'):
	""" Copy static assets to the CDN directory

	:param source: Static source directory
	:type source: str

	"""
	if not isinstance(source, basestring):
		raise TypeError('Source directory must be a string')

	print 'COPYING {source} to {destination}'.format(source=source, destination=STATIC_DIRECTORY)
	with api.cd(REPO_DIRECTORY):
		api.run('cp -ru {source}/* {destination}'.format(
			source=source, destination=STATIC_DIRECTORY))

def update_database(env='env'):
	""" Synchronize the database with the codebase

	:param env: virtualenv directory
	:type env: str

	"""
	if not isinstance(env, basestring):
		raise TypeError('virtualenv source must be a string')

	print 'UPDATING DATABASE in {env}'.format(env=env)
	with api.cd(REPO_DIRECTORY):
		with context_managers.prefix('source {env}/bin/activate'.format(env=env)):
			api.run('python manage.py syncdb')

def touch_cgi(cgi_file='mysite.fcgi'):
	""" Touch the CGI file to force updated processing

	:param cgi_file: The file to touch
	:type cgi_file: str

	"""
	if not isinstance(cgi_file, basestring):
		raise TypeError('CGI file must be a string')

	print 'TOUCHING {directory}{cgi_file}'.format(directory=FCGI_DIRECTORY, cgi_file=cgi_file)
	with api.cd(FCGI_DIRECTORY):
		api.run('touch {cgi_file}'.format(cgi_file=cgi_file))

def run_tests(test_directory='tests/', env='env'):
	""" Run tests

	:param test_directory: Directory where the tests live
	:type test_directory: str
	:param env: virtualenv directory
	:type env: str

	"""
	if not isinstance(test_directory, basestring):
		raise TypeError('Test directory must be a string')

	print 'TESTING {test_directory}'.format(test_directory=test_directory)
	with api.cd(REPO_DIRECTORY):
		with context_managers.prefix('source {env}/bin/activate'.format(env=env)):
			api.run('python manage.py test {test_directory}'.format(test_directory=test_directory))

def host_type():
	api.run('uname -s')

def python_version():
	with api.cd(REPO_DIRECTORY):
		with context_managers.prefix('source env/bin/activate'):
			api.run('python --version')
