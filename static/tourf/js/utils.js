'use strict';

window.ELITE_DODGEBALL = window.ELITE_DODGEBALL || {};
window.ELITE_DODGEBALL.CONSTANTS = window.ELITE_DODGEBALL.CONSTANTS || {};

window.ELITE_DODGEBALL.CONSTANTS.WIN_VALUE = 2;
window.ELITE_DODGEBALL.CONSTANTS.LOSS_VALUE = 1;

/**
 * Turn an API bracket response into a display bracket.
 * @param {Array} rounds
 * @param {string} bracketType - `winners_bracket`, `losers_bracket`, `finals_bracket`
 * @returns {Array}
 */
window.ELITE_DODGEBALL.transformBracket = function transformBracket(rounds, bracketType) {
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
};

/**
 * Turn an API round-robin response into a display round-robin.
 * @param {Array} rounds
 * @param {Object} matchupHash
 * @param {Object} teamHash
 * @returns {Array}
 */
window.ELITE_DODGEBALL.transformRoundRobin = function transformRoundRobin(rounds, matchupHash, teamHash) {
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

	return transformedRounds;
};

/**
 * Set the `top_team` and `bottom_team` attributes of games.
 * @param {Array} rounds
 * @param {Object} teamHash
 * @param {Object} [gameHash]
 */
window.ELITE_DODGEBALL.assignTeamObjects = function assignTeamObjects(rounds, teamHash, gameHash) {
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

			if (gameHash) {
				gameHash[rounds[i][j].id] = rounds[i][j];
			}
		}
	}
};

/**
 * Assign round-robin games to their respective `groupNumber`.
 * @param {Object} divisionDatum
 * @param {Object} teamHash
 */
window.ELITE_DODGEBALL.buildGroupHash = function buildGroupHash(divisionDatum, teamHash) {
	// reset divisionDatum

	divisionDatum.groupCount = 0;

	if (divisionDatum.groupHash) {
		for (var groupNumber in divisionDatum.groupHash) {
			divisionDatum.groupHash[groupNumber].teamSet.clear();
			divisionDatum.groupHash[groupNumber].teams.length = 0;

			delete divisionDatum.groupHash[groupNumber];
		}
	} else {
		divisionDatum.groupHash = {};
	}

	// build groupHash

	for (var i = 0, l = divisionDatum.rounds.length; i < l; i++) {
		for (var j = 0, k = divisionDatum.rounds[i].courts.length; j < k; j++) {
			var game = divisionDatum.rounds[i].courts[j];

			if (game.group_number in divisionDatum.groupHash !== true) {
				divisionDatum.groupHash[game.group_number] = {
					groupName: String.fromCharCode(65 + game.group_number),
					teamSet: new Set(),
					teams: [],
				};

				divisionDatum.groupCount++;
			}

			var groupDatum = divisionDatum.groupHash[game.group_number];

			if (groupDatum.teamSet.has(game.top_team.event_division_team.id) !== true) {
				groupDatum.teamSet.add(game.top_team.event_division_team.id);
				groupDatum.teams.push(teamHash[game.top_team.event_division_team.id]);
			}

			if (groupDatum.teamSet.has(game.bottom_team.event_division_team.id) !== true) {
				groupDatum.teamSet.add(game.bottom_team.event_division_team.id);
				groupDatum.teams.push(teamHash[game.bottom_team.event_division_team.id]);
			}
		}
	}
};

/**
 * Calculate round-robin points for a `divisionDatum`.
 * @param {Object} divisionDatum
 * @param {Object} matchupHash
 * @param {Object} teamHash
 * @returns {Object}
 */
