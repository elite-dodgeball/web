'use strict';

angular.module('TourfApp', ['ngMaterial', 'ngMessages'], function ($interpolateProvider) {
	$interpolateProvider.startSymbol('[[');
	$interpolateProvider.endSymbol(']]');
}).config(function ($sceDelegateProvider) {
	$sceDelegateProvider.resourceUrlWhitelist([
		'self',
		'https://youtube.com/**',
	]);
}).controller('TourfCtrl', function ($scope, $http, $location, $q) {
	$scope.isLoading = true;
	$scope.didInitialize = false;

	$scope.highestActiveRoundRobin = 0;

	$scope.event = {};

	$scope.eventDivisionHash = {};
	$scope.selectedDivision = null;

	$scope.eventStates = [];
	$scope.gameStates = [];

	// Make the event data request

	var eventId = $location.absUrl().match(/\/live\/([0-9]+)[^0-9]*$/)[1];

	function loadEvent() {
		$scope.isLoading = true;
		$http.get(`/tourf/events/${eventId}/?includePlayers=true&fillBracket=true`).then(onLoadSuccess, onLoadFailure).finally(onLoadFinally);
	}

	function onLoadSuccess(response) {
		var data = response.data.data;

		$scope.event = data.event;
		$scope.eventDivisionHash = data.event_division_hash;

		if (!$scope.selectedDivision) {
			for (var eventDivisionId in $scope.eventDivisionHash) {
				$scope.selectedDivision = $scope.eventDivisionHash[eventDivisionId];
				break;
			}
		}

		$scope.eventStates = data.event_states.map(mapState);
		$scope.gameStates = data.game_states.map(mapState);

		$scope.didInitialize = true;

		processEvent();
		$scope.stats.initialize();
	}

	function onLoadFailure(response) {
		console.log(response);
		$scope.didInitialize = false;
	}

	function onLoadFinally() {
		$scope.isLoading = false;
	}

	// Process stream stats

	var playerHash = {};

	$scope.stats = {
		game: null,
		topTeam: null,
		bottomTeam: null,
		initialize: function () {
			$http.get(`/tourf/events/${eventId}/stats/`).then($scope.stats.onStatsSuccess);
		},
		onStatsSuccess: function (response) {
			var data = response.data.data;

			if (data.game && data.top_team && data.bottom_team && data.top_team.players.length > 0 && data.bottom_team.players.length > 0) {
				$scope.stats.game = data.game;
				$scope.stats.topTeam = data.top_team;
				$scope.stats.bottomTeam = data.bottom_team;

				$scope.stats.setTeam($scope.stats.topTeam, $scope.stats.topTeam.id);
				$scope.stats.setTeam($scope.stats.bottomTeam, $scope.stats.bottomTeam.id);

				$scope.stats.game.bracket_type = data.bracket_types.find(bracket_type => bracket_type[0] === $scope.stats.game.bracket_type);
			} else {
				$scope.stats.game = null;
				$scope.stats.topTeam = null;
				$scope.stats.bottomTeam = null;
			}
		},
		setTeam: function (teamObject, eventDivisionTeamId) {
			teamObject.name = teamHash[eventDivisionTeamId].team.name.substr(0, 3);
			teamObject.cover = teamHash[eventDivisionTeamId].team.cover;

			for (var i = 0, l = teamObject.players.length; i < l; i++) {
				var playerDatum = playerHash[teamObject.players[i].event_division_team_player_id];

				teamObject.players[i].name = playerDatum.player.name;
				teamObject.players[i].number = playerDatum.player.number;
			}
		},
	};

	function makePlayerHash(playerData) {
		for (var i = 0, l = playerData.length; i < l; i++) {
			playerHash[playerData[i].event_division_team_player.id] = playerData[i];
		}
	}

	// Digest the event data

	var teamHash = {},
		gameHash = {},
		matchupHash = {};

	function processEvent() {
		for (var eventDivisionId in $scope.eventDivisionHash) {
			var divisionDatum = $scope.eventDivisionHash[eventDivisionId];

			for (var i = 0, l = divisionDatum.teams.length; i < l; i++) {
				divisionDatum.teams[i].seed = i + 1;
				divisionDatum.teams[i].points = 0;
			}
		}

		makeTeamHash();
		$scope.highestActiveRoundRobin = 0;

		for (eventDivisionId in $scope.eventDivisionHash) {
			var divisionDatum = $scope.eventDivisionHash[eventDivisionId];

			divisionDatum.rounds = null;
			divisionDatum.brackets = {};

			for (var bracketType in divisionDatum.bracket) {
				window.ELITE_DODGEBALL.assignTeamObjects(divisionDatum.bracket[bracketType].rounds, teamHash, gameHash);

				if (bracketType === 'round_robin') {
					divisionDatum.rounds = window.ELITE_DODGEBALL.transformRoundRobin(divisionDatum.bracket[bracketType].rounds, matchupHash, teamHash);

					window.ELITE_DODGEBALL.buildGroupHash(divisionDatum, teamHash);
					window.ELITE_DODGEBALL.calculateDivisionPoints(divisionDatum, matchupHash, teamHash);
				} else if (bracketType === 'winners_bracket') {
					divisionDatum.brackets.winners = window.ELITE_DODGEBALL.transformBracket(divisionDatum.bracket[bracketType].rounds, bracketType);
				} else if (bracketType === 'losers_bracket') {
					divisionDatum.brackets.losers = window.ELITE_DODGEBALL.transformBracket(divisionDatum.bracket[bracketType].rounds, bracketType);
				} else if (bracketType === 'finals_bracket') {
					divisionDatum.brackets.finals = window.ELITE_DODGEBALL.transformBracket(divisionDatum.bracket[bracketType].rounds, bracketType);
				}
			}
		}

		if ($scope.selectedDivision.rounds) {
			$scope.selectedIndex = 1;
		}

		if ($scope.selectedDivision.brackets.winners) {
			$scope.selectedIndex = 2;
		}

		$scope.event.normalized_stream_link = normalizeStreamLink($scope.event.stream_link);
	}

	function makeTeamHash() {
		teamHash = {};
		matchupHash = {};

		for (var eventDivisionId in $scope.eventDivisionHash) {
			for (var i = 0, l = $scope.eventDivisionHash[eventDivisionId].teams.length; i < l; i++) {
				teamHash[$scope.eventDivisionHash[eventDivisionId].teams[i].event_division_team.id] = $scope.eventDivisionHash[eventDivisionId].teams[i];
				matchupHash[$scope.eventDivisionHash[eventDivisionId].teams[i].event_division_team.id] = {};

				makePlayerHash($scope.eventDivisionHash[eventDivisionId].teams[i].players);
			}
		}
	}

	$scope.makeGameClass = function (game, bracketRound) {
		var className = '';

		if (game === null) {
			className = 'bracket-game-empty';
		} else {
			if (game.childCount === 0) {
				className = 'bracket-game-orphan';
			} else if (game.childCount === 1) {
				className = 'bracket-game-solo';
			}
		}

		if (bracketRound) {
			if (bracketRound.isFirstLast === true) {
				className = 'bracket-game-direct';
			} else if (bracketRound.isSecondLast === true) {
				className += ' bracket-game-direct';
			}
		}

		return className;
	};

	// Gotta make sure we control media embeds

	var regex = {
		youtube: /^.*(?:(?:youtu\.be\/|v\/|vi\/|u\/\w\/|embed\/)|(?:(?:watch)?\?v(?:i)?=|\&v(?:i)?=))([^#\&\?]*).*/,
	};

	function normalizeStreamLink(url) {
		if (typeof url !== 'string') {
			return url;
		}

		if (url.includes('youtube.com') === true) {
			return 'https://youtube.com/embed/' + url.match(regex.youtube)[1] + '?showinfo=0' + ($scope.event.state === $scope.eventStates[1].id ? '&autoplay=1' : '');
		}
	}

	// WebSocket stuff

	$scope.updater = {
		socket: null,
		isConnecting: false,
		connectAttempts: 0,
		connect: function () {
			if ($scope.updater.isConnecting === false && $scope.updater.connectAttempts < 5) {
				if ($scope.updater.socket) {
					$scope.updater.socket.close();
				}

				$scope.updater.socket = new WebSocket(`ws://${window.location.host}/ws/tourf/${eventId}/`);

				$scope.updater.socket.addEventListener('message', $scope.updater.onMessage);
				$scope.updater.socket.addEventListener('close', $scope.updater.onClose);
				$scope.updater.socket.addEventListener('open', $scope.updater.onOpen);

				$scope.updater.isConnecting = true;
				$scope.updater.connectAttempts++;
			}
		},
		updateEvent: function (data) {
			var oldStream = $scope.event.stream_link;

			angular.extend($scope.event, data);

			if (oldStream !== $scope.event.stream_link) {
				$scope.event.normalized_stream_link = normalizeStreamLink($scope.event.stream_link);
			}
		},
		updateGame: function (data) {
			if (Array.isArray(data) !== true) {
				data = [data];
			}

			var games = [];

			for (var i = 0, l = data.length; i < l; i++) {
				if (data[i].id in gameHash === false) {
					gameHash[data[i].id] = {};
				}
				games.push(angular.extend(gameHash[data[i].id], data[i]));
			}

			window.ELITE_DODGEBALL.assignTeamObjects([games], teamHash, gameHash);
		},
		updateTeam: function (data) {
			if (Array.isArray(data) !== true) {
				data = [data];
			}

			for (var i = 0, l = data.length; i < l; i++) {
				angular.extend(teamHash[data[i].id], data[i]);
			}

			for (var eventDivisionId in $scope.eventDivisionHash) {
				if (!$scope.eventDivisionHash[eventDivisionId].rounds) {
					continue;
				}

				for (i = 0, l = $scope.eventDivisionHash[eventDivisionId].rounds.length; i < l; i++) {
					for (var j = 0, k = $scope.eventDivisionHash[eventDivisionId].rounds[i].courts.length; j < k; j++) {
						var game = $scope.eventDivisionHash[eventDivisionId].rounds[i].courts[j];

						matchupHash[game.top_team.event_division_team.id][game.bottom_team.event_division_team.id] = {
							wins: game.top_wins,
							loss: game.bottom_wins,
						};

						matchupHash[game.bottom_team.event_division_team.id][game.top_team.event_division_team.id] = {
							wins: game.bottom_wins,
							loss: game.top_wins,
						};
					}
				}
			}

			// Call calculateDivisionPoints()

			var updateSet = new Set();

			for (var i = 0, l = data.length; i < l; i++) {
				if (updateSet.has(teamHash[data[i].id].event_division_team.event_division_id) === true) {
					continue;
				}

				updateSet.add(teamHash[data[i].id].event_division_team.event_division_id);

				if ($scope.eventDivisionHash[teamHash[data[i].id].event_division_team.event_division_id].rounds) {
					window.ELITE_DODGEBALL.calculateDivisionPoints($scope.eventDivisionHash[teamHash[data[i].id].event_division_team.event_division_id], matchupHash, teamHash);
				}
			}
		},
		updateRobin: function (data) {
			window.ELITE_DODGEBALL.assignTeamObjects(data.rounds, teamHash, gameHash);
			$scope.eventDivisionHash[data.event_division_id].rounds = window.ELITE_DODGEBALL.transformRoundRobin(data.rounds, matchupHash, teamHash);

			window.ELITE_DODGEBALL.buildGroupHash($scope.eventDivisionHash[data.event_division_id], teamHash);
			window.ELITE_DODGEBALL.calculateDivisionPoints($scope.eventDivisionHash[data.event_division_id], matchupHash, teamHash);
		},
		updateBracket: function (data) {
			for (var bracketType in data) {
				window.ELITE_DODGEBALL.assignTeamObjects(data[bracketType].rounds, teamHash, gameHash);

				if (bracketType === 'winners_bracket') {
					$scope.eventDivisionHash[data[bracketType].event_division_id].brackets.winners = window.ELITE_DODGEBALL.transformBracket(data[bracketType].rounds, bracketType);
				} else if (bracketType === 'losers_bracket') {
					$scope.eventDivisionHash[data[bracketType].event_division_id].brackets.losers = window.ELITE_DODGEBALL.transformBracket(data[bracketType].rounds, bracketType);
				} else if (bracketType === 'finals_bracket') {
					$scope.eventDivisionHash[data[bracketType].event_division_id].brackets.finals = window.ELITE_DODGEBALL.transformBracket(data[bracketType].rounds, bracketType);
				}
			}
		},
		updateStats: function (data) {
			$scope.stats.onStatsSuccess({
				data: {
					data: data,
				},
			});
		},
		onMessage: function (ev) {
			var data = JSON.parse(ev.data);

			if (data.type === 'event') {
				$scope.updater.updateEvent(data.data);
			} else if (data.type === 'game') {
				$scope.updater.updateGame(data.data.games);
				$scope.updater.updateTeam(data.data.teams);
			} else if (data.type === 'team') {
				$scope.updater.updateTeam(data.data);
			} else if (data.type === 'robin') {
				$scope.updater.updateRobin(data.data);
			} else if (data.type === 'bracket') {
				$scope.updater.updateBracket(data.data);
			} else if (data.type === 'stats') {
				$scope.updater.updateStats(data.data);
			}

			$scope.$apply();
		},
		onClose: function (ev) {
			window.setTimeout($scope.updater.connect, 1000);
		},
		onOpen: function (ev) {
			$scope.updater.isConnecting = false;
		},
	};

	// Kick it off

	loadEvent();
	$scope.updater.connect();
});

function mapState(state) {
	return {
		id: state[0],
		name: state[1],
	};
}
