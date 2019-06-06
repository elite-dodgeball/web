'use strict';

angular.module('ReggieApp', ['ngMaterial', 'ngMessages'], function ($interpolateProvider) {
	$interpolateProvider.startSymbol('[[');
	$interpolateProvider.endSymbol(']]');
}).controller('ReggieCtrl', function ($scope, $http) {
	$scope.isValid = false;
	$scope.isSubmitting = false;

	$scope.didSucceed = false;
	$scope.errorMessage = null;

	$scope.event = angular.copy(DATA.event);
	$scope.divisions = angular.copy(DATA.divisions);
	$scope.invite = angular.copy(DATA.invite);

	if ($scope.invite) {
		$scope.team = $scope.invite.team;
	}

	$scope.form = {
		totalCost: 0,
		serviceFee: 0,
		hasAccepted: false,
	};

	$scope.redirectId = null;

	$scope.inviteRedirect = function () {
		window.location.pathname = '/register/' + $scope.event.id + '/' + $scope.redirectId + '/';
	};

	const REQUIRED_CAPTAINS = 1;
	const REQUIRED_REFEREES = 2;

	$scope.checkValid = function () {
		$scope.isValid = true;
		$scope.form.totalCost = 0;

		for (var i = 0, l = $scope.divisions.length, foundSelected = 0, foundTeams = 0; i < l; i++) {
			if ($scope.divisions[i].isSelected === true) {
				foundSelected++;
				$scope.form.totalCost += $scope.divisions[i].cost;

				for (var j = 0, k = $scope.divisions[i].players.length, foundPlayer = false, captainCount = 0, refereeCount = 0; j < k; j++) {
					if ($scope.divisions[i].players[j].isAttending === true) {
						foundPlayer = true;
					}
					if ($scope.divisions[i].players[j].isCaptain === true) { 
						captainCount++;
					}
					if ($scope.divisions[i].players[j].isReferee === true) { 
						refereeCount++;
					}
				}

				if (foundPlayer === true && captainCount === REQUIRED_CAPTAINS && refereeCount === REQUIRED_REFEREES) {
					foundTeams++;
				}
			}
		}

		if (foundSelected < 1 || foundSelected !== foundTeams || $scope.form.hasAccepted !== true) {
			$scope.isValid = false;
		}

		$scope.form.serviceFee = calculateServiceFee($scope.form.totalCost);
	};

	// Stripe stuff

	var formData = {},
		stripeHandler = StripeCheckout.configure({
			locale: 'auto',
			name: 'Elite Dodgeball',
			image: '/static/img/logo.png',
			panelLabel: 'Pay with Card {{amount}}',
			zipCode: true,
			allowRememberMe: false,
			key: STRIPE_PUBLIC_KEY,
			token: function (token, args) {
				formData.token = token;

				$http.post('/register/callback/', formData).then(stripeHandlerSuccess, stripeHandlerFailure).finally(function () {
					$scope.isSubmitting = false;
				});

				$scope.$apply(function () {
					$scope.isSubmitting = true;
				});
			},
		});

	function calculateServiceFee(totalCost) {
		if (totalCost > 0) {
			return (Math.ceil((($scope.form.totalCost + STRIPE_SERVICE_FEE) / (1.0 - STRIPE_SERVICE_PERCENT)) * 100) / 100) - totalCost;
		}
		return 0;
	}

	function stripeHandlerFailure(error) {
		if ('data' in error.data) {
			var divisionHash = {};

			for (var i = 0, l = error.data.data.divisions.length; i < l; i++) {
				divisionHash[error.data.data.divisions[i].event_division_id] = error.data.data.divisions[i];
			}

			for (i = 0, l = $scope.divisions.length; i < l; i++) {
				if ($scope.divisions[i].event_division_id in divisionHash) {
					$scope.divisions[i].is_open = divisionHash[$scope.divisions[i].event_division_id].is_open;
					$scope.divisions[i].cost = divisionHash[$scope.divisions[i].event_division_id].cost;

					if ($scope.divisions[i].is_open === false) {
						$scope.divisions[i].isSelected = false;
					}
				}
			}

			$scope.checkValid();
		}

		$scope.errorMessage = error.data.message;
	}

	function stripeHandlerSuccess(data) {
		$scope.didSucceed = true;
	}

	$scope.getToken = function () {
		if ($scope.regForm.$invalid === true || $scope.isValid === false) {
			return;
		}

		$scope.errorMessage = null;

		var divisionCount = 0,
			divisionNames = [],
			selectedDivisions = [];

		for (var i = 0, l = $scope.divisions.length; i < l; i++) {
			if ($scope.divisions[i].isSelected === true) {
				var players = [];

				for (var j = 0, k = $scope.divisions[i].players.length; j < k; j++) {
					if ($scope.divisions[i].players[j].isAttending === true) {
						players.push({
							playerId: $scope.divisions[i].players[j].season_division_team_player.player_id,
							seasonDivisionTeamPlayerId: $scope.divisions[i].players[j].season_division_team_player.id,
							seasonDivisionTeamId: $scope.divisions[i].players[j].season_division_team_player.season_division_team_id,
							isCaptain: $scope.divisions[i].players[j].isCaptain,
							isReferee: $scope.divisions[i].players[j].isReferee,
						});
					}
				}

				selectedDivisions.push({
					eventDivisionId: $scope.divisions[i].event_division_id,
					divisionId: $scope.divisions[i].division_id,
					players: angular.copy(players),
				});

				divisionNames.push($scope.divisions[i].name);
				divisionCount++;
			}
		}

		var divisionString = divisionNames.splice(-1, 1)[0];

		if (divisionCount > 1) {
			divisionString = divisionNames.join(', ') + (divisionCount > 2 ? ',' : '') + ' and ' + divisionString + ' divisions';
		} else {
			divisionString += ' division';
		}

		formData = {
			teamId: $scope.team.id,
			eventId: $scope.event.id,
			inviteId: $scope.invite.id,
			divisions: selectedDivisions,
		};

		stripeHandler.open({
			email: $scope.team.email_address,
			amount: ($scope.form.totalCost + $scope.form.serviceFee) * 100,
			description: $scope.event.title + ' Registration - ' + divisionString,
		});
	};

	window.addEventListener('popstate', function () {
		stripeHandler.close();
	});
}).directive('rosterList', function ($timeout) {
	return {
		restrict: 'E',
		scope: {
			ngModel: '=',
			onChange: '&',
		},
		link: function (scope, element) {
			scope.refereesRequired = 2;

			scope.toggleCaptain = function (player) {
				player.isCaptain = !player.isCaptain;

				for (var i = 0, l = scope.ngModel.length; i < l; i++) {
					if (scope.ngModel[i] !== player) {
						scope.ngModel[i].isCaptain = false;
					}
				}

				if (typeof scope.onChange === 'function') {
					scope.onChange(player);
				}
			};

			scope.toggleReferee = function (player) {
				player.isReferee = !player.isReferee;

				for (var i = 0, l = scope.ngModel.length, refereeCount = player.isReferee ? 1 : 0; i < l; i++) {
					if (scope.ngModel[i] !== player) {
						if (refereeCount >= scope.refereesRequired) {
							scope.ngModel[i].isReferee = false;
						} else if (scope.ngModel[i].isReferee) {
							refereeCount++;
						}
					}
				}

				if (typeof scope.onChange === 'function') {
					scope.onChange(player);
				}
			};

			scope.toggleAttending = function (player) {
				if (player.isAttending === false) {
					player.isCaptain = player.isReferee = false;
				}

				if (typeof scope.onChange === 'function') {
					scope.onChange(player);
				}
			};
		},
		templateUrl: '/static/templates/reggie/roster-list.html',
	};
});