window.ELITE_DODGEBALL.calculateDivisionPoints = function calculateDivisionPoints(divisionDatum, matchupHash, teamHash) {
	var divisionTeamHash = {};

	if (divisionDatum.groupHash) {
		// Call calculateGroupPoints()

		for (var groupNumber in divisionDatum.groupHash) {
			var groupTeamHash = window.ELITE_DODGEBALL.calculateGroupPoints(divisionDatum.groupHash[groupNumber], matchupHash, teamHash);

			// Transfer to divisionTeamHash

			for (var eventDivisionTeamId in groupTeamHash) {
				divisionTeamHash[eventDivisionTeamId] = groupTeamHash[eventDivisionTeamId];
			}
		}

		// Detect ties

		var tieHash = window.ELITE_DODGEBALL.buildTieHash(divisionTeamHash, teamHash);

		for (var points in tieHash) {
			if (Array.isArray(tieHash[points]) === false) {
				continue;
			}

			var tieCount = tieHash[points].length;

			if (tieCount === 2) {
				var firstRatio = window.ELITE_DODGEBALL.makeRatio(divisionTeamHash[tieHash[points][0]].wins, divisionTeamHash[tieHash[points][0]].loss),
					secondRatio = window.ELITE_DODGEBALL.makeRatio(divisionTeamHash[tieHash[points][1]].wins, divisionTeamHash[tieHash[points][1]].loss);

				if (firstRatio > secondRatio) {
					teamHash[tieHash[points][0]].points += 0.25;
				} else if (secondRatio > firstRatio) {
					teamHash[tieHash[points][1]].points += 0.25;
				}
			} else if (tieCount > 2) {
				var ratioList = [],
					spotValue = ((parseInt(points, 10) || (1 / tieCount)) / tieCount) / 10;

				for (var i = 0; i < tieCount; i++) {
					divisionTeamHash[tieHash[points][i]].ratio = divisionTeamHash[tieHash[points][i]].wins / divisionTeamHash[tieHash[points][i]].loss;

					if (isNaN(divisionTeamHash[tieHash[points][i]].ratio) === true) {
						divisionTeamHash[tieHash[points][i]].ratio = -Infinity;
					}

					ratioList.push(divisionTeamHash[tieHash[points][i]]);
				}

				ratioList.sort(window.ELITE_DODGEBALL.ratioSort);

				for (i = 0; i < tieCount; i++) {
					teamHash[ratioList[i].id].points += i * spotValue;
				}
			}
		}
	}

	return divisionTeamHash;
};

/**
 * Calculate round-robin points for a `groupDatum`.
 * @param {Object} groupDatum
 * @param {Object} matchupHash
 * @param {Object} teamHash
 * @returns {Object}
 */
window.ELITE_DODGEBALL.calculateGroupPoints = function calculateGroupPoints(groupDatum, matchupHash, teamHash) {
	var checkSet = new Set(),
		groupTeamHash = {};

	// Zero out the points

	for (var i = 0, l = groupDatum.teams.length; i < l; i++) {
		groupTeamHash[groupDatum.teams[i].event_division_team.id] = {
			wins: 0,
			loss: 0,
			id: groupDatum.teams[i].event_division_team.id,
		};

		teamHash[groupDatum.teams[i].event_division_team.id].points = 0;
	}

	// Calculate match points

	for (var eventDivisionTeamIdA in groupTeamHash) {
		for (var eventDivisionTeamIdB in matchupHash[eventDivisionTeamIdA]) {
			if (eventDivisionTeamIdB in groupTeamHash !== true) {
				continue;
			}

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
				groupTeamHash[eventDivisionTeamIdA].wins++;
				groupTeamHash[eventDivisionTeamIdB].loss++;

				teamHash[eventDivisionTeamIdA].points += window.ELITE_DODGEBALL.CONSTANTS.WIN_VALUE;
				teamHash[eventDivisionTeamIdB].points += window.ELITE_DODGEBALL.CONSTANTS.LOSS_VALUE;
			} else if (game.loss > game.wins) {
				groupTeamHash[eventDivisionTeamIdA].loss++;
				groupTeamHash[eventDivisionTeamIdB].wins++;

				teamHash[eventDivisionTeamIdA].points += window.ELITE_DODGEBALL.CONSTANTS.LOSS_VALUE;
				teamHash[eventDivisionTeamIdB].points += window.ELITE_DODGEBALL.CONSTANTS.WIN_VALUE;
			}
		}
	}

	// Detect ties

	var tieHash = window.ELITE_DODGEBALL.buildTieHash(groupTeamHash, teamHash);

	for (var points in tieHash) {
		if (Array.isArray(tieHash[points]) === false) {
			continue;
		}

		var tieCount = tieHash[points].length;

		if (tieCount === 2) {
			// Two teams is simple

			var game = matchupHash[tieHash[points][0]][tieHash[points][1]];

			if (game.wins > game.loss) {
				teamHash[tieHash[points][0]].points += 0.5;
			} else if (game.loss > game.wins) {
				teamHash[tieHash[points][1]].points += 0.5;
			}
		} else if (tieCount > 2) {
			// Match points for only relevant games

			var matchSpotValue = 1 / tieCount,
				matchTeamSet = new Set(tieHash[points]),
				matchTeamHash = {},
				matchTeams = [];

			for (var i = 0; i < tieCount; i++) {
				matchTeamHash[tieHash[points][i]] = {
					wins: 0,
					loss: 0,
					game_wins: 0,
					game_loss: 0,
					points: 0,
					id: tieHash[points][i],
				};

				for (var eventDivisionTeamId in matchupHash[tieHash[points][i]]) {
					if (matchTeamSet.has(eventDivisionTeamId) !== true) {
						continue;
					}

					var game = matchupHash[tieHash[points][i]][eventDivisionTeamId];

					matchTeamHash[tieHash[points][i]].game_wins += game.wins;
					matchTeamHash[tieHash[points][i]].game_loss += game.loss;

					if (game.wins > game.loss) {
						matchTeamHash[tieHash[points][i]].wins++;
						matchTeamHash[tieHash[points][i]].points += window.ELITE_DODGEBALL.CONSTANTS.WIN_VALUE;
					} else if (game.loss > game.wins) {
						matchTeamHash[tieHash[points][i]].loss++;
						matchTeamHash[tieHash[points][i]].points += window.ELITE_DODGEBALL.CONSTANTS.LOSS_VALUE;
					}
				}

				matchTeams.push(matchTeamHash[tieHash[points][i]]);
			}

			matchTeams.sort(window.ELITE_DODGEBALL.pointSort);

			// Ratio wins/loss if match points are the same

			var matchRatioTieHash = window.ELITE_DODGEBALL.buildTieHash(matchTeamHash, matchTeamHash);

			for (var i = 0; i < tieCount; i++) {
				matchTeamHash[matchTeams[i].id].points += i * matchSpotValue;
			}

			for (var matchRatioPoints in matchRatioTieHash) {
				if (Array.isArray(matchRatioTieHash[matchRatioPoints]) === false) {
					continue;
				}

				var matchRatioTieCount = matchRatioTieHash[matchRatioPoints].length,
					matchRatioSpotValue = matchSpotValue / matchRatioTieCount,
					matchRatioTeams = [];

				for (var i = 0; i < matchRatioTieCount; i++) {
					matchTeamHash[matchRatioTieHash[matchRatioPoints][i]].points = matchTeamHash[matchRatioTieHash[matchRatioPoints][0]].points;
					matchTeamHash[matchRatioTieHash[matchRatioPoints][i]].ratio = window.ELITE_DODGEBALL.makeRatio(matchTeamHash[matchRatioTieHash[matchRatioPoints][i]].game_wins, matchTeamHash[matchRatioTieHash[matchRatioPoints][i]].game_loss);

					matchRatioTeams.push(matchTeamHash[matchRatioTieHash[matchRatioPoints][i]]);
				}

				matchRatioTeams.sort(window.ELITE_DODGEBALL.ratioSort);

				for (var i = 0; i < matchRatioTieCount; i++) {
					teamHash[matchRatioTeams[i].id].points += i * matchRatioSpotValue;
				}
			}

			// Ratio per-wins/per-loss if wins/loss ratio is the same
		}
	}

	// TODO: Detect internal ties
	// http://www.usatt.net/rules/stumpump/stump97/11.shtml
	// https://www.allabouttabletennis.com/calculation-of-group-ranking.html

	return groupTeamHash;
};

