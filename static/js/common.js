/**
 * Common functionality for HiveBuzz
 * Enhanced version to prevent automatic page reloads on specific pages
 */

// URL patterns that should not be automatically refreshed
const noRefreshUrls = ["/posts", "/post/"];

// Initialize with a higher priority than other scripts
(function () {
	// Check if the current URL is one that should not be auto-refreshed
	const currentPath = window.location.pathname;
	const isNoRefreshPage = noRefreshUrls.some((pattern) =>
		currentPath.includes(pattern)
	);

	if (isNoRefreshPage) {
		console.log("Auto-refresh prevention activated for:", currentPath);
		disableAutoRefresh();
	}
})();

// Disable automatic refresh for specific pages
function disableAutoRefresh() {
	// Set flags
	window.HB_NO_AUTO_REFRESH = true;
	localStorage.setItem("noAutoRefresh", "true");
	document.documentElement.setAttribute("data-no-refresh", "true");

	// Add to body class as soon as it's available
	if (document.body) {
		document.body.classList.add("no-auto-refresh");
	} else {
		document.addEventListener("DOMContentLoaded", function () {
			document.body.classList.add("no-auto-refresh");
		});
	}

	// Block history API manipulation
	const originalPushState = history.pushState;
	const originalReplaceState = history.replaceState;

	history.pushState = function () {
		console.log("Intercepted history.pushState");
		const url = arguments[2];
		if (url && typeof url === "string" && !url.includes("?")) {
			return originalPushState.apply(this, arguments);
		}
		console.log("Blocked history.pushState that might cause refresh");
		return;
	};

	history.replaceState = function () {
		console.log("Intercepted history.replaceState");
		const url = arguments[2];
		if (url && typeof url === "string" && !url.includes("?")) {
			return originalReplaceState.apply(this, arguments);
		}
		console.log("Blocked history.replaceState that might cause refresh");
		return;
	};

	// Override reload function
	const originalReload = window.location.reload;
	window.location.reload = function () {
		console.log("Page reload attempted but prevented");
		return false;
	};

	// Prevent beforeunload events
	window.addEventListener("beforeunload", function (e) {
		// Is this from an API request?
		const referrer = document.referrer;
		if (
			referrer &&
			(referrer.includes("/api/status") ||
				referrer.includes("/api/posts") ||
				referrer.includes("/api/check-feed-status"))
		) {
			console.log("Prevented unload due to API request");
			e.preventDefault();
			e.returnValue = "";
			return "";
		}
	});

	// Monkey-patch fetch
	const originalFetch = window.fetch;
	window.fetch = function (url, options) {
		// If the URL is an API check that might cause page refresh
		if (
			typeof url === "string" &&
			(url.includes("/api/status") ||
				url.includes("/api/check-feed-status"))
		) {
			console.log("Adding no-refresh headers to request:", url);

			// Add headers to prevent refresh
			options = options || {};
			options.headers = options.headers || {};
			options.headers["X-No-Refresh"] = "true";
			options.headers["Cache-Control"] = "no-cache";

			// Add cache-busting parameter
			url =
				url +
				(url.includes("?") ? "&" : "?") +
				"_t=" +
				new Date().getTime();

			// Create a wrapper promise that prevents reloads from the response
			return new Promise((resolve) => {
				originalFetch(url, options)
					.then((response) => {
						// Create a proxy for the response
						const responseProxy = new Proxy(response, {
							get: function (target, prop) {
								// Intercept the json() method
								if (prop === "json") {
									return function () {
										return target.json().then((data) => {
											// Remove any potential reload triggers
											if (
												data &&
												typeof data === "object"
											) {
												delete data.refresh;
												delete data.reload;
											}
											return data;
										});
									};
								}
								return target[prop];
							},
						});
						resolve(responseProxy);
					})
					.catch((err) => {
						console.error("Error fetching API data:", err);
						resolve(
							new Response(JSON.stringify({ error: err.message }))
						);
					});
			});
		}

		// Otherwise, proceed with the original fetch
		return originalFetch(url, options);
	};

	// Prevent automatic redirects from API responses
	const originalOpen = XMLHttpRequest.prototype.open;
	XMLHttpRequest.prototype.open = function () {
		const url = arguments[1];
		if (
			typeof url === "string" &&
			(url.includes("/api/status") ||
				url.includes("/api/check-feed-status"))
		) {
			this.addEventListener("readystatechange", function () {
				if (this.readyState === 4) {
					// Prevent any actions that might cause page reload
					console.log("XHR completed, preventing possible reload");
				}
			});
		}
		return originalOpen.apply(this, arguments);
	};

	// Disable any existing reload timers
	for (let i = 1; i < 10000; i++) {
		clearTimeout(i);
		clearInterval(i);
	}

	console.log("Auto-refresh prevention complete");
}

// Listen for DOM ready to ensure our settings are applied
document.addEventListener("DOMContentLoaded", function () {
	// Is this a no-refresh page?
	const currentPath = window.location.pathname;
	const isNoRefreshPage = noRefreshUrls.some((pattern) =>
		currentPath.includes(pattern)
	);

	if (isNoRefreshPage) {
		console.log("Reinforcing auto-refresh prevention after DOM ready");
		disableAutoRefresh();

		// Remove any potential meta refresh tags
		const metaTags = document.querySelectorAll("meta");
		metaTags.forEach((tag) => {
			if (tag.getAttribute("http-equiv") === "refresh") {
				console.log("Removing meta refresh tag", tag);
				tag.parentNode.removeChild(tag);
			}
		});

		// Disable any checkApiStatus functionality
		if (window.checkApiStatus) {
			window.checkApiStatus = function () {
				console.log("API status check prevented");
				return false;
			};
		}
	}
});
