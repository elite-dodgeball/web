'use strict';

angular.module('DashboardApp', ['ngMaterial', 'ngMessages'], function ($interpolateProvider) {
	$interpolateProvider.startSymbol('[[');
	$interpolateProvider.endSymbol(']]');
}).controller('DashboardCtrl', function ($scope, $http, $q) {
	const API_PREFIX = '/dashboard/api';

	$scope.activeRequests = 0;

	$scope.teams = [];
	$scope.teamHash = {};

	$scope.players = [];
	$scope.playerHash = {};

	$scope.divisions = [];
	$scope.divisionHash = {};

	// view

	$scope.view = {
		selectedView: null,
		viewOptions: [
			{id: 0, name: 'Season', module: 'season', isDisabled: false},
			{id: 1, name: 'Event', module: 'event', isDisabled: false},
		],
		onChange: function () {
			$scope[$scope.view.selectedView.module].initialize();
		},
		initialize: function () {
			$scope.view.selectedView = $scope.view.viewOptions[0];
			$scope.view.onChange();
		},
	};

	// event

	$scope.event = {
		invites: [],
		inviteHash: {},

		eventOptions: [],
		selectedEvent: null,

		eventDivisions: [],
		eventDivisionHash: {},
		selectedEventDivision: null,

		eventDivisionTeams: [],
		eventDivisionTeamHash: {},

		seasonDivisionTeams: [],
		seasonDivisionTeamHash: {},

		activeEventDivisionTeam: null,
		activeSeasonDivisionTeamPlayers: [],

		activeDivisions: [],
		activeEmailAddress: '',
		activeSeasonDivisionTeam: null,

		addTeam: function (seasonDivisionTeam) {
			incrementRequests();

			return $http.post(`${API_PREFIX}/event_division_teams/`, {
				eventDivisionId: $scope.event.selectedEventDivision.id,
				seasonDivisionTeamId: seasonDivisionTeam.id,
			}).then(function (data) {
				var eventDivisionTeam = getData(data).event_division_team;

				$scope.event.eventDivisionTeams.push(eventDivisionTeam);
				$scope.event.eventDivisionTeamHash[eventDivisionTeam.season_division_team_id] = eventDivisionTeam;

				$scope.event.selectedEventDivision.team_count++;
			}, function (error) {
				console.log(error);
			}).finally(function () {
				decrementRequests();
			});
		},
		removeTeam: function (eventDivisionTeam) {
			incrementRequests();

			return $http.delete(`${API_PREFIX}/event_division_teams/${eventDivisionTeam.id}`).then(function (data) {
				$scope.event.selectedEventDivision.team_count--;

				for (var i = 0, l = $scope.event.eventDivisionTeams.length; i < l; i++) {
					if ($scope.event.eventDivisionTeams[i].id === eventDivisionTeam.id) {
						$scope.event.eventDivisionTeams.splice(i, 1);
						break;
					}
				}

				delete $scope.event.eventDivisionTeamHash[eventDivisionTeam.season_division_team_id];
			}, function (error) {
				console.log(error);
			}).finally(function () {
				decrementRequests();
			});
		},
		viewSeasonDivisionTeamInvites: function (seasonDivisionTeam) {
			incrementRequests();

			return $http.get(`${API_PREFIX}/seasons/${seasonDivisionTeam.season_id}/teams/${seasonDivisionTeam.team_id}/divisions/`).then(function (data) {
				$scope.event.activeEmailAddress = $scope.teamHash[seasonDivisionTeam.team_id].email_address;
				$scope.event.activeSeasonDivisionTeam = seasonDivisionTeam;

				$scope.event.activeDivisions = getData(data).divisions.reduce(function (accumulator, currentValue) {
					if (currentValue.id in $scope.event.eventDivisionHash) {
						accumulator.push($scope.divisionHash[currentValue.id]);
					}
					return accumulator;
				}, []);
			}).finally(function () {
				decrementRequests();
			});
		},
		clearSeasonDivisionTeamInvites: function () {
			$scope.event.activeDivisions = null;
			$scope.event.activeEmailAddress = null;
			$scope.event.activeSeasonDivisionTeam = null;
		},
		viewEventDivisionTeamPlayers: function (eventDivisionTeam) {
			incrementRequests();

			$q.all([
				$http.get(`${API_PREFIX}/season_division_teams/${eventDivisionTeam.season_division_team_id}/players/`),
				$http.get(`${API_PREFIX}/event_division_teams/${eventDivisionTeam.id}/players/`),
			]).then(function (data) {
				var seasonDivisionTeamPlayerHash = hashify(getData(data[0]).season_division_team_players);

				$scope.event.activeSeasonDivisionTeamPlayers = getData(data[1]).event_division_team_players.reduce(function (accumulator, currentValue) {
					if (currentValue.season_division_team_player_id in seasonDivisionTeamPlayerHash) {
						seasonDivisionTeamPlayerHash[currentValue.season_division_team_player_id].event_division_team_player = currentValue;
						accumulator.push(seasonDivisionTeamPlayerHash[currentValue.season_division_team_player_id]);
					}
					return accumulator;
				}, []);

				$scope.event.activeEventDivisionTeam = eventDivisionTeam;
			}).finally(function () {
				decrementRequests();
			});
		},
		clearEventDivisionTeamPlayers: function () {
			$scope.event.activeEventDivisionTeam = null;
			$scope.event.activeSeasonDivisionTeamPlayers = null;
		},
		sendEmail: function () {
			var invite = $scope.event.inviteHash[$scope.event.activeSeasonDivisionTeam.team_id];

			if (!invite || !$scope.event.activeEmailAddress) {
				return;
			}

			incrementRequests();

			return $http.post(`${API_PREFIX}/invites/${invite.id}/sender/`, {
				emailAddress: $scope.event.activeEmailAddress,
			}).then(function () {
				$scope.event.activeEmailAddress = '';
			}, function (error) {
				console.log(error);
			}).finally(function () {
				decrementRequests();
			});
		},
		inviteTeam: function (division) {
			var eventDivision = $scope.event.eventDivisionHash[division.id],
				discount = eventDivision.discount ? eventDivision.discount : 0,
				payload = {
					teamId: $scope.event.activeSeasonDivisionTeam.team_id,
					eventId: $scope.event.selectedEvent.id,
					divisionId: division.id,
					isClaimed: false,
					discount: discount,
				};

			incrementRequests();

			return $http.post(`${API_PREFIX}/division_invites/`, payload).then(function (data) {
				var invite = getData(data).invite,
					divisionInvite = getData(data).division_invite;

				if (payload.teamId in $scope.event.inviteHash === false) {
					$scope.event.inviteHash[payload.teamId] = invite;
				}

				if ('division_invites' in $scope.event.inviteHash[payload.teamId] === false) {
					invite.division_invites = [];
				}

				if ('divisionInviteHash' in $scope.event.inviteHash[payload.teamId] === false) {
					invite.divisionInviteHash = {};
				}

				$scope.event.inviteHash[payload.teamId].division_invites.push(divisionInvite);
				$scope.event.inviteHash[payload.teamId].divisionInviteHash[payload.divisionId] = divisionInvite;
			}, function (error) {
				console.log(error);
			}).finally(function () {
				decrementRequests();
			});
		},
		uninviteTeam: function (division) {
			var invite = $scope.event.inviteHash[$scope.event.activeSeasonDivisionTeam.team_id],
				divisionInvite = invite.divisionInviteHash[division.id];

			incrementRequests();

			return $http.delete(`${API_PREFIX}/division_invites/${divisionInvite.id}/`).then(function () {
				for (var i = 0, l = invite.division_invites.length; i < l; i++) {
					if (invite.division_invites[i].id === divisionInvite.id) {
						invite.division_invites.splice(i, 1);
						break;
					}
				}

				delete invite.divisionInviteHash[division.id];
			}, function (error) {
				console.log(error);
			}).finally(function () {
				decrementRequests();
			});
		},
		onEventDivisionChange: function () {
			incrementRequests();

			return $q.all([
				$http.get(`${API_PREFIX}/event_divisions/${$scope.event.selectedEventDivision.id}/season_division_teams/`),
				$http.get(`${API_PREFIX}/seasons/${$scope.event.selectedEvent.season}/divisions/${$scope.event.selectedEventDivision.division_id}/teams/`),
			]).then(function (data) {
				$scope.event.eventDivisionTeams = getData(data[0]).event_division_teams;
				$scope.event.eventDivisionTeamHash = hashify($scope.event.eventDivisionTeams, 'season_division_team_id');

				$scope.event.seasonDivisionTeams = getData(data[1]).season_division_teams;
				$scope.event.seasonDivisionTeamHash = hashify($scope.event.seasonDivisionTeams, 'id');
			}).finally(function () {
				decrementRequests();
			});
		},
		onEventChange: function () {
			incrementRequests();

			return $q.all([
				$http.get(`${API_PREFIX}/events/${$scope.event.selectedEvent.id}/divisions/`),
				$http.get(`${API_PREFIX}/events/${$scope.event.selectedEvent.id}/invites/`),
			]).then(function (data) {
				$scope.event.eventDivisions = getData(data[0]).event_divisions;
				$scope.event.eventDivisionHash = hashify($scope.event.eventDivisions, 'division_id');

				$scope.event.selectedEventDivision = $scope.event.eventDivisions[0];

				$scope.event.invites = getData(data[1]).invites;
				$scope.event.inviteHash = {};

				for (var i = 0, l = $scope.event.invites.length; i < l; i++) {
					$scope.event.invites[i].divisionInviteHash = {};
					$scope.event.inviteHash[$scope.event.invites[i].team_id] = $scope.event.invites[i];

					if ('division_invites' in $scope.event.invites[i] !== true) {
						continue;
					}

					for (var j = 0, k = $scope.event.invites[i].division_invites.length; j < k; j++) {
						$scope.event.invites[i].divisionInviteHash[$scope.event.invites[i].division_invites[j].division_id] = $scope.event.invites[i].division_invites[j];
					}
				}

				$scope.event.onEventDivisionChange();
			}).finally(function () {
				decrementRequests();
			});
		},
		initialize: function () {
			incrementRequests();

			return $http.get(`${API_PREFIX}/events/`).then(function (data) {
				$scope.event.eventOptions = getData(data).events;
				$scope.event.selectedEvent = $scope.event.eventOptions[0];

				$scope.event.onEventChange();
			}).finally(function () {
				decrementRequests();
			});
		},
	};

	// season

	$scope.season = {
		seasonOptions: [],
		selectedSeason: null,
		selectedDivision: null,

		seasonDivisionTeams: [],
		seasonDivisionTeamHash: {},

		activePlayerFilter: '',
		activeSeasonDivisionTeam: null,
		activeSeasonDivisionTeamPlayers: [],
		activeSeasonDivisionTeamPlayerHash: {},

		addPlayer: function (player) {
			incrementRequests();

			return $http.post(`${API_PREFIX}/season_division_team_players/`, {
				playerId: player.id,
				seasonDivisionTeamId: $scope.season.activeSeasonDivisionTeam.id,
			}).then(function (data) {
				var seasonDivisionTeamPlayer = getData(data).season_division_team_player;

				$scope.season.activeSeasonDivisionTeamPlayers.push(seasonDivisionTeamPlayer);
				$scope.season.activeSeasonDivisionTeamPlayerHash[player.id] = seasonDivisionTeamPlayer;
			}).finally(function () {
				decrementRequests();
			});
		},
		removePlayer: function (seasonDivisionTeamPlayer) {
			incrementRequests();

			return $http.delete(`${API_PREFIX}/season_division_team_players/${seasonDivisionTeamPlayer.id}/`).then(function (data) {
				for (var i = 0, l = $scope.season.activeSeasonDivisionTeamPlayers.length; i < l; i++) {
					if ($scope.season.activeSeasonDivisionTeamPlayers[i].id === seasonDivisionTeamPlayer.id) {
						$scope.season.activeSeasonDivisionTeamPlayers.splice(i, 1);
						break;
					}
				}

				delete $scope.season.activeSeasonDivisionTeamPlayerHash[seasonDivisionTeamPlayer.player_id];
			}).finally(function () {
				decrementRequests();
			});
		},
		onKeydown: function (ev) {
			if ((ev.keyCode || ev.which) === 27) {
				ev.preventDefault();
				ev.stopPropagation();
				$scope.season.activePlayerFilter = '';
			}
		},
		viewSeasonDivisionTeamPlayers: function (seasonDivisionTeam) {
			incrementRequests();

			return $http.get(`${API_PREFIX}/season_division_teams/${seasonDivisionTeam.id}/players/`).then(function (data) {
				$scope.season.activePlayerFilter = '';
				$scope.season.activeSeasonDivisionTeam = seasonDivisionTeam;

				$scope.season.activeSeasonDivisionTeamPlayers = getData(data).season_division_team_players;
				$scope.season.activeSeasonDivisionTeamPlayerHash = hashify($scope.season.activeSeasonDivisionTeamPlayers, 'player_id');
			}).finally(function () {
				decrementRequests();
			});
		},
		clearSeasonDivisionTeamPlayers: function () {
			$scope.season.activePlayerFilter = '';
			$scope.season.activeSeasonDivisionTeam = null;

			$scope.season.activeSeasonDivisionTeamPlayers = null;
			$scope.season.activeSeasonDivisionTeamPlayerHash = null;
		},
		addTeam: function (team) {
			incrementRequests();

			return $http.post(`${API_PREFIX}/season_division_teams/`, {
				seasonId: $scope.season.selectedSeason.id,
				teamId: team.id,
				divisionId: $scope.season.selectedDivision.id,
			}).then(function (data) {
				var seasonDivisionTeam = getData(data).season_division_team;

				$scope.season.seasonDivisionTeams.push(seasonDivisionTeam);
				$scope.season.seasonDivisionTeamHash[team.id] = seasonDivisionTeam;
			}).finally(function () {
				decrementRequests();
			});
		},
		removeTeam: function (seasonDivisionTeam) {
			incrementRequests();

			return $http.delete(`${API_PREFIX}/season_division_teams/${seasonDivisionTeam.id}/`).then(function (data) {
				for (var i = 0, l = $scope.season.seasonDivisionTeams.length; i < l; i++) {
					if ($scope.season.seasonDivisionTeams[i].id === seasonDivisionTeam.id) {
						$scope.season.seasonDivisionTeams.splice(i, 1);
						break;
					}
				}

				delete $scope.season.seasonDivisionTeamHash[seasonDivisionTeam.team_id];
			}).finally(function () {
				decrementRequests();
			});
		},
		onChange: function () {
			incrementRequests();

			return $http.get(`${API_PREFIX}/seasons/${$scope.season.selectedSeason.id}/divisions/${$scope.season.selectedDivision.id}/teams/`).then(function (data) {
				$scope.season.seasonDivisionTeams = getData(data).season_division_teams;
				$scope.season.seasonDivisionTeamHash = hashify($scope.season.seasonDivisionTeams, 'team_id');
			}).finally(function () {
				decrementRequests();
			});
		},
		initialize: function () {
			incrementRequests();
			$scope.season.clearSeasonDivisionTeamPlayers();

			return $http.get(`${API_PREFIX}/seasons/`).then(function (data) {
				$scope.season.seasonOptions = getData(data).seasons;

				$scope.season.selectedSeason = $scope.season.seasonOptions[0];
				$scope.season.selectedDivision = $scope.divisions[0];

				$scope.season.onChange();
			}).finally(function () {
				decrementRequests();
			});
		},
	};

	// initialize

	function initialize() {
		incrementRequests();

		return $q.all([
			$http.get(`${API_PREFIX}/teams/`),
			$http.get(`${API_PREFIX}/players/`),
			$http.get(`${API_PREFIX}/divisions/`),
			$http.get(`${API_PREFIX}/regions/`),
		]).then(function (data) {
			$scope.teams = getData(data[0]).teams;
			$scope.teamHash = hashify($scope.teams);

			$scope.players = getData(data[1]).players;
			$scope.playerHash = hashify($scope.players);

			$scope.divisions = getData(data[2]).divisions;
			$scope.divisionHash = hashify($scope.divisions);

			$scope.regions = getData(data[3]).regions;
			$scope.regionHash = hashify($scope.regions);

			$scope.view.initialize();
		}).finally(function () {
			decrementRequests();
		});
	}

	initialize();

	// utils

	function incrementRequests() {
		$scope.activeRequests++;
	}

	function decrementRequests() {
		$scope.activeRequests--;
	}

	function getData(payload) {
		return payload.data.data;
	}

	function hashify(data, idKey) {
		if (idKey === undefined) {
			idKey = 'id';
		}

		return data.reduce(function (accumulator, currentValue) {
			accumulator[currentValue[idKey]] = currentValue;
			return accumulator;
		}, {});
	}
});
