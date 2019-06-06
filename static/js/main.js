'use strict';

(function () {
	var search = document.querySelector('#search'),
		input = search.querySelector('input[type="text"]'),
		icon = search.querySelector('input[type="submit"]'),
		nav = document.querySelector('#nav'),
		menu = nav.querySelector('.menu');

	document.body.addEventListener('click', function(e){
		if (nav.classList.contains('show') === true && nav.contains(e.target) === false) {
			e.preventDefault();
			e.stopPropagation();
			nav.classList.remove('show');
		} else {
			if (e.target === menu || menu.contains(e.target) === true) {
				e.preventDefault();
				nav.classList.toggle('show');
			}
		}
	});

	search.addEventListener('submit', function(e) {
		if (search.classList.contains('show') === true) {
			if (input.value === '') {
				e.preventDefault();
				input.focus();
			}
		} else {
			e.preventDefault();
			input.value = '';
			search.classList.add('show');
			input.focus();
		}
	});

	input.addEventListener('focus', function(e){
		input.value = '';
		search.classList.add('show');
	});

	input.addEventListener('blur', function(e){
		if (e.relatedTarget === icon) {
			console.log('search');
		} else {
			search.classList.remove('show');
		}
	});

	input.addEventListener('keydown', function(e){
		var k = e.keyCode || e.which;
		if (k === 27) {
			input.blur();
		}
	});

	var rot = new Rotator(document.querySelector('.carousel'));
	var pla = new Player(document.getElementById('player'), document.querySelector('.thumbs'));

	function totalOffset(elem) {
		var bodyRect = document.body.getBoundingClientRect(),
			elemRect = elem.getBoundingClientRect();

		return {
			top: elemRect.top - bodyRect.top,
			view: bodyRect
		};
	}

	var divSelect = document.querySelector('#division-select'),
		divBlocks = document.querySelectorAll('[data-division-name]');

	if (divSelect && divBlocks) {
		var divHash = {},
			HIDE_CLASS = 'hide-division';

		for (var i = 0, l = divBlocks.length; i < l; i++) {
			if (divBlocks[i].dataset.divisionName in divHash === false) {
				divHash[divBlocks[i].dataset.divisionName] = [];
			}
			divHash[divBlocks[i].dataset.divisionName].push(divBlocks[i]);
		}

		function onDivisionChange() {
			for (var divisionName in divHash) {
				toggleListClass(divHash[divisionName], divisionName !== divSelect.value);
			}
			divSelect.blur();
		}

		function toggleListClass(divList, shouldHide) {
			var classFn = shouldHide ? 'add' : 'remove';
			for (var i = 0, l = divList.length; i < l; i++) {
				divList[i].classList[classFn](HIDE_CLASS);
			}
		}

		divSelect.addEventListener('change', onDivisionChange);
		onDivisionChange();
	}
})();
