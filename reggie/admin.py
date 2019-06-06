"""
.. module:: admin
   :platform: Unix
   :synopsis: ModelAdmin registration

.. moduleauthor:: Tim <tim@elite-dodgeball.com>

"""

from django.contrib import admin
from django.urls import path

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from reggie import models as reggie

@admin.register(reggie.Invite)
class InviteAdmin(admin.ModelAdmin):
	readonly_fields = (
		'date_created',
	)
	list_display = (
		'id',
		'event',
		'team',
		'date_created',
	)
	ordering = [
		'-event__datetime',
		'event__title',
		'team',
	]
	search_fields = [
		'event__title',
		'team',
	]
	list_select_related = (
		'event',
		'team',
	)

	def team(self, obj):
		return obj.season_division_team.team.name

	def get_urls(self):
		return [
			path('<uuid:invite_id>/sender/', self.sender, name='reggie_invite_sender'),
		] + super(InviteAdmin, self).get_urls()

	@csrf_exempt
	def sender(self, request, invite_id):
		if request.method == 'POST':
			if not request.POST.get('emailAddress'):
				return JsonResponse({'success': False, 'message': 'POST payload is missing emailAddress attribute'}, status=400)

			try:
				invite = reggie.Invite.objects.select_related('event', 'team').get(pk=invite_id)
			except reggie.Invite.DoesNotExist:
				return JsonResponse({'success': False, 'message': 'Invite does not exist'}, status=404)

			email_body = invite.send_email(email_address=request.POST.get('emailAddress'))

			return JsonResponse({'success': True, 'message': email_body})

		return JsonResponse({'success': False, 'message': '%s is not allowed' % request.method}, status=405)

@admin.register(reggie.DivisionInvite)
class DivisionInviteAdmin(admin.ModelAdmin):
	list_display = (
		'division',
		'invite',
		'discount',
		'is_claimed',
	)
	ordering = [
		'-invite__event__datetime',
		'invite__event__title',
		'division__name',
	]
	search_fields = [
		'division__name',
		'invite__event__title',
		'invite__team__name',
	]
	list_select_related = (
		'invite',
		'division',
	)

	def event(self, obj):
		return obj.event_division.event.title
