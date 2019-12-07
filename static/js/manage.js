'use strict';

angular.module('ManageApp', ['ngMaterial', 'ngMessages'], function ($interpolateProvider) {
	$interpolateProvider.startSymbol('[[');
	$interpolateProvider.endSymbol(']]');
}).controller('ManageCtrl', function ($scope, $http, $filter, $location, $timeout, $q) {
	$scope.didInitialize = false;
	$scope.selectedIndex = 0;

	$scope.event = {};

	$scope.eventDivisionHash = {};
	$scope.selectedDivision = null;

	$scope.tournamentTypes = [];
	$scope.eventStates = [];
	$scope.gameStates = [];

	$scope.modelOptions = {
		debounce: 700,
	};

	$scope.WIN_TYPE = {
		TOP_TEAM: 1,
		BOTTOM_TEAM: 2,
	};

	// Event update

	var eventId = $location.absUrl().match(/\/event\/([0-9]+)\/manage/)[1];

	$scope.theEvent = {
		isSaving: false,
		save: function () {
			$scope.theEvent.isSaving = true;
			$scope.eventForm.$setPristine(true);

			$http.patch(`/tourf/events/${$scope.event.id}/`, {
				state: $scope.event.state,
				streamLink: $scope.event.stream_link,
			}).then(function (data) {
				console.log(data);
			}).finally(function () {
				$scope.theEvent.isSaving = false;
			});
		},
		onLoad: function (response) {
			var data = response.data.data;

			$scope.event = data.event;
			$scope.eventDivisionHash = data.event_division_hash;

			for (var eventDivisionId in $scope.eventDivisionHash) {
				$scope.selectedDivision = $scope.eventDivisionHash[eventDivisionId];
				break;
			}

			$scope.tournamentTypes = data.tournament_types.map(mapState);
			$scope.eventStates = data.event_states.map(mapState);
			$scope.gameStates = data.game_states.map(mapState);

			setup();
		},
		initialize: function () {
			return $http.get(`/tourf/events/${eventId}/?includePlayers=true&fillBracket=true`);
		},
	};

	// Division change

	$scope.onDivisionChange = function () {
		$scope.robin.isLocked = !!$scope.selectedDivision.rounds;
	};

	// Overlay stuff

	$scope.overlay = {
		selectedGame: null,
		activeRequests: 0,
		reset: function () {
			$scope.overlay.selectedGame = null;
		},
		onGameChange: function () {
			if ($scope.overlay.selectedGame) {
				$scope.overlay.selectedGame.top_team.players.forEach($scope.overlay.onGamePlayerChange);
				$scope.overlay.selectedGame.bottom_team.players.forEach($scope.overlay.onGamePlayerChange);
			}
		},
		onGamePlayerChange: function (playerDatum, playerIndex) {
			playerDatum.isPlaying = playerDatum.isIn = playerIndex < 6;
		},
		onPlayerChange: function (playerDatum) {
			playerDatum.isIn = playerDatum.isPlaying;
		},
		preparePlayers: function () {
			var payload = {
				game: {
					id: $scope.overlay.selectedGame.id,
				},
				players: [],
			};

			$scope.overlay.selectedGame.top_team.players.forEach(function (playerDatum) {
				payload.players.push({
					eventDivisionTeamPlayerId: playerDatum.event_division_team_player.id,
					isPlaying: playerDatum.isPlaying,
					isIn: playerDatum.isIn,
				});
			});

			$scope.overlay.selectedGame.bottom_team.players.forEach(function (playerDatum) {
				payload.players.push({
					eventDivisionTeamPlayerId: playerDatum.event_division_team_player.id,
					isPlaying: playerDatum.isPlaying,
					isIn: playerDatum.isIn,
				});
			});

			return payload;
		},
		update: function () {
			$scope.overlay.activeRequests++;

			var overlayPromise;

			if ($scope.overlay.selectedGame) {
				overlayPromise = $http.put(`/tourf/events/${eventId}/stats/`, $scope.overlay.preparePlayers());
			} else {
				overlayPromise = $http.delete(`/tourf/events/${eventId}/stats/`);
			}

			return overlayPromise.then(function (data) {
				console.log(data);
			}).finally(function () {
				$scope.overlay.activeRequests--;
			});
		},
		onLoad: function (response) {
			var data = response.data.data;

			if (data.game && data.game.bracket_type === 1) {
				for (var i = 0, l = $scope.selectedDivision.rounds.length; i < l; i++) {
					for (var j = 0, k = $scope.selectedDivision.rounds[i].courts.length; j < k; j++) {
						if ($scope.selectedDivision.rounds[i].courts[j].id === data.game.id) {
							$scope.overlay.selectedGame = $scope.selectedDivision.rounds[i].courts[j];
							break;
						}
					}

					if ($scope.overlay.selectedGame) {
						break;
					}
				}
			}

			if ($scope.overlay.selectedGame) {
				var playerHash = {};

				$scope.overlay.onGameChange();

				$scope.overlay.selectedGame.top_team.players.forEach(function (playerDatum) {
					playerHash[playerDatum.event_division_team_player.id] = playerDatum;
				});

				$scope.overlay.selectedGame.bottom_team.players.forEach(function (playerDatum) {
					playerHash[playerDatum.event_division_team_player.id] = playerDatum;
				});

				data.top_team.players.forEach(function (livePlayer) {
					playerHash[livePlayer.event_division_team_player_id].isIn = livePlayer.is_in;
					playerHash[livePlayer.event_division_team_player_id].isPlaying = livePlayer.is_playing;
				});

				data.bottom_team.players.forEach(function (livePlayer) {
					playerHash[livePlayer.event_division_team_player_id].isIn = livePlayer.is_in;
					playerHash[livePlayer.event_division_team_player_id].isPlaying = livePlayer.is_playing;
				});
			}
		},
		initialize: function () {
			return $http.get(`/tourf/events/${eventId}/stats/`);
		},
	};

	// Check-in stuff

	$scope.checkin = {
		activeRequests: 0,
		activeTeamDatum: null,
		showTeamPlayers: false,
		viewTeamPlayers: function (teamDatum) {
			$scope.checkin.activeTeamDatum = teamDatum;
			$scope.checkin.showTeamPlayers = true;
		},
		checkPlayers: function (playerDatum) {
			$scope.checkin.activeTeamDatum.event_division_team.is_checked_in = true;

			for (var i = 0, l = $scope.checkin.activeTeamDatum.players.length; i < l; i++) {
				if ($scope.checkin.activeTeamDatum.players[i].event_division_team_player.is_checked_in !== true) {
					$scope.checkin.activeTeamDatum.event_division_team.is_checked_in = false;
					break;
				}
			}

			$scope.checkin.updatePlayer(playerDatum);
			$scope.checkin.updateTeam($scope.checkin.activeTeamDatum);
		},
		updateTeam: function (teamDatum) {
			$scope.checkin.activeRequests++;

			return $http.patch(`/tourf/teams/${teamDatum.event_division_team.id}/`, {
				isCheckedIn: teamDatum.event_division_team.is_checked_in,
			}).finally(function () {
				$scope.bracket.activeRequests--;
			});
		},
		updatePlayer: function (playerDatum) {
			$scope.checkin.activeRequests++;

			return $http.patch(`/tourf/players/${playerDatum.event_division_team_player.id}/`, {
				isCheckedIn: playerDatum.event_division_team_player.is_checked_in,
			}).finally(function () {
				$scope.bracket.activeRequests--;
			});
		},
	};

	$scope.scanner = {
		scanner: null,
		hasError: false,
		isEnabled: false,
		foundPlayer: null,
		foundContent: null,
		deviceOptions: [],
		selectedDevice: null,
		onScan: function (content, image) {
			if (!$scope.scanner.foundPlayer) {
				$scope.scanner.foundPlayer = false;
				$scope.scanner.foundContent = content;

				for (var i = 0, l = $scope.selectedDivision.teams.length; i < l; i++) {
					for (var j = 0, k = $scope.selectedDivision.teams[i].players.length; j < k; j++) {
						if ($scope.selectedDivision.teams[i].players[j].player.usad_id === content) {
							$scope.scanner.foundPlayer = $scope.selectedDivision.teams[i].players[j];
							break;
						}
					}

					if ($scope.scanner.foundPlayer) {
						break;
					}
				}

				if ($scope.scanner.foundPlayer) {
					$scope.checkin.viewTeamPlayers(teamHash[$scope.scanner.foundPlayer.event_division_team_player.event_division_team_id]);
				}
			}

			$scope.$apply();
		},
		start: function () {
			if ($scope.scanner.isShowing !== true) {
				$scope.scanner.hasError = false;
				$scope.scanner.isShowing = true;

				$scope.scanner.clear();

				return $scope.scanner.scanner.start($scope.scanner.selectedDevice).catch(function (error) {
					$scope.scanner.hasError = error;
				});
			}
		},
		stop: function () {
			if ($scope.scanner.isShowing !== false) {
				$scope.scanner.hasError = false;
				$scope.scanner.isShowing = false;

				$scope.scanner.clear();

				return $scope.scanner.scanner.stop();
			}
		},
		clear: function () {
			$scope.scanner.foundPlayer = null;
			$scope.scanner.foundContent = null;
		},
		checkin: function () {
			if ($scope.scanner.foundPlayer) {
				$scope.scanner.foundPlayer.event_division_team_player.is_checked_in = true;
				$scope.checkin.checkPlayers($scope.scanner.foundPlayer);
			}

			$scope.scanner.clear();
		},
		getDevices: function () {
			return Instascan.Camera.getCameras().then(function (devices) {
				$scope.scanner.deviceOptions = devices;

				if ($scope.scanner.deviceOptions) {
					$scope.scanner.selectedDevice = devices[0];
				}

				if ($scope.scanner.selectedDevice) {
					$scope.scanner.isEnabled = true;
				}
			}).catch(function (error) {
				$scope.scanner.hasError = error;
			}).finally(function () {
				$scope.$apply();
			});
		},
		initialize: function () {
			$scope.scanner.scanner = new Instascan.Scanner({
				scanPeriod: 5,
				video: document.querySelector('#scanner-camera'),
			});

			$scope.scanner.scanner.addListener('scan', $scope.scanner.onScan);

			return $scope.scanner.getDevices();
		},
	};

	// Round-robin generator

	$scope.robin = {
		courtTotal: 3,
		refereeCount: 2,
		poolNumber: 1,
		isLocked: false,
		activeRequests: 0,
		eventPromise: null,
		reset: function (reseed, clearRounds) {
			var currentSeed = 1;

			for (var i = 0, l = $scope.selectedDivision.teams.length; i < l; i++) {
				$scope.selectedDivision.teams[i].points = 0;

				if (reseed === true) {
					if ($scope.selectedDivision.teams[i].event_division_team.is_checked_in === true) {
						$scope.selectedDivision.teams[i].seed = currentSeed++;
					} else {
						$scope.selectedDivision.teams[i].seed = l + i + 1;
					}
				}
			}

			if (clearRounds === true) {
				$scope.selectedDivision.rounds = null;
				$scope.robin.isLocked = false;
			}
		},
		generate: function () {
			$scope.robin.activeRequests++;

			return $http.post('/tourf/robins/', {
				eventId: $scope.event.id,
				eventDivisionId: $scope.selectedDivision.event_division.id,
				courtTotal: $scope.robin.courtTotal,
				refereeCount: $scope.robin.refereeCount,
				poolNumber: $scope.robin.poolNumber,
				teams: $scope.selectedDivision.teams.reduce($scope.robin.reduceTeam, []),
			}).then(function (response) {
				$scope.robin.isLocked = true;
				$scope.selectedDivision.rounds = transformRoundRobin(response.data.data.round_robin.rounds);
			}).finally(function () {
				$scope.robin.activeRequests--;
			});
		},
		reduceTeam: function (accumulator, teamDatum) {
			if (teamDatum.event_division_team.is_checked_in === true) {
				accumulator.push({
					eventDivisionTeamId: teamDatum.event_division_team.id,
					seed: teamDatum.seed,
				});
			}
			return accumulator;
		},
		putGame: function (game) {
			$scope.robin.activeRequests++;

			return $http.put(`/tourf/games/${game.id}/`, prepareGame(game)).then(function (data) {
				console.log(data);
			}).finally(function () {
				$scope.robin.activeRequests--;
			});
		},
		crankWins: function (ev, game, WIN_TYPE) {
			ev.preventDefault();
			ev.stopImmediatePropagation();

			if ($scope.robin.eventPromise) {
				$timeout.cancel($scope.robin.eventPromise);
				$scope.robin.decrementWins(game, WIN_TYPE);
			} else {
				$scope.robin.eventPromise = $timeout($scope.robin.incrementWins, 500, true, game, WIN_TYPE);
			}
		},
		incrementWins: function (game, WIN_TYPE) {
			$scope.robin.eventPromise = null;

			if (WIN_TYPE === $scope.WIN_TYPE.TOP_TEAM) {
				game.top_wins++;
			} else if (WIN_TYPE === $scope.WIN_TYPE.BOTTOM_TEAM) {
				game.bottom_wins++;
			}

			$scope.robin.updateWins(game);
		},
		decrementWins: function (game, WIN_TYPE) {
			$scope.robin.eventPromise = null;

			if (WIN_TYPE === $scope.WIN_TYPE.TOP_TEAM && game.top_wins > 0) {
				game.top_wins--;
			} else if (WIN_TYPE === $scope.WIN_TYPE.BOTTOM_TEAM && game.bottom_wins > 0) {
				game.bottom_wins--;
			}

			$scope.robin.updateWins(game);
		},
		updateWins: function (game) {
			var putPromise = $scope.robin.putGame(game);

			// Add up wins/loss

			matchupHash[game.top_team.event_division_team.id][game.bottom_team.event_division_team.id].wins = game.top_wins;
			matchupHash[game.top_team.event_division_team.id][game.bottom_team.event_division_team.id].loss = game.bottom_wins;

			matchupHash[game.bottom_team.event_division_team.id][game.top_team.event_division_team.id].wins = game.bottom_wins;
			matchupHash[game.bottom_team.event_division_team.id][game.top_team.event_division_team.id].loss = game.top_wins;

			// Calculate points

			$scope.robin.calculatePoints();
		},
		calculatePoints: function () {
			var checkSet = new Set(),
				divisionTeamHash = {};

			// Zero out the points

			for (var eventDivisionTeamId in teamHash) {
				if (teamHash[eventDivisionTeamId].event_division_team.event_division_id === $scope.selectedDivision.event_division.id) {
					teamHash[eventDivisionTeamId].points = 0;
					divisionTeamHash[eventDivisionTeamId] = {
						wins: 0,
						loss: 0,
						id: eventDivisionTeamId,
					};
				}
			}

			// Calculate match points

			for (var eventDivisionTeamIdA in divisionTeamHash) {
				for (var eventDivisionTeamIdB in matchupHash[eventDivisionTeamIdA]) {
					var game = matchupHash[eventDivisionTeamIdA][eventDivisionTeamIdB],
						checkKey = eventDivisionTeamIdA + '|' + eventDivisionTeamIdB;

					if (checkSet.has(checkKey) === true) {
						continue;
					}

					checkSet.add(checkKey);
					checkSet.add(eventDivisionTeamIdB + '|' + eventDivisionTeamIdA);

					if (game.wins === 0 && game.loss === 0) {
						continue;
					}

					if (game.wins > game.loss) {
						divisionTeamHash[eventDivisionTeamIdA].wins++;
						divisionTeamHash[eventDivisionTeamIdB].loss++;

						teamHash[eventDivisionTeamIdA].points += 2;
						teamHash[eventDivisionTeamIdB].points += 1;
					} else if (game.loss > game.wins) {
						divisionTeamHash[eventDivisionTeamIdA].loss++;
						divisionTeamHash[eventDivisionTeamIdB].wins++;

						teamHash[eventDivisionTeamIdA].points += 1;
						teamHash[eventDivisionTeamIdB].points += 2;
					}
				}
			}

			// Detect ties

			var tieHash = {};

			for (eventDivisionTeamId in divisionTeamHash) {
				if (teamHash[eventDivisionTeamId].points in tieHash === false) {
					tieHash[teamHash[eventDivisionTeamId].points] = eventDivisionTeamId;
				} else if (Array.isArray(tieHash[teamHash[eventDivisionTeamId].points]) === false) {
					tieHash[teamHash[eventDivisionTeamId].points] = [tieHash[teamHash[eventDivisionTeamId].points], eventDivisionTeamId];
				} else {
					tieHash[teamHash[eventDivisionTeamId].points].push(eventDivisionTeamId);
				}
			}

			for (var points in tieHash) {
				if (Array.isArray(tieHash[points]) === false) {
					continue;
				}

				var tieCount = tieHash[points].length;

				if (tieCount === 2) {
					game = matchupHash[tieHash[points][0]][tieHash[points][1]];

					if (game.wins > game.loss) {
						teamHash[tieHash[points][0]].points += 0.5;
					} else if (game.loss > game.wins) {
						teamHash[tieHash[points][1]].points += 0.5;
					}
				} else if (tieCount > 2) {
					var ratioList = [],
						spotValue = 1 / tieCount;

					for (var i = 0; i < tieCount; i++) {
						divisionTeamHash[tieHash[points][i]].ratio = divisionTeamHash[tieHash[points][i]].wins / divisionTeamHash[tieHash[points][i]].loss;
						ratioList.push(divisionTeamHash[tieHash[points][i]]);
					}

					ratioList.sort(ratioSort);

					for (i = 0; i < tieCount; i++) {
						teamHash[ratioList[i].id].points += i * spotValue;
					}
				}
			}

			// TODO: Detect internal ties http://www.usatt.net/rules/stumpump/stump97/11.shtml
		},
		shuffleTeams: function () {
			shuffleArray($scope.selectedDivision.teams);
			$scope.robin.reset(true, true);
		},
	};

	function ratioSort(a, b) {
		if (a.ratio === b.ratio) {
			return 0;
		}
		return a.ratio > b.ratio ? 1 : -1;
	}

	// Bracket processing

	$scope.bracket = {
		isLocked: false,
		activeRequests: 0,
		eventPromise: null,
		makeGameClass: function (game, bracketRound) {
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
		},
		saveDivision: function () {
			$scope.bracket.activeRequests++;

			return $http.patch(`/tourf/divisions/${$scope.selectedDivision.event_division.id}/`, {
				tournamentType: $scope.selectedDivision.event_division.tournament_type,
			}).finally(function () {
				$scope.bracket.activeRequests--;
			});
		},
		postBracket: function () {
			$scope.bracket.activeRequests++;

			return $http.post('/tourf/brackets/?fillBracket=true', {
				eventId: $scope.event.id,
				eventDivisionId: $scope.selectedDivision.event_division.id,
				isDoubleElimination: $scope.selectedDivision.event_division.tournament_type === $scope.tournamentTypes[1].id,
				teams: $filter('orderBy')(angular.copy($scope.selectedDivision.teams), ['-points', 'seed']).map($scope.bracket.mapTeam),
			}).then(function (response) {
				$scope.selectedDivision.brackets = {};

				for (var bracketType in response.data.data) {
					assignTeamObjects(response.data.data[bracketType].rounds);

					if (bracketType === 'round_robin') {
						$scope.selectedDivision.rounds = transformRoundRobin(response.data.data[bracketType].rounds);
					} else if (bracketType === 'winners_bracket') {
						$scope.selectedDivision.brackets.winners = transformBracket(response.data.data[bracketType].rounds, bracketType);
					} else if (bracketType === 'losers_bracket') {
						$scope.selectedDivision.brackets.losers = transformBracket(response.data.data[bracketType].rounds, bracketType);
					} else if (bracketType === 'finals_bracket') {
						$scope.selectedDivision.brackets.finals = transformBracket(response.data.data[bracketType].rounds, bracketType);
					}
				}

				$scope.bracket.isLocked = true;
			}).finally(function () {
				$scope.bracket.activeRequests--;
			});
		},
		generate: function () {
			return $q.all([
				$scope.bracket.saveDivision(),
				$scope.bracket.postBracket(),
			]);
		},
		mapTeam: function (teamDatum, teamIndex) {
			return {
				eventDivisionTeamId: teamDatum.event_division_team.id,
				seed: teamIndex !== undefined ? teamIndex + 1 : teamDatum.seed,
			};
		},
		crankWins: function (ev, game, WIN_TYPE) {
			ev.preventDefault();
			ev.stopImmediatePropagation();

			if (game.state === $scope.gameStates[1].id) {
				if ($scope.bracket.eventPromise) {
					$timeout.cancel($scope.bracket.eventPromise);
					$scope.bracket.decrementWins(game, WIN_TYPE);
				} else {
					$scope.bracket.eventPromise = $timeout($scope.bracket.incrementWins, 500, true, game, WIN_TYPE);
				}
			}
		},
		incrementWins: function (game, WIN_TYPE) {
			$scope.bracket.eventPromise = null;

			if (WIN_TYPE === $scope.WIN_TYPE.TOP_TEAM) {
				game.top_wins++;
			} else if (WIN_TYPE === $scope.WIN_TYPE.BOTTOM_TEAM) {
				game.bottom_wins++;
			}

			$scope.bracket.updateGame(game);
		},
		decrementWins: function (game, WIN_TYPE) {
			$scope.bracket.eventPromise = null;

			if (WIN_TYPE === $scope.WIN_TYPE.TOP_TEAM && game.top_wins > 0) {
				game.top_wins--;
			} else if (WIN_TYPE === $scope.WIN_TYPE.BOTTOM_TEAM && game.bottom_wins > 0) {
				game.bottom_wins--;
			}

			$scope.bracket.updateGame(game);
		},
		updateGame: function (game) {
			$scope.bracket.activeRequests++;

			return $http.put(`/tourf/games/${game.id}/`, prepareGame(game)).then(function (response) {
				for (var i = 0, l = response.data.data.teams.length; i < l; i++) {
					teamHash[response.data.data.teams[i].id].seed = response.data.data.teams[i].place;
					teamHash[response.data.data.teams[i].id].event_division_team.place = response.data.data.teams[i].place;
					teamHash[response.data.data.teams[i].id].event_division_team.suffix = response.data.data.teams[i].suffix;
				}

				var gameHash = {};

				for (var bracketType in $scope.selectedDivision.brackets) {
					for (i = 0, l = $scope.selectedDivision.brackets[bracketType].length; i < l; i++) {
						for (var j = 0, k = $scope.selectedDivision.brackets[bracketType][i].length; j < k; j++) {
							if ($scope.selectedDivision.brackets[bracketType][i][j] === null) {
								continue;
							}

							gameHash[$scope.selectedDivision.brackets[bracketType][i][j].id] = $scope.selectedDivision.brackets[bracketType][i][j];
						}
					}
				}

				for (i = 0, l = $scope.selectedDivision.brackets.winners.length; i < l; i++) {
					for (var j = 0, k = $scope.selectedDivision.brackets.winners[i].length; j < k; j++) {
						if ($scope.selectedDivision.brackets.winners[i][j] === null) {
							continue;
						}

						gameHash[$scope.selectedDivision.brackets.winners[i][j].id] = $scope.selectedDivision.brackets.winners[i][j];
					}
				}

				for (i = 0, l = response.data.data.games.length; i < l; i++) {
					gameHash[response.data.data.games[i].id].top_team = teamHash[response.data.data.games[i].top_team.id];
					gameHash[response.data.data.games[i].id].bottom_team = teamHash[response.data.data.games[i].bottom_team.id];
				}
			}).finally(function () {
				$scope.bracket.activeRequests--;
			});
		},
	};

	function prepareGame(game) {
		return {
			id: game.id,
			topTeamId: game.top_team.event_division_team.id,
			topWins: game.top_wins,
			bottomTeamId: game.bottom_team.event_division_team.id,
			bottomWins: game.bottom_wins,
			state: game.state,
		};
	}

	// Initialization function

	var teamHash = {},
		matchupHash = {};

	function setup() {
		for (var eventDivisionId in $scope.eventDivisionHash) {
			var divisionDatum = $scope.eventDivisionHash[eventDivisionId];

			for (var i = 0, l = divisionDatum.teams.length; i < l; i++) {
				divisionDatum.teams[i].seed = i + 1;
				divisionDatum.teams[i].points = 0;
			}
		}

		makeTeamHash();
		$scope.robin.reset(true, true);

		for (eventDivisionId in $scope.eventDivisionHash) {
			var divisionDatum = $scope.eventDivisionHash[eventDivisionId];

			divisionDatum.rounds = null;
			divisionDatum.brackets = {};

			for (var bracketType in divisionDatum.bracket) {
				assignTeamObjects(divisionDatum.bracket[bracketType].rounds);

				if (bracketType === 'round_robin') {
					divisionDatum.rounds = transformRoundRobin(divisionDatum.bracket[bracketType].rounds);
				} else if (bracketType === 'winners_bracket') {
					divisionDatum.brackets.winners = transformBracket(divisionDatum.bracket[bracketType].rounds, bracketType);
				} else if (bracketType === 'losers_bracket') {
					divisionDatum.brackets.losers = transformBracket(divisionDatum.bracket[bracketType].rounds, bracketType);
				} else if (bracketType === 'finals_bracket') {
					divisionDatum.brackets.finals = transformBracket(divisionDatum.bracket[bracketType].rounds, bracketType);
				}
			}
		}

		if ($scope.selectedDivision.rounds) {
			$scope.robin.isLocked = true;
			$scope.selectedIndex = 1;
		}

		if ($scope.selectedDivision.brackets.winners) {
			$scope.bracket.isLocked = true;
			$scope.selectedIndex = 2;
		}
	}

	function transformBracket(rounds, bracketType) {
		var bracket = [],
			winnerToHash = {};

		for (var i = rounds.length - 1; i >= 0; i--) {
			bracket.push(rounds[i]);

			for (var j = 0, k = rounds[i].length; j < k; j++) {
				if (rounds[i][j] === null) {
					continue;
				}

				// childCount

				if (rounds[i][j].id in winnerToHash === true) {
					rounds[i][j].childCount = winnerToHash[rounds[i][j].id];
				} else {
					rounds[i][j].childCount = 0;
				}

				// winnerToHash

				if (rounds[i][j].winner_to in winnerToHash === false) {
					winnerToHash[rounds[i][j].winner_to] = 0;
				}

				winnerToHash[rounds[i][j].winner_to]++;
			}

			if (bracketType === 'losers_bracket') {
				if (i === 0) {
					rounds[i].isFirstLast = true;
				} else if (i === 1) {
					rounds[i].isSecondLast = true;
				}
			}
		}

		return bracket;
	}

	function transformRoundRobin(rounds) {
		var transformedRounds = [];

		for (var i = 0, l = rounds.length; i < l; i++) {
			var transformedRound = {
				courts: [],
				referees: [],
			};

			for (var j = 0, k = rounds[i].length; j < k; j++) {
				if (rounds[i][j].top_team && 'id' in rounds[i][j].top_team) {
					teamHash[rounds[i][j].top_team.id].seed = rounds[i][j].top_team.seed;
					rounds[i][j].top_team = teamHash[rounds[i][j].top_team.id];
				}

				if (!rounds[i][j].bottom_team) {
					transformedRound.referees.push(rounds[i][j].top_team);
				} else {
					if ('id' in rounds[i][j].bottom_team) {
						teamHash[rounds[i][j].bottom_team.id].seed = rounds[i][j].bottom_team.seed;
						rounds[i][j].bottom_team = teamHash[rounds[i][j].bottom_team.id];
					}

					matchupHash[rounds[i][j].top_team.event_division_team.id][rounds[i][j].bottom_team.event_division_team.id] = {
						wins: rounds[i][j].top_wins,
						loss: rounds[i][j].bottom_wins,
					};

					matchupHash[rounds[i][j].bottom_team.event_division_team.id][rounds[i][j].top_team.event_division_team.id] = {
						wins: rounds[i][j].bottom_wins,
						loss: rounds[i][j].top_wins,
					};

					transformedRound.courts.push(rounds[i][j]);
				}
			}

			transformedRounds.push(transformedRound);
		}

		$scope.robin.calculatePoints();

		return transformedRounds;
	}

	function assignTeamObjects(rounds) {
		for (var i = 0, l = rounds.length; i < l; i++) {
			for (var j = 0, k = rounds[i].length; j < k; j++) {
				if (rounds[i][j] === null) {
					continue;
				}

				if (rounds[i][j].top_team && rounds[i][j].top_team.id in teamHash) {
					teamHash[rounds[i][j].top_team.id].seed = rounds[i][j].top_team.seed;
					rounds[i][j].top_team = teamHash[rounds[i][j].top_team.id];
				}

				if (rounds[i][j].bottom_team && rounds[i][j].bottom_team.id in teamHash) {
					teamHash[rounds[i][j].bottom_team.id].seed = rounds[i][j].bottom_team.seed;
					rounds[i][j].bottom_team = teamHash[rounds[i][j].bottom_team.id];
				}
			}
		}
	}

	function makeTeamHash() {
		teamHash = {};
		matchupHash = {};

		for (var eventDivisionId in $scope.eventDivisionHash) {
			for (var i = 0, l = $scope.eventDivisionHash[eventDivisionId].teams.length; i < l; i++) {
				teamHash[$scope.eventDivisionHash[eventDivisionId].teams[i].event_division_team.id] = $scope.eventDivisionHash[eventDivisionId].teams[i];
				matchupHash[$scope.eventDivisionHash[eventDivisionId].teams[i].event_division_team.id] = {};
			}
		}
	}

	function initialize() {
		$scope.didInitialize = false;

		$q.all([
			$scope.theEvent.initialize(),
			$scope.overlay.initialize(),
		]).then(function (response) {
			$scope.theEvent.onLoad(response[0]);
			$scope.overlay.onLoad(response[1]);

			$scope.scanner.initialize();
		}).finally(function () {
			$scope.didInitialize = true;
		});
	}

	initialize();
});

function shuffleArray(array) {
	for (var i = array.length - 1; i > 0; i--) {
		var j = Math.floor(Math.random() * (i + 1)),
			temp = array[i];
		array[i] = array[j];
		array[j] = temp;
	}
	return array;
}

function animateScroll(elem) {
	var rect = elem.getBoundingClientRect(),
		target = rect.top + rect.height;

	if (target > 0) {
		window.scrollTo(0, window.scrollY + 30);
		setTimeout(animateScroll, 10, elem);
	}
}

function mapState(state) {
	return {
		id: state[0],
		name: state[1],
	};
}
