Elite Dodgeball
===============

New homepage design for [Elite Dodgeball](http://www.elite-dodgeball.com/).

## Running Locally

The big assumption is that you're on OSX. If not, you'll need to instal MySQL and Python 3.5 (we need at least 3.5.2 because of `channels-redis`).

### Setup

Start your local MySQL server.

```bash
$ mysql.server start
```

Install `pyenv`.

```bash
$ brew update
$ brew install pyenv
$ brew install pyenv-virtualenv
```

Create your Python environment.

```bash
$ pyenv install 3.5.2
$ pyenv virtualenv 3.5.2 elite
$ pip install -r requirements.txt
```

Update your `/elite/settings.py` values. (The `DATABASES['default']['HOST']` and `DATABASES['default']['PORT']` values are probably fine.)

```python
DEBUG = True

DATABASES = {
	'default': {
		'NAME': 'database-name',
		'USER': 'database-user',
		'PASSWORD': 'database-password',
	}
}

ANYMAIL = {
	'MAILGUN_API_KEY': 'api-key',
}

STRIPE_API_KEY = 'api-key'
```

Make sure your migrations are updated.

```bash
$ python manage.py migrate
```

Now run your debug server.

```bash
$ python manage.py runserver
```

## Running Tests

Django's `manage.py` helps us run tests located in the `/tests/` directory.

```bash
$ python manage.py test tests/
```

## Deploying to Production

We use [Fabric](http://www.fabfile.org/) to facilitate deployment.

```bash
$ fab deploy
```
