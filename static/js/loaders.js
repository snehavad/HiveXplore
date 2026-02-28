/**
 * Loading State Manager for HiveBuzz
 * Handles showing and hiding loading indicators and states
 */
class LoadingManager {
	/**
	 * Initialize Loading Manager
	 */
	constructor() {
		this.loaders = {};
		this.defaultOptions = {
			size: "md", // sm, md, lg
			message: "Loading...",
			overlay: false,
			spinnerColor: "var(--accent-primary)",
			useSvg: true,
		};
	}

	/**
	 * Show a loading indicator in a container
	 * @param {string|HTMLElement} container - Container selector or element
	 * @param {Object} options - Loading options
	 * @returns {string} Loader ID for later reference
	 */
	showLoader(container, options = {}) {
		// Merge options with defaults
		const config = { ...this.defaultOptions, ...options };

		// Get the container element
		let containerEl;
		if (typeof container === "string") {
			containerEl = document.querySelector(container);
		} else {
			containerEl = container;
		}

		if (!containerEl) {
			console.warn("Loading container not found:", container);
			return null;
		}

		// Generate a loader ID
		const loaderId = `loader-${Math.random()
			.toString(36)
			.substring(2, 10)}`;

		// Create the loader element
		const loaderEl = document.createElement("div");
		loaderEl.className = `loader-container loader-${config.size}`;
		loaderEl.id = loaderId;

		if (config.overlay) {
			loaderEl.classList.add("loader-overlay");

			// Save original position if needed
			if (getComputedStyle(containerEl).position === "static") {
				containerEl.dataset.originalPosition = "static";
				containerEl.style.position = "relative";
			}
		}

		// Create the loader content
		if (config.useSvg) {
			// Use SVG loader
			loaderEl.innerHTML = `
                <div class="loader-spinner">
                    <img src="${this._getLoaderSvgUrl()}" alt="Loading" width="${this._getSizeInPixels(
				config.size
			)}">
                </div>
                ${
					config.message
						? `<div class="loader-message">${config.message}</div>`
						: ""
				}
            `;
		} else {
			// Use CSS spinner
			loaderEl.innerHTML = `
                <div class="loader-spinner">
                    <div class="spinner" style="border-color: ${
						config.spinnerColor
					}"></div>
                </div>
                ${
					config.message
						? `<div class="loader-message">${config.message}</div>`
						: ""
				}
            `;
		}

		// Add to container
		containerEl.appendChild(loaderEl);

		// Store reference
		this.loaders[loaderId] = {
			element: loaderEl,
			container: containerEl,
			config: config,
		};

		return loaderId;
	}

	/**
	 * Hide a specific loader by ID
	 * @param {string} loaderId - Loader ID
	 */
	hideLoader(loaderId) {
		if (!this.loaders[loaderId]) return;

		const loader = this.loaders[loaderId];

		// Add fadeout class
		loader.element.classList.add("loader-fadeout");

		// Remove after animation
		setTimeout(() => {
			// Restore original position if needed
			if (
				loader.config.overlay &&
				loader.container.dataset.originalPosition
			) {
				loader.container.style.position =
					loader.container.dataset.originalPosition;
				delete loader.container.dataset.originalPosition;
			}

			// Remove the loader element
			if (loader.element.parentNode) {
				loader.element.parentNode.removeChild(loader.element);
			}

			// Remove from tracked loaders
			delete this.loaders[loaderId];
		}, 300); // Match CSS transition duration
	}

	/**
	 * Replace content with loading state and restore when promise resolves
	 * @param {string|HTMLElement} container - Container selector or element
	 * @param {Promise} promise - Promise to wait for
	 * @param {Object} options - Loading options
	 * @returns {Promise} The original promise
	 */
	async withLoading(container, promise, options = {}) {
		// Get the container element
		let containerEl;
		if (typeof container === "string") {
			containerEl = document.querySelector(container);
		} else {
			containerEl = container;
		}

		if (!containerEl) {
			console.warn("Loading container not found:", container);
			return promise;
		}

		// Save original content
		const originalContent = containerEl.innerHTML;

		// Show loader
		const loaderId = this.showLoader(containerEl, options);

		try {
			// Wait for promise
			const result = await promise;

			// Hide loader
			this.hideLoader(loaderId);

			// Return result
			return result;
		} catch (error) {
			// Hide loader
			this.hideLoader(loaderId);

			// Rethrow error
			throw error;
		}
	}

	/**
	 * Convert size name to pixels
	 * @param {string} size - Size name (sm, md, lg)
	 * @returns {number} Size in pixels
	 */
	_getSizeInPixels(size) {
		const sizes = {
			sm: 24,
			md: 48,
			lg: 96,
		};
		return sizes[size] || 48;
	}

	/**
	 * Get the URL for the loader SVG
	 * @returns {string} URL to the loader SVG
	 */
	_getLoaderSvgUrl() {
		return "/static/img/illustrations/loading.svg";
	}
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
	window.loadingManager = new LoadingManager();
});
