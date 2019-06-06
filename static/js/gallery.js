'use strict';

function Popper(list) {
	var self = this,
		by_id = {},
		total = list.length,
		current = 0,
		showing = false;

	this.wrap = document.createElement('div');
	this.wrap.className = 'popper';
	this.wrap.innerHTML = '<img tabindex="0" class="vertical-center" /><span></span><a href="#">x</a>';
	document.body.appendChild(this.wrap);

	this.image = this.wrap.querySelector('img');
	this.blurb = this.wrap.querySelector('span');
	this.xbtn = this.wrap.querySelector('a');

	this.wrap.addEventListener('click', function(e){
		self.hashReset();
	});
	this.image.addEventListener('click', function(e){
		e.stopPropagation();
		self.next();
	});

	this.image.addEventListener('keydown', function(e){
		var key = e.charCode || e.keyCode || e.which;
		if (key === 27) {
			e.preventDefault();
			window.location.hash = '';
		} else if (key === 39 && showing === true) {
			e.preventDefault();
			self.next();
		} else if (key === 37 && showing === true) {
			e.preventDefault();
			self.prev();
		}
	});

	this.next = function(){
		current++;
		if (current >= total) {
			current = 0;
		}
		window.location.hash = self.hashParse(list[current].id);
	};

	this.prev = function(){
		current--;
		if (current < 0) {
			current = total - 1;
		}
		window.location.hash = self.hashParse(list[current].id);
	};

	this.show = function(id){
		var el = document.querySelector('#image' + id);
		if (el) {
			showing = true;
			this.image.src = self.getAttribute(el, 'data-path');

			this.wrap.className = 'popper show';
			document.body.className = 'popper-body';

			this.image.focus();
			current = parseInt(self.getAttribute(el, 'data-index'), 10);
			this.blurb.innerHTML = (current + 1) + ' of ' + total;

			return true;
		}

		return false;
	};

	this.hide = function(){
		showing = false;
		document.body.className = '';
		this.wrap.className = 'popper';
		this.image.blur();
	};

	this.isShowing = function(){
		return showing;
	};

	this.getAttribute = function(el, attr){
		if (attr in el) {
			return el[attr];
		} else {
			return el.getAttribute(attr);
		}
	};

	this.hashWatch = function(e){
		if (window.location.hash !== '') {
			if (self.show(window.location.hash.replace('#', '')) === false) {
				window.location.hash = '';
			}
		} else {
			self.hide();

			if (e !== undefined) {
				var eid = self.URLParse(e.oldURL),
					elem = by_id[eid],
					offset = totalOffset(elem);
				window.scrollTo(window.scrollX, offset.top - ((offset.view.height - elem.offsetHeight) / 2));
			}
		}
	};

	this.hashReset = function(){
		window.location.hash = '';
	};

	this.hashParse = function(hash){
		var res = hash.match(/^image(\d+)$/);
		if (res) {
			return res[1];
		}
		return false;
	};

	this.URLParse = function(url){
		var res = url.match(/#(\d+)$/);
		if (res) {
			return res[1];
		}
		return false;
	};

	for (var i = 0; i < total; i++) {
		by_id[this.hashParse(list[i].id)] = list[i]
	}
}

(function () {
	var pop = new Popper(document.querySelectorAll('#container .image-list a'));

	window.addEventListener('hashchange', pop.hashWatch);

	document.querySelector('#container').addEventListener('click', function(e){
		var iid = pop.hashParse(e.target.id);
		if (iid !== false) {
			e.preventDefault();
			window.location.hash = iid;
		}
	});

	pop.hashWatch();

	var bLazy = new Blazy({
		selector: 'a[data-path]',
	});
})();
