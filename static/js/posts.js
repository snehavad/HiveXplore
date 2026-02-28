/**
 * Posts functionality for HiveBuzz
 * Handles post interactions, voting, dynamic updates, and infinite scrolling
 */

class PostsManager {
	constructor() {
		this.page = 1;
		this.isLoading = false;
		this.hasMorePosts = true;
		this.postsContainer = document.getElementById("posts-container");
		this.loadingIndicator = document.getElementById("loading-posts");
		this.feedType = document.body.dataset.feedType || "trending";
		this.tag = document.body.dataset.tag || "";
		this.username = document.body.dataset.username || "";
		this.initialPostCount = 25; // Initial number of posts to load
		this.loadedPostCount = 0;
		this.hasNewPosts = false; // Flag to track if new posts are available

		// Initialize components
		this.loadInitialPosts();
		this.initInfiniteScroll();

		// Initialize refresh button instead of automatic updates
		this.initRefreshButton();

		// Track the latest post ID to prevent duplicates
		this.loadedPostIds = new Set();

		// Debug flag - set to true to see debugging messages
		this.debug = false;

		// Check for new posts every minute, but only show notification, don't auto-load
		this.newPostCheckInterval = setInterval(
			() => this.checkForNewPosts(),
			60000
		);

		// Set flags to prevent auto-refresh
		window.HB_NO_AUTO_REFRESH = true;
		localStorage.setItem("noAutoRefresh", "true");
		document.documentElement.setAttribute("data-no-refresh", "true");
	}

	/**
	 * Log debug messages if debug is enabled
	 */
	log(...args) {
		if (this.debug) {
			console.log(...args);
		}
	}

	/**
	 * Initialize refresh button
	 */
	initRefreshButton() {
		const refreshButton = document.getElementById("refresh-posts");
		if (refreshButton) {
			refreshButton.addEventListener("click", async (e) => {
				e.preventDefault();
				await this.refreshPosts();
			});
		}
	}

	/**
	 * Check for new posts without displaying them
	 */
	async checkForNewPosts() {
		try {
			const timestamp = new Date().getTime(); // Add timestamp to prevent caching
			const response = await fetch(
				`/api/posts/check?feed=${this.feedType}&tag=${this.tag}&_t=${timestamp}`,
				{
					headers: {
						"X-No-Refresh": "true",
						"Cache-Control": "no-cache",
					},
				}
			);

			if (!response.ok) {
				throw new Error(
					`Error ${response.status}: ${response.statusText}`
				);
			}

			const data = await response.json();

			if (data.new_count > 0) {
				this.hasNewPosts = true;

				// Update the refresh button to indicate new posts
				const refreshButton = document.getElementById("refresh-posts");
				if (refreshButton) {
					refreshButton.classList.add("has-new-posts");
					refreshButton.innerHTML = `<i class="bi bi-arrow-clockwise"></i> Refresh (${data.new_count} new)`;
				}

				// Also show a notification if it's been at least 5 minutes since last check
				const lastNotifyTime = parseInt(
					sessionStorage.getItem("last_post_notify") || "0"
				);
				const currentTime = Date.now();
				if (currentTime - lastNotifyTime > 300000) {
					// 5 minutes
					this.showNotification(
						`${data.new_count} new post${
							data.new_count !== 1 ? "s" : ""
						} available. Click refresh to view.`,
						"info"
					);
					sessionStorage.setItem(
						"last_post_notify",
						currentTime.toString()
					);
				}
			}
		} catch (error) {
			console.error("Error checking for new posts:", error);
		}
	}

	/**
	 * Refresh posts from the server
	 */
	async refreshPosts() {
		const refreshButton = document.getElementById("refresh-posts");
		if (refreshButton) {
			// Show loading state
			const originalHtml = refreshButton.innerHTML;
			refreshButton.innerHTML =
				'<span class="spinner-border spinner-border-sm" role="status"></span> Refreshing...';
			refreshButton.disabled = true;
			refreshButton.classList.remove("has-new-posts");

			try {
				// First, get new posts only
				const newPosts = await this.loadNewPostsOnly();

				if (newPosts && newPosts.length > 0) {
					// Add new posts at the beginning with animation
					this.addPostsToContainer(newPosts, true);

					this.showNotification(
						`${newPosts.length} new post${
							newPosts.length > 1 ? "s" : ""
						} loaded`,
						"success"
					);

					// Tell server to merge new posts into main list
					await fetch(
						`/api/posts/merge?feed=${this.feedType}&tag=${this.tag}`,
						{
							method: "POST",
							headers: {
								"X-No-Refresh": "true",
								"Cache-Control": "no-cache",
							},
						}
					);
				} else {
					this.showNotification("No new posts available", "info");
				}
			} catch (error) {
				console.error("Error during refresh:", error);
				this.showNotification(
					`Failed to refresh posts: ${error.message}`,
					"danger"
				);
			} finally {
				// Reset the refresh button
				refreshButton.innerHTML =
					'<i class="bi bi-arrow-clockwise"></i> Refresh';
				refreshButton.disabled = false;
				this.hasNewPosts = false;
			}
		}
	}