/**
 * Detect ties in a set of games.
 * @param {Object} trackingHash
 * @param {Object} teamHash
 * @returns {Object}
 */
window.ELITE_DODGEBALL.buildTieHash = function buildTieHash(trackingHash, teamHash) {
	var tieHash = {};

	for (var eventDivisionTeamId in trackingHash) {
		if (teamHash[eventDivisionTeamId].points in tieHash === false) {
			tieHash[teamHash[eventDivisionTeamId].points] = eventDivisionTeamId;
		} else if (Array.isArray(tieHash[teamHash[eventDivisionTeamId].points]) === false) {
			tieHash[teamHash[eventDivisionTeamId].points] = [tieHash[teamHash[eventDivisionTeamId].points], eventDivisionTeamId];
		} else {
			tieHash[teamHash[eventDivisionTeamId].points].push(eventDivisionTeamId);
		}
	}

	return tieHash;
};

/**
 * Normalize a ratio of `wins` and `loss`.
 * @param {number} wins
 * @param {number} loss
 * @returns {number}
 */
window.ELITE_DODGEBALL.makeRatio = (function () {
	const SHIFT_VALUE = 1000;

	return function makeRatio(wins, loss) {
		var ratio = wins / loss;

		if (isNaN(ratio) === true) {
			ratio = -Infinity;
		}

		return ratio;
	};
})();

/**
 * Sort by `ratio` attribute.
 * @param {Object} a
 * @param {Object} b
 * @returns {number}
 */
window.ELITE_DODGEBALL.ratioSort = function ratioSort(a, b) {
	if (a.ratio === b.ratio) {
		return window.ELITE_DODGEBALL.idSort(a, b);
	}
	return a.ratio > b.ratio ? 1 : -1;
};

/**
 * Sort by `points` attribute.
 * @param {Object} a
 * @param {Object} b
 * @returns {number}
 */
window.ELITE_DODGEBALL.pointSort = function pointSort(a, b) {
	if (a.points === b.points) {
		return window.ELITE_DODGEBALL.idSort(a, b);
	}
	return a.points > b.points ? 1 : -1;
};

/**
 * Sort by `id` attribute.
 * @param {Object} a
 * @param {Object} b
 * @returns {number}
 */
window.ELITE_DODGEBALL.idSort = function idSort(a, b) {
	if (a.id === b.id) {
		return 0;
	}
	return a.id > b.id ? 1 : -1;
};
