'use strict';

function Player(el, na, se) {
	if (!el) {
		return false;
	}

	var self = this,
		borderWidth = 3,
		template = '<iframe src="https://www.youtube.com/embed/{{id}}?showinfo=0" frameborder="0" width="460" height="259"></iframe>';

	if (se === undefined) {
		se = {borderWidth: borderWidth, template: template};
	}
	if (se.borderWidth !== undefined) {
		borderWidth = se.borderWidth;
	}
	if (se.template !== undefined) {
		template = se.template;
	}

	this.element = el;
	this.current = null;
	this.navigation = na;
	this.outline = document.createElement('div');

	this.outline.className = 'player-outline';
	this.outline.style.borderWidth = borderWidth + 'px';

	na.parentNode.insertBefore(this.outline, na);
	na.className = na.className + ' player-nav';
	na.parentNode.className = na.parentNode.className + ' player-wrapper';

	this.position = {
		left: na.offsetLeft,
		top: na.offsetTop
	};

	na.addEventListener('click', function(e){
		e.preventDefault();
		self.go(e.target);
	});

	this.go = function(e){
		var a = null;
		while (e !== na && e.nodeName !== 'LI') {
			if (e.nodeName === 'A') {
				a = e.href;
			}
			e = e.parentNode;
		}

		if (a !== null) {
			self.outline.style.width = e.offsetWidth + 'px';
			self.outline.style.height = e.offsetHeight + 'px';
			self.outline.style.left = (self.position.left + e.offsetLeft - borderWidth) + 'px';
			self.outline.style.top = (self.position.top + e.offsetTop - borderWidth) + 'px';

			el.innerHTML = template.replace('{{id}}', a.replace(/.+?v=(.+?)&?/, '$1'))
		}
	};

	this.go(na.querySelector('a'));
}