	/**
	 * Load only new posts
	 */
	async loadNewPostsOnly() {
		const timestamp = new Date().getTime(); // Add timestamp to prevent caching
		try {
			const response = await fetch(
				`/api/posts/new?feed=${this.feedType}&tag=${this.tag}&new_only=true&_t=${timestamp}`,
				{
					headers: {
						"X-No-Refresh": "true",
						"Cache-Control": "no-cache",
					},
				}
			);

			if (!response.ok) {
				throw new Error(
					`Error ${response.status}: ${response.statusText}`
				);
			}

			const data = await response.json();

			if (Array.isArray(data.posts) && data.posts.length > 0) {
				// Filter out posts we already have
				const newPosts = data.posts.filter(
					(post) => post.id && !this.loadedPostIds.has(post.id)
				);

				return newPosts;
			}

			return [];
		} catch (error) {
			console.error("Error loading new posts:", error);
			throw error;
		}
	}

	/**
	 * Load new posts using AJAX
	 */
	async loadNewPosts() {
		try {
			// Use the first post ID as a reference point if available
			let firstPostId = "";

			// Fix: Check if the container has children that are elements before trying to querySelector
			if (
				this.postsContainer.children &&
				this.postsContainer.children.length > 0
			) {
				const firstPostElement =
					this.postsContainer.children[0].querySelector(
						"[data-post-id]"
					);
				if (firstPostElement) {
					firstPostId = firstPostElement.dataset.postId;
				}
			}

			console.log(`Fetching new posts, after ID: ${firstPostId}`);

			const response = await fetch(
				`/api/posts/new?feed=${this.feedType}&tag=${this.tag}&after=${firstPostId}`
			);

			if (!response.ok) {
				const errorText = await response.text();
				console.error(
					`Server error (${response.status}): ${errorText}`
				);
				throw new Error(
					`Server error ${response.status}: ${response.statusText}`
				);
			}

			const data = await response.json();
			console.log(
				`Received ${data.posts ? data.posts.length : 0} posts from API`
			);

			// Only add posts that don't already exist in the container
			if (Array.isArray(data.posts) && data.posts.length > 0) {
				// Filter out posts that don't have an ID or we already have
				const newPosts = data.posts.filter(
					(post) => post.id && !this.loadedPostIds.has(post.id)
				);

				console.log(`Found ${newPosts.length} new unique posts to add`);

				if (newPosts.length > 0) {
					this.addPostsToContainer(newPosts, true);
					this.showNotification(
						`${newPosts.length} new post${
							newPosts.length > 1 ? "s" : ""
						} loaded`,
						"success"
					);
				} else {
					this.showNotification("No new posts available", "info");
				}
			} else {
				// If posts array is undefined or empty
				console.log("No posts returned from API");
				this.showNotification("No new posts available", "info");
			}

			return true;
		} catch (error) {
			console.error("Error loading new posts:", error);
			this.showNotification(
				`Failed to load new posts: ${error.message}`,
				"danger"
			);
			throw error;
		}
	}

