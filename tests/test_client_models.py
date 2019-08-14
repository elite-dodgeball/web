"""
.. module:: test_models
   :platform: Unix
   :synopsis: Unit tests for models

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

from django.test import TestCase

from client import models

class ContactTests(TestCase):
	""" Test case for Contact model

	"""
	def test_str(self):
		""" Test string representation of a Contact model

		"""
		co = models.Contact(
			name='asdf', email='asdf@qwer.com',
			subject='zxcv', body='body text', date_created='now')
		self.assertEqual(str(co), 'asdf - zxcv (now)')
