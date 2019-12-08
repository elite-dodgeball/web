'use strict';

window.ELITE_DODGEBALL = window.ELITE_DODGEBALL || {};

window.ELITE_DODGEBALL.Video = function Video(container, template) {
	var self = this;

	this.getAttribute = function(el, attr){
		if (attr in el) {
			return el[attr];
		} else {
			return el.getAttribute(attr);
		}
	};

	this.loadVideo = function(el){
		var yid = self.getAttribute(el, 'data-yid');
		if (yid) {
			el.parentNode.innerHTML = template.replace(/\[\[youtube_id\]\]/g, yid);
		}
	};

	container.addEventListener('click', function(e){
		if (self.getAttribute(e.target, 'data-yid')) {
			e.preventDefault();
			self.loadVideo(e.target);
		}
	});
};

window.ELITE_DODGEBALL.Navver = function Navver(data, container, template) {
	var self = this,
		page = 1,
		per_page = 9,
		adjacents = 1,
		total = Math.ceil(data.length / per_page);

	this.set_page = function(value){
		page = value;
		var html = '',
			prev = page - 1,
			next = page + 1;

		// Dip out if there are no pages to htmlify
		if (total < 1) {
			container.innerHTML = html;
		}

		// Add previous button
		if (prev > 0) {
			html += self.htmlify(prev, '«');
		}

		// Not enough pages to break up
		if (total < 7 + (adjacents * 2)) {
			for (var i = 1; i <= total; i++) {
				html += self.htmlify(i, i);
			}
		// Hide some of the buttons
		} else if (total > 5 + (adjacents * 2)) {
			var almost = total - 1;

			// Close to the beginning
			if (page < 1 + (adjacents * 2)) {
				for (var i = 1; i < 4 + (adjacents * 2); i++) {
					html += self.htmlify(i, i);
				}
				html += self.htmlify(false, '…') + self.htmlify(almost, almost) + self.htmlify(total, total);
			// Hide from both sides
			} else if (total - (adjacents * 2) > page && page > (adjacents * 2)) {
				html += self.htmlify(1, 1) + self.htmlify(2, 2) + self.htmlify(false, '…');
				for (var i = page - adjacents; i <= page + adjacents; i++) {
					html += self.htmlify(i, i);
				}
				html += self.htmlify(false, '…') + self.htmlify(almost, almost) + self.htmlify(total, total);
			// Close to the end
			} else {
				html += self.htmlify(1, 1) + self.htmlify(2, 2) + self.htmlify(false, '…');
				for (var i = total - (2 + (adjacents * 2)); i <= total; i++) {
					html += self.htmlify(i, i);
				}
			}
		}

		// Add next button
		if (page < total) {
			html += self.htmlify(next, '»');
		}

		container.innerHTML = html;
	};

	this.htmlify = function(page_num, label){
		if (page_num === false) {
			return template.replace(/<a .+\/a>/g, '<a>'+label+'</a>').replace(/\[\[current\]\]/g, 'nav-disabled');
		}
		if (label === page) {
			return template.replace(/<a .+\/a>/g, '<a>'+label+'</a>').replace(/\[\[current\]\]/g, 'nav-current');
		}
		return template.replace(/\[\[page_num\]\]/g, page_num).replace(/\[\[label\]\]/g, label).replace(/\[\[current\]\]/g, (label === page ? 'nav-current' : ''));
	};

	this.set_data = function(obj){
		data = obj;
		total = Math.ceil(data.length / per_page);
		window.location.hash = '#page=1';
	};

	this.hash_watch = function(){
		var res = window.location.hash.match(/\Wpage=(\d+)&?/);
		if (res) {
			self.set_page(parseInt(res[1], 10));
		} else {
			window.location.hash = '#page';
		}
	};

	window.addEventListener('hashchange', this.hash_watch);
	this.hash_watch();
};

window.ELITE_DODGEBALL.VideoList = function VideoList(data, container, template) {
	var self = this,
		page = 1,
		per_page = 9,
		offset = 0,
		total = data.length;

	this.htmlify = function(data){
		var info = '';
		for (var key in data.description) {
			info += '<p>' + (data.description[key] ? data.description[key] : '&nbsp;') + '</p>';
		}

		return template.replace(/\[\[id\]\]/g, data.id).replace(/\[\[youtube_id\]\]/g, data.youtube_id).replace(/\[\[title\]\]/g, data.title).replace(/\[\[duration\]\]/g, data.duration).replace(/\[\[description\]\]/g, info).replace(/\[\[thumbnail\]\]/g, data.thumbnail);
	};

	this.set_page = function(value){
		page = value;
		self.calc_offset();

		var html = ''
		for (var i = offset, l = offset + per_page; i < l && i < total; i++) {
			html += self.htmlify(data[i]);
		}

		container.innerHTML = html;
	};

	this.calc_offset = function(){
		offset = (page - 1) * per_page;
		return offset;
	};

	this.set_data = function(obj){
		data = obj;
		total = data.length;
		window.location.hash = '#page';
	};

	this.hash_watch = function(){
		var res = window.location.hash.match(/\Wpage=(\d+)&?/);
		if (res) {
			self.set_page(parseInt(res[1], 10));
		} else {
			window.location.hash = '#page=1';
		}
	};

	window.addEventListener('hashchange', this.hash_watch);
	this.hash_watch();
};

window.ELITE_DODGEBALL.Search = function Search(data, input, callbacks) {
	var self = this;

	if (callbacks instanceof Function === true) {
		callbacks = [callbacks]
	}

	if (callbacks instanceof Array === false) {
		return false;
	}

	this.query = function(param){
		var ret = [],
			rex = new RegExp(param.replace(/[\-\[\]\/\{\}\(\)\*\+\?\.\\\^\$\|]/g, '\\$&'), 'ig');
		for (var i in data) {
			if (data[i].title.match(rex)) {
				ret.push(data[i]);
			}
		}
		return ret;
	};

	function do_callbacks(new_data) {
		for (var i in callbacks) {
			callbacks[i](new_data);
		}
		input.scrollIntoView();
	}

	function change(e) {
		var key = e.keyCode || e.which;
		if (key === 27) {
			input.blur();
			input.value = '';
			do_callbacks(data);
		} else if (key === 13) {
			input.blur()
			do_callbacks(self.query(input.value));
		}
	}

	input.addEventListener('keydown', change);
};

(function () {
	var vlcon = document.querySelector('.video-list');

	if (vlcon) {
		var video = new window.ELITE_DODGEBALL.Video(vlcon, document.querySelector('#video-embed').innerHTML),
			list = new window.ELITE_DODGEBALL.VideoList(window.videos, vlcon, document.querySelector('#video-item').innerHTML),
			lnav = new window.ELITE_DODGEBALL.Navver(window.videos, document.querySelector('.video-nav'), document.querySelector('#video-nav').innerHTML),
			linp = new window.ELITE_DODGEBALL.Search(window.videos, document.querySelector('#video-search'), [list.set_data, lnav.set_data]);
	}
})();
