'use strict';

(function () {
	window.Set = window.Set || function (iterable) {
		var self = this,
			hash = {},
			list = [];

		this.size = 0;

		this.add = function (value) {
			if (self.has(value) === false) {
				list.push(value);
				hash[value] = true;
				self.size++;
			}
			return self;
		};

		this.clear = function () {
			for (var key in hash) {
				delete hash[key];
			}
			self.size = 0;
			list.length = 0;
		};

		this.delete = function (value) {
			var found = self.has(value);
			if (found === true) {
				delete hash[value];
				list.splice(list.indexOf(value), 1);
				self.size--;
			}
			return found;
		};

		this.entries = function () {
			var ret = [];
			for (var key in hash) {
				ret.push([key, key]);
			}
			return ret;
		};

		this.has = function (value) {
			return value in hash;
		};

		this.keys = function () {
			return list;
		};

		this.values = function () {
			return list;
		};

		this.forEach = function (callbackFn, thisArg) {
			if (thisArg === undefined) {
				thisArg = this;
			}
			for (var i = 0; i < self.size; i++) {
				callbackFn.bind(thisArg, list[i]);
			}
		};

		for (let item of iterable) {
			this.add(item);
		}
	};

	Array.prototype.map = Array.prototype.map || function (callback/*, thisArg*/) {
		if (this == null) {
			throw new TypeError('this is null or not defined');
		}

		var thisArg,
			thisObj = Object(this),
			thisLen = thisObj.length >>> 0;

		if (typeof callback !== 'function') {
			throw new TypeError(callback + ' is not a function');
		}

		if (arguments.length > 1) {
			thisArg = arguments[1];
		}

		var arrayValues = new Array(thisLen);

		for (var i = 0; i < thisLen; i++) {
			if (i in thisObj) {
				arrayValues[i] = callback.call(thisArg, thisObj[i], i, thisObj);
			}
		}

		return arrayValues;
	};

	if (!Array.prototype.reduce) {
		Object.defineProperty(Array.prototype, 'reduce', {
			value: function (callback /*, initialValue*/) {
				if (this === null) {
					throw new TypeError('Array.prototype.reduce called on null or undefined');
				}

				if (typeof callback !== 'function') {
					throw new TypeError(callback + ' is not a function');
				}

				var value,
					k = 0,
					thisObj = Object(this),
					thisLen = o.length >>> 0;

				if (arguments.length >= 2) {
					value = arguments[1];
				} else {
					while (k < thisLen && !(k in thisObj)) {
						k++;
					}

					if (k >= thisLen) {
						throw new TypeError('Reduce of empty array with no initial value');
					}

					value = thisObj[k++];
				}

				while (k < thisLen) {
					if (k in thisObj) {
						value = callback(value, thisObj[k], k, thisObj);
					}
					k++;
				}

				return value;
			},
		});
	}

	if (!String.prototype.includes) {
		String.prototype.includes = function(search, start) {
			if (typeof start !== 'number') {
				start = 0;
			}

			if (start + search.length > this.length) {
				return false;
			} else {
				return this.indexOf(search, start) !== -1;
			}
		};
	}
})();