	/**
	 * Add new posts to the container
	 * @param {Array} posts - Array of post objects
	 * @param {Boolean} prepend - Whether to add posts to the beginning of the container
	 */
	addPostsToContainer(posts, prepend = false) {
		if (!Array.isArray(posts) || posts.length === 0) {
			console.warn("No posts to add to container");
			return;
		}

		posts.forEach((post) => {
			// Skip if we already have this post or if post has no ID
			if (!post.id || this.loadedPostIds.has(post.id)) {
				console.log(
					`Skipping post - already loaded or no ID: ${
						post.id || "undefined"
					}`
				);
				return;
			}

			// Add post ID to tracked set
			this.loadedPostIds.add(post.id);
			console.log(`Adding post ${post.id} to container`);

			const postElement = this.createPostElement(post);

			if (prepend) {
				// Add to the beginning with a fade-in animation
				postElement.style.opacity = "0";
				postElement.style.transform = "translateY(-20px)";
				this.postsContainer.insertBefore(
					postElement,
					this.postsContainer.firstChild
				);

				// Trigger animation
				setTimeout(() => {
					postElement.style.transition =
						"opacity 0.5s, transform 0.5s";
					postElement.style.opacity = "1";
					postElement.style.transform = "translateY(0)";
				}, 10);
			} else {
				// Add to the end for infinite scrolling
				this.postsContainer.appendChild(postElement);
			}

			this.initVoteButtons(postElement);
		});
	}

	/**
	 * Initialize vote buttons for a given post element
	 * @param {HTMLElement} postElement - The container for the post
	 */
	initVoteButtons(postElement) {
		const voteButtons = postElement.querySelectorAll(
			".vote-btn:not(.initialized)"
		);
		voteButtons.forEach((btn) => {
			btn.classList.add("initialized"); // Mark as initialized
			btn.addEventListener("click", async (event) => {
				event.preventDefault();

				const author = btn.dataset.author;
				const permlink = btn.dataset.permlink;

				// Check if Hive Keychain is available
				if (
					!HiveKeychainHelper ||
					!HiveKeychainHelper.isKeychainInstalled()
				) {
					this.showNotification(
						"Hive Keychain is required for voting",
						"warning"
					);
					return;
				}

				await this.castVote(btn, this.username, author, permlink);
			});
		});
	}

	/**
	 * Cast a vote on a post using Hive Keychain
	 *
	 * @param {HTMLElement} button - The vote button element
	 * @param {string} username - Current user's username
	 * @param {string} author - Post author
	 * @param {string} permlink - Post permlink
	 */
	async castVote(button, username, author, permlink) {
		// Default to 100% upvote
		const weight = 10000;

		// Show loading state
		button.disabled = true;
		const originalHtml = button.innerHTML;
		button.innerHTML =
			'<span class="spinner-border spinner-border-sm" role="status"></span>';

		try {
			// Request vote via Hive Keychain
			const response = await HiveKeychainHelper.requestVote(
				username,
				author,
				permlink,
				weight
			);

			if (response.success) {
				// Update vote count and style
				const countElement = button.querySelector(".vote-count");
				if (countElement) {
					countElement.textContent =
						parseInt(countElement.textContent || "0") + 1;
				}

				button.classList.add("active");
				this.showNotification("Vote successful!", "success");
			} else {
				// Show error message
				this.showNotification(
					"Vote failed: " + (response.message || "Unknown error"),
					"danger"
				);
			}
		} catch (error) {
			this.showNotification("Error: " + error, "danger");
		} finally {
			// Restore button state
			button.innerHTML = originalHtml;
			button.disabled = false;
		}
	}

	/**
	 * Initialize infinite scrolling
	 */
	initInfiniteScroll() {
		// Only setup if we have the container
		if (!this.postsContainer) return;

		// Set up intersection observer for infinite scrolling
		const observer = new IntersectionObserver((entries) => {
			if (
				entries[0].isIntersecting &&
				!this.isLoading &&
				this.hasMorePosts
			) {
				this.loadMorePosts();
			}
		});

		// Observe the loading indicator if it exists
		if (this.loadingIndicator) {
			observer.observe(this.loadingIndicator);
		}
	}

