/**
 * Dashboard functionality for HiveBuzz
 * Manages trending posts scrolling and activity refresh
 */

class DashboardManager {
	constructor() {
		// Elements
		this.trendingPostsScroll = document.querySelector(
			".trending-posts-scroll"
		);
		this.scrollLeftBtn = document.querySelector(".scroll-left");
		this.scrollRightBtn = document.querySelector(".scroll-right");
		this.refreshActivityBtn = document.getElementById("refresh-activity");
		this.refreshStatsBtn = document.getElementById("refresh-stats");
		this.walletActionBtns = document.querySelectorAll(".wallet-action-btn");

		// Initialize components if they exist
		this.initTrendingPostsScroll();
		this.initActivityRefresh();
		this.initStatsRefresh();
		this.initWalletActions();

		// Add error handling for dates
		this.fixDateDisplay();
	}

	/**
	 * Initialize trending posts scroll functionality
	 */
	initTrendingPostsScroll() {
		if (
			!this.trendingPostsScroll ||
			!this.scrollLeftBtn ||
			!this.scrollRightBtn
		) {
			return;
		}

		// Scroll up/down when buttons are clicked
		this.scrollLeftBtn.addEventListener("click", () => {
			this.trendingPostsScroll.scrollBy({
				top: -100,
				behavior: "smooth",
			});
		});

		this.scrollRightBtn.addEventListener("click", () => {
			this.trendingPostsScroll.scrollBy({
				top: 100,
				behavior: "smooth",
			});
		});

		// Update scroll button states on scroll
		this.trendingPostsScroll.addEventListener("scroll", () => {
			this.updateScrollButtonStates();
		});

		// Initially check for overflow and update button states
		window.addEventListener("load", () => {
			this.updateScrollControlsVisibility();
			this.updateScrollButtonStates();
		});

		// Update on resize
		window.addEventListener("resize", () => {
			this.updateScrollControlsVisibility();
		});

		// Initial check
		setTimeout(() => {
			this.updateScrollControlsVisibility();
			this.updateScrollButtonStates();
		}, 500);
	}

	/**
	 * Update visibility of scroll controls based on content overflow
	 */
	updateScrollControlsVisibility() {
		if (!this.trendingPostsScroll) return;

		const hasOverflow =
			this.trendingPostsScroll.scrollHeight >
			this.trendingPostsScroll.clientHeight;
		const scrollControls = document.querySelector(".scroll-controls");

		if (scrollControls) {
			// Only show controls if there's content to scroll
			scrollControls.style.display = hasOverflow ? "block" : "none";
		}
	}

	/**
	 * Update states of scroll buttons based on scroll position
	 */
	updateScrollButtonStates() {
		if (
			!this.trendingPostsScroll ||
			!this.scrollLeftBtn ||
			!this.scrollRightBtn
		) {
			return;
		}

		const atTop = this.trendingPostsScroll.scrollTop <= 5;
		const atBottom =
			this.trendingPostsScroll.scrollTop +
				this.trendingPostsScroll.clientHeight >=
			this.trendingPostsScroll.scrollHeight - 5;

		// Update visual state and accessibility attributes
		this.scrollLeftBtn.disabled = atTop;
		this.scrollRightBtn.disabled = atBottom;

		this.scrollLeftBtn.setAttribute("aria-disabled", atTop);
		this.scrollRightBtn.setAttribute("aria-disabled", atBottom);

		this.scrollLeftBtn.style.opacity = atTop ? "0.3" : "0.7";
		this.scrollRightBtn.style.opacity = atBottom ? "0.3" : "0.7";
	}

	/**
	 * Initialize activity refresh button
	 */
	initActivityRefresh() {
		if (!this.refreshActivityBtn) {
			return;
		}

		this.refreshActivityBtn.addEventListener("click", () => {
			// Show loading spinner
			this.refreshActivityBtn.innerHTML =
				'<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
			this.refreshActivityBtn.disabled = true;

			// Reload the page to refresh activity data
			setTimeout(() => {
				window.location.reload();
			}, 500);
		});
	}

	/**
	 * Initialize stats refresh button
	 */
	initStatsRefresh() {
		if (!this.refreshStatsBtn) {
			return;
		}

		this.refreshStatsBtn.addEventListener("click", () => {
			// Show loading spinner
			this.refreshStatsBtn.innerHTML =
				'<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';
			this.refreshStatsBtn.disabled = true;

			// In a real implementation, you would make an AJAX call to refresh stats
			// For simplicity, we'll just reload the page
			setTimeout(() => {
				window.location.reload();
			}, 500);
		});
	}

	/**
	 * Initialize wallet action buttons
	 */
	initWalletActions() {
		if (!this.walletActionBtns.length) {
			return;
		}

		this.walletActionBtns.forEach((btn) => {
			btn.addEventListener("click", () => {
				const action = btn.getAttribute("data-action");

				// Direct check for hive_keychain - more reliable than the helper
				const isKeychainAvailable =
					typeof window.hive_keychain !== "undefined";

				if (!isKeychainAvailable) {
					alert(
						"Hive Keychain browser extension is required for wallet operations.\n\nPlease install it from the Chrome Web Store or Firefox Add-ons store."
					);
					return;
				}

				// Navigate to wallet page with specific action
				window.location.href = `/wallet#${action}`;
			});
		});
	}

	/**
	 * Fix any date display issues
	 */
	fixDateDisplay() {
		// Find any elements with datetime display issues
		document.querySelectorAll(".text-muted small").forEach((el) => {
			if (el.innerText.includes("object")) {
				// Replace with generic date
				el.innerText = "Recent";
			}
		});
	}
}

// Initialize the dashboard when the DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
	const dashboard = new DashboardManager();
});
