/**
 * Icon Manager for HiveBuzz
 * Handles SVG icon initialization, theme switching, and dynamic loading
 */
class IconManager {
	/**
	 * Initialize Icon Manager
	 * @param {SVGLoader} svgLoader - The SVG loader instance to use
	 */
	constructor(svgLoader) {
		this.svgLoader = svgLoader || window.svgLoader;
		this.isDarkMode = document.body.classList.contains("dark-mode");
		this.themeColor = this._getThemeColor();
		this.iconCache = {};

		// Listen for theme changes
		window.addEventListener("themeChanged", (e) => {
			this.isDarkMode = e.detail.isDark;
			this.themeColor = e.detail.themeColor || this.themeColor;
			this._updateThemedIcons();
		});
	}

	/**
	 * Initialize icons on the page
	 * @param {string} selector - CSS selector for icon containers
	 */
	initIcons(selector = "[data-icon]") {
		document.querySelectorAll(selector).forEach((container) => {
			this.loadIcon(container);
		});
	}

	/**
	 * Load a specific icon into a container
	 * @param {HTMLElement} container - Container element
	 * @param {string} [iconName] - Optional icon name to override data-icon attribute
	 * @param {Object} [options] - Options for the icon
	 */
	loadIcon(container, iconName = null, options = {}) {
		const icon = iconName || container.getAttribute("data-icon");
		if (!icon) return;

		// Set up options
		const size = options.size || container.getAttribute("data-size") || 24;
		const color =
			options.color ||
			container.getAttribute("data-color") ||
			"currentColor";
		const themed =
			options.themed || container.getAttribute("data-themed") === "true";

		// Determine the icon path
		let iconPath = `icons/${icon}.svg`;
		if (themed) {
			const theme = this.isDarkMode ? "dark" : "light";
			iconPath = `icons/${theme}/${icon}.svg`;
		}

		// Load the SVG
		if (this.svgLoader) {
			this.svgLoader
				.loadSVG(iconPath, container, {
					width: size,
					height: size,
					color: color,
				})
				.catch((err) => {
					console.warn(`Failed to load icon: ${icon}`, err);
					container.innerHTML = this._getFallbackIcon(icon);
				});
		} else {
			console.warn("SVG Loader not available");
			container.innerHTML = this._getFallbackIcon(icon);
		}
	}

	/**
	 * Get current theme color from body classes
	 * @returns {string} Theme color name
	 */
	_getThemeColor() {
		const bodyClasses = document.body.className.split(" ");
		for (const cls of bodyClasses) {
			if (cls.startsWith("theme-")) {
				return cls.replace("theme-", "");
			}
		}
		return "blue"; // Default theme color
	}

	/**
	 * Update icons that need to change when theme changes
	 */
	_updateThemedIcons() {
		document
			.querySelectorAll('[data-themed="true"]')
			.forEach((container) => {
				this.loadIcon(container);
			});

		// Update theme toggle icon
		const themeToggleIcon = document.querySelector(
			'[data-theme-icon="theme-toggle"]'
		);
		if (themeToggleIcon) {
			themeToggleIcon.innerHTML = this.isDarkMode
				? '<i class="bi bi-sun"></i>'
				: '<i class="bi bi-moon"></i>';
		}
	}

	/**
	 * Get fallback icon for when SVG loading fails
	 * @param {string} iconName - Icon name
	 * @returns {string} HTML for fallback icon
	 */
	_getFallbackIcon(iconName) {
		// Map common icon names to Bootstrap Icons as fallback
		const iconMap = {
			dashboard: "bi-grid",
			feed: "bi-rss",
			user: "bi-person",
			wallet: "bi-wallet2",
			trending: "bi-graph-up",
			settings: "bi-gear",
			heart: "bi-heart",
			comment: "bi-chat",
			share: "bi-share",
			bookmark: "bi-bookmark",
			// Add more mappings as needed
		};

		const iconClass = iconMap[iconName] || "bi-question-circle";
		return `<i class="bi ${iconClass}"></i>`;
	}
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", function () {
	// Wait for SVG loader to be ready
	setTimeout(() => {
		window.iconManager = new IconManager(window.svgLoader);
		window.iconManager.initIcons();
	}, 100);
});