	/**
	 * Load initial posts
	 */
	async loadInitialPosts() {
		if (!this.postsContainer) return;

		this.isLoading = true;
		if (this.loadingIndicator) {
			this.loadingIndicator.classList.remove("d-none");
		}

		try {
			const response = await fetch(
				`/api/posts?feed=${this.feedType}&tag=${this.tag}&page=${this.page}&limit=${this.initialPostCount}`
			);

			if (!response.ok) {
				throw new Error(
					`Error ${response.status}: ${response.statusText}`
				);
			}

			const data = await response.json();

			if (Array.isArray(data.posts) && data.posts.length > 0) {
				// Append new posts to container
				data.posts.forEach((post) => {
					// Track each post ID
					if (post.id) {
						this.loadedPostIds.add(post.id);
					}

					const postElement = this.createPostElement(post);
					this.postsContainer.appendChild(postElement);
					this.initVoteButtons(postElement);
				});

				this.loadedPostCount += data.posts.length;

				// Update hasMore status
				this.hasMorePosts =
					data.hasMore &&
					this.loadedPostCount < this.initialPostCount;

				// Show a message if there are more posts but we're not loading them yet
				if (
					data.hasMore &&
					this.loadedPostCount >= this.initialPostCount
				) {
					this.showMorePostsMessage();
				}
			} else {
				// No more posts
				this.hasMorePosts = false;
				if (this.loadingIndicator) {
					this.loadingIndicator.innerHTML = "<p>No posts found</p>";
				}
			}
		} catch (error) {
			console.error("Error loading initial posts:", error);
			this.showNotification("Failed to load initial posts", "danger");
		} finally {
			this.isLoading = false;
			if (this.loadingIndicator) {
				this.loadingIndicator.classList.add("d-none");
			}
		}
	}

	/**
	 * Show a message indicating there are more posts available
	 */
	showMorePostsMessage() {
		if (this.loadingIndicator) {
			this.loadingIndicator.classList.remove("d-none");
			this.loadingIndicator.innerHTML = `
				<p>Loaded the first ${this.loadedPostCount} posts. Click refresh to check for new content.</p>
				<button class="btn btn-outline-primary mt-2" id="load-more-posts-btn">
					<i class="bi bi-plus-circle"></i> Load More
				</button>
			`;

			// Add event listener to the new button
			const loadMoreBtn = document.getElementById("load-more-posts-btn");
			if (loadMoreBtn) {
				loadMoreBtn.addEventListener("click", () => {
					this.manuallyLoadMorePosts();
				});
			}
		}
	}

	/**
	 * Manually load more posts when the user clicks the "Load More" button
	 */
	async manuallyLoadMorePosts() {
		// Hide the "Load More" button and show a loading spinner
		if (this.loadingIndicator) {
			this.loadingIndicator.innerHTML = `
				<div class="spinner-border text-primary" role="status">
					<span class="visually-hidden">Loading...</span>
				</div>
				<p class="mt-2">Loading more posts...</p>
			`;
		}

		// Enable infinite scrolling to load more posts
		this.hasMorePosts = true;

		// Load the next page
		await this.loadMorePosts();
	}

	/**
	 * Load more posts when scrolling
	 */
	async loadMorePosts() {
		// Skip if we've reached our initial post count limit and haven't explicitly requested more
		if (
			this.loadedPostCount >= this.initialPostCount &&
			!this.hasMorePosts
		) {
			return;
		}

		this.isLoading = true;

		// Show loading indicator
		if (this.loadingIndicator) {
			this.loadingIndicator.classList.remove("d-none");
		}

		try {
			// Increment page number
			this.page++;

			// Make AJAX request to load more posts
			const response = await fetch(
				`/api/posts?feed=${this.feedType}&tag=${this.tag}&page=${this.page}`
			);

			if (!response.ok) {
				throw new Error(
					`Error ${response.status}: ${response.statusText}`
				);
			}

			const data = await response.json();

			if (Array.isArray(data.posts) && data.posts.length > 0) {
				// Append new posts to container
				data.posts.forEach((post) => {
					// Skip duplicates
					if (post.id && this.loadedPostIds.has(post.id)) {
						return;
					}

					// Add to loaded IDs set
					if (post.id) {
						this.loadedPostIds.add(post.id);
					}

					const postElement = this.createPostElement(post);
					this.postsContainer.appendChild(postElement);
					this.initVoteButtons(postElement);
				});

				this.loadedPostCount += data.posts.length;

				// Determine if we should continue loading more posts
				this.hasMorePosts =
					data.hasMore &&
					(this.loadedPostCount < this.initialPostCount ||
						document.getElementById("load-more-posts-btn"));
			} else {
				// No more posts
				this.hasMorePosts = false;
				if (this.loadingIndicator) {
					this.loadingIndicator.innerHTML =
						"<p>No more posts to load</p>";
				}
			}
		} catch (error) {
			console.error("Error loading more posts:", error);
			this.showNotification("Failed to load more posts", "danger");
		} finally {
			this.isLoading = false;

			// Update loading indicator state
			if (this.loadingIndicator) {
				if (!this.hasMorePosts) {
					// No more posts to load
					setTimeout(() => {
						this.loadingIndicator.classList.add("d-none");
					}, 1000);
				} else if (this.loadedPostCount >= this.initialPostCount) {
					// We've reached our initial limit but there are more posts
					this.showMorePostsMessage();
				} else {
					// We're still loading the initial batch
					this.loadingIndicator.classList.add("d-none");
				}
			}
		}
	}

