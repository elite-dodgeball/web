"""
.. module:: context_processors
   :platform: Unix
   :synopsis: Custom context processors

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

def global_vars(request):
	""" Add in some global variables

	:param request: The Django request object
	:type request: request
	:returns: dict

	"""
	return {
		'ANGULAR_VERSION': '1.7.6',
		'ANGULAR_MATERIAL_VERSION': '1.1.12',
		'DEFAULT_TITLE': 'This isn\'t gym class anymore',
		'DEFAULT_DESCRIPTION': 'An invitation-only dodgeball league hosting national tournaments at the highest level.',
		'CHAMPIONS_TITLE': 'Champions',
		'CHAMPIONS_DESCRIPTION': 'Elite Dodgeball\'s history of champions.',
		'CONTACT_TITLE': 'Contact',
		'CONTACT_DESCRIPTION': 'Make contact with Elite Dodgeball.',
		'EVENTS_TITLE': 'Events',
		'EVENTS_DESCRIPTION': 'Upcoming and past Elite Dodgeball events.',
		'GALLERIES_TITLE': 'Photo Galleries',
		'GALLERIES_DESCRIPTION': 'Photos of Elite Dodgeball events.',
		'HISTORY_TITLE': 'Our History',
		'HISTORY_DESCRIPTION': 'The history of Elite Dodgeball.',
		'LEADERSHIP_TITLE': 'Leadership',
		'LEADERSHIP_DESCRIPTION': 'The leadership council of Elite Dodgeball.',
		'MISSION_TITLE': 'Our Mission',
		'MISSION_DESCRIPTION': 'The Elite Dodgeball Invitational is a tournament for dodgeballers by dodgeballers.',
		'POSTS_TITLE': 'News',
		'POSTS_DESCRIPTION': 'Find all the up-to-date news about Elite Dodgeball.',
		'PRESS_TITLE': 'Press Coverage',
		'PRESS_DESCRIPTION': 'Read about Elite Dodgeball in the press.',
		'REFEREE_TITLE': 'Referee Guidelines',
		'REFEREE_DESCRIPTION': 'Be sure to officiate by the rules in Elite Dodgeball.',
		'REGULATIONS_TITLE': 'Regulations and Requirements',
		'REGULATIONS_DESCRIPTION': 'Be sure to participate by the rules in Elite Dodgeball.',
		'RULES_TITLE': 'Rules',
		'RULES_DESCRIPTION': 'Be sure to play by the rules in Elite Dodgeball.',
		'SCHEDULE_TITLE': 'Schedule',
		'SCHEDULE_DESCRIPTION': 'Check the calendar to see what Elite Dodgeball events are coming up.',
		'STORE_TITLE': 'Store',
		'STORE_DESCRIPTION': 'Purchase Elite Dodgeball branded goods and support the league.',
		'TEAMS_TITLE': 'Teams',
		'TEAMS_DESCRIPTION': 'The best teams in the country are the teams of Elite Dodgeball.',
		'VIDEOS_TITLE': 'Episodes',
		'VIDEOS_DESCRIPTION': 'Watch our teams duke it out to be the best of Elite Dodgeball.',
	}
