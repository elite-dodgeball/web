'use strict';

window.ELITE_DODGEBALL = window.ELITE_DODGEBALL || {};

window.ELITE_DODGEBALL.Rotator = function Rotator(el) {
	if (!el) {
		return false;
	}

	var self = this;

	this.page = 0;
	this.element = el;
	this.items = el.querySelectorAll('li');
	this.max = this.items.length;
	this.dimension = {
		width: el.offsetWidth,
		height: el.offsetHeight
	};
	this.wrapper = document.createElement('div');
	this.controls = {
		left: document.createElement('a'),
		right: document.createElement('a')
	};

	this.wrapper.className = 'rotator-wrapper';
	this.wrapper.setAttribute('style', 'width: '+this.dimension.width+'px; height: '+this.dimension.height+'px;')
	el.parentNode.insertBefore(this.wrapper, el);
	this.wrapper.appendChild(el);

	el.className = el.className + ' rotator-list';
	el.style.width = (this.dimension.width * this.max) + 'px';
	el.style.height = this.dimension.height + 'px';

	for (var i = 0, l = this.max; i < l; i++) {
		this.items[i].className = this.items[i].className + ' rotator-item';
		this.items[i].style.left = (i * this.dimension.width) + 'px';
		this.items[i].style.width = this.dimension.width + 'px';
		this.items[i].style.height = this.dimension.height + 'px';
	}

	this.controls.left.className = 'rotator-control rotator-left';
	this.controls.right.className = 'rotator-control rotator-right';
	this.wrapper.appendChild(this.controls.left);
	this.wrapper.appendChild(this.controls.right);
	this.controls.left.addEventListener('click', function(e){
		self.left();
	});
	this.controls.right.addEventListener('click', function(e){
		self.right();
	});

	this.left = function(){
		self.page--;
		if (self.page < 0) {
			self.page = self.max - 1;
		}
		update();
	};

	this.right = function(){
		self.page++;
		if (self.page > self.max - 1) {
			self.page = 0;
		}
		update();
	};

	function update() {
		el.style.left = '-' + self.page + '00%';
	}
	update();
};
