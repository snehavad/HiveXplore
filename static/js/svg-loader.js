/**
 * SVG Loader for HiveBuzz
 * Provides a simple way to use the SVG icons as inline SVG elements
 */

class SVGLoader {
	/**
	 * Initialize the SVG loader with the base path to SVG files
	 * @param {string} basePath - The base path to the SVG directory
	 */
	constructor(basePath = "/static/img/") {
		this.basePath = basePath;
		this.cache = {};
	}

	/**
	 * Load an SVG from the given path and replace the target element
	 * @param {string} path - Path to the SVG file relative to basePath
	 * @param {HTMLElement} element - Element to replace with the SVG
	 * @param {Object} options - Options for the SVG
	 * @returns {Promise} - A promise that resolves when the SVG is loaded
	 */
	loadSVG(path, element, options = {}) {
		const fullPath = this.basePath + path;

		// Check if we already have the SVG in cache
		if (this.cache[fullPath]) {
			this.replaceSVG(element, this.cache[fullPath], options);
			return Promise.resolve(element);
		}

		// Fetch the SVG
		return fetch(fullPath)
			.then((response) => {
				if (!response.ok) {
					throw new Error(
						`Failed to load SVG: ${response.statusText}`
					);
				}
				return response.text();
			})
			.then((svgText) => {
				// Cache the SVG
				this.cache[fullPath] = svgText;
				// Replace the target element with the SVG
				this.replaceSVG(element, svgText, options);
				return element;
			})
			.catch((error) => {
				console.error("Error loading SVG:", error);
				// Set a fallback content
				element.innerHTML = `<span class="svg-error">${
					options.fallback || ""
				}</span>`;
				return element;
			});
	}

	/**
	 * Replace an element with the SVG content
	 * @param {HTMLElement} element - Element to replace
	 * @param {string} svgText - SVG content as text
	 * @param {Object} options - Options for the SVG
	 */
	replaceSVG(element, svgText, options = {}) {
		// Create a temporary div to hold the SVG
		const temp = document.createElement("div");
		temp.innerHTML = svgText.trim();

		// Get the SVG element
		const svg = temp.querySelector("svg");
		if (!svg) {
			console.error("No SVG found in the loaded content");
			return;
		}

		// Apply options
		if (options.className) {
			svg.classList.add(...options.className.split(" "));
		}

		if (options.color) {
			svg.style.color = options.color;
		}

		if (options.width) {
			svg.setAttribute("width", options.width);
		}

		if (options.height) {
			svg.setAttribute("height", options.height);
		}

		if (options.attributes) {
			Object.entries(options.attributes).forEach(([key, value]) => {
				svg.setAttribute(key, value);
			});
		}

		// Replace the element with the SVG
		element.innerHTML = "";
		element.appendChild(svg);
	}

	/**
	 * Initialize SVGs in the page by replacing elements with data-svg attribute
	 */
	initPageSVGs() {
		document.querySelectorAll("[data-svg]").forEach((element) => {
			const path = element.getAttribute("data-svg");
			const options = {};

			// Parse options from data attributes
			if (element.dataset.svgClass)
				options.className = element.dataset.svgClass;
			if (element.dataset.svgColor)
				options.color = element.dataset.svgColor;
			if (element.dataset.svgWidth)
				options.width = element.dataset.svgWidth;
			if (element.dataset.svgHeight)
				options.height = element.dataset.svgHeight;

			this.loadSVG(path, element, options);
		});
	}
}

// Create a global instance and initialize when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
	window.svgLoader = new SVGLoader();
	window.svgLoader.initPageSVGs();
});
