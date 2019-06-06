"""
.. module:: serializer
   :platform: Unix
   :synopsis: Base serializer class

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

import re

from django.db.models.query import QuerySet

class Serializer(object):
	type_match = re.compile(r'^<\w+ \'(?:\w+\.)*(\w+)\'>$')

	@staticmethod
	def object_to_method(data):
		groups = Serializer.type_match.match(str(type(data))).groups()

		if len(groups) < 1:
			return None

		class_name = groups[0]
		method_name = class_name[0].lower()

		for letter in class_name[1:]:
			method_name += '_%s' % letter.lower() if letter.isupper() else letter

		return method_name

	@classmethod
	def serialize(cls, data):
		if isinstance(data, dict):
			return {key: cls.serialize(value) for key, value in data.items()}
		elif isinstance(data, (list, tuple, QuerySet)):
			return [cls.serialize(datum) for datum in data]

		method_name = cls.object_to_method(data)

		try:
			return getattr(cls, method_name)(data)
		except AttributeError:
			return None