	/**
	 * Create a post element from post data
	 *
	 * @param {Object} post - Post data
	 * @returns {HTMLElement} - Post element
	 */
	createPostElement(post) {
		// Make sure we have a post ID
		if (!post.id) {
			post.id = `post-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
			console.log(`Generated random ID for post: ${post.id}`);
		}

		const col = document.createElement("div");
		col.className = "col";

		// Add class based on source (cache or blockchain)
		const sourceClass = post.from_blockchain ? "from-blockchain" : "from-cache";

		col.innerHTML = `
			<div class="card h-100 post-card ${sourceClass}" data-post-id="${post.id}">
				<div class="card-body">
					<h5 class="card-title">
						<a href="/post/${post.author}/${post.permlink}">${
			post.title
		}</a>
					</h5>
					<p class="card-text text-muted">by <a href="/profile/${
						post.author
					}">@${post.author}</a> • ${this.formatDate(
			post.created
		)}</p>
					<div class="card-text post-excerpt">${this.truncateText(
						post.body || "",
						150
					)}</div>
					<div class="post-actions mt-3">
						<button class="btn btn-sm btn-outline-primary vote-btn"
								data-author="${post.author}"
								data-permlink="${post.permlink}"
								data-username="${this.username}">
							<i class="bi bi-hand-thumbs-up"></i>
							<span class="vote-count">${
								post.vote_count || 0
							}</span>
						</button>
						<a href="/post/${post.author}/${
			post.permlink
		}" class="btn btn-sm btn-link">
							<i class="bi bi-chat"></i>
							${post.comment_count || 0} Comments
						</a>
						<span class="ms-2 text-muted">
							<i class="bi bi-currency-dollar"></i> ${
								post.payout || "0.000 HBD"
							}
						</span>
					</div>
				</div>
			</div>
		`;
		return col;
	}

	/**
	 * Format a date string or timestamp
	 * @param {string|Date} dateString - Date to format
	 * @returns {string} Formatted date
	 */
	formatDate(dateString) {
		if (!dateString) return "Recent";

		try {
			const date = new Date(dateString);
			// Check if valid date
			if (isNaN(date.getTime())) return dateString;

			// Format the date
			return date.toLocaleDateString(undefined, {
				year: "numeric",
				month: "short",
				day: "numeric",
			});
		} catch (e) {
			return dateString;
		}
	}

	/**
	 * Truncate text to a certain length and add ellipsis
	 * @param {string} text - Text to truncate
	 * @param {number} maxLength - Maximum length
	 * @returns {string} Truncated text
	 */
	truncateText(text, maxLength) {
		// Remove HTML tags
		const plainText = text.replace(/<\/?[^>]+(>|$)/g, "");
		if (plainText.length <= maxLength) return plainText;

		return plainText.substring(0, maxLength) + "...";
	}

	/**
	 * Show notification toast
	 *
	 * @param {string} message - Notification message
	 * @param {string} type - Notification type (success, danger, warning, info)
	 */
	showNotification(message, type = "info") {
		const toast = document.createElement("div");
		toast.className = "position-fixed bottom-0 end-0 p-3";
		toast.style.zIndex = "11";
		toast.innerHTML = `
			<div class="toast align-items-center text-white bg-${type} border-0" role="alert" aria-live="assertive" aria-atomic="true">
				<div class="d-flex">
					<div class="toast-body">
						<i class="bi bi-${
							type === "success"
								? "check-circle"
								: type === "danger"
								? "exclamation-circle"
								: "info-circle"
						} me-2"></i>
						${message}
					</div>
					<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
				</div>
			</div>
		`;
		document.body.appendChild(toast);

		// Initialize and show the toast
		const toastEl = new bootstrap.Toast(toast.querySelector(".toast"));
		toastEl.show();

		// Remove toast element after it hides
		toast.addEventListener("hidden.bs.toast", () => {
			document.body.removeChild(toast);
		});
	}
}

// Initialize the Posts Manager when the DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
	const postsManager = new PostsManager();

	// Make it globally accessible for debugging
	window.postsManager = postsManager;
});
