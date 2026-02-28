/**
 * QR Code Helper for HiveBuzz
 * Provides utility functions for QR code generation
 */
const QRCodeHelper = {
	/**
	 * Check if the QRCode library is available
	 * @returns {boolean} true if QRCode is available
	 */
	isAvailable: function () {
		return typeof QRCode !== "undefined" && QRCode !== null;
	},

	/**
	 * Generate a QR code in a canvas element
	 * @param {HTMLElement} element - DOM element to render QR code in
	 * @param {string} data - Data to encode in QR code
	 * @param {object} options - Options for QR code generation
	 * @returns {Promise} resolves when QR code is generated, rejects on error
	 */
	generateQRCode: function (element, data, options = { width: 200 }) {
		return new Promise((resolve, reject) => {
			if (!this.isAvailable()) {
				reject(new Error("QRCode library not loaded"));
				return;
			}

			if (!element) {
				reject(new Error("Invalid element provided"));
				return;
			}

			try {
				// Clear any previous content
				element.innerHTML = "";

				QRCode.toCanvas(element, data, options, function (error) {
					if (error) {
						reject(error);
					} else {
						resolve();
					}
				});
			} catch (e) {
				reject(e);
			}
		});
	},

	/**
	 * Generate a QR code as a data URL
	 * @param {string} data - Data to encode in QR code
	 * @param {object} options - Options for QR code generation
	 * @returns {Promise<string>} resolves with data URL, rejects on error
	 */
	generateQRDataURL: function (data, options = {}) {
		return new Promise((resolve, reject) => {
			if (!this.isAvailable()) {
				reject(new Error("QRCode library not loaded"));
				return;
			}

			try {
				QRCode.toDataURL(data, options, function (error, url) {
					if (error) {
						reject(error);
					} else {
						resolve(url);
					}
				});
			} catch (e) {
				reject(e);
			}
		});
	},

	/**
	 * Display fallback content when QR code generation fails
	 * @param {HTMLElement} element - Element to display fallback in
	 * @param {Error} error - Error that occurred
	 * @param {string} fallbackCode - Optional code to display
	 */
	displayQRFallback: function (element, error, fallbackCode = "") {
		if (!element) return;

		element.innerHTML = `
            <div class="alert alert-warning">
                <p><i class="bi bi-exclamation-triangle-fill me-2"></i> QR code generation failed</p>
                <p class="mb-1">Error: ${error.message || "Unknown error"}</p>
                ${
					fallbackCode
						? `
                <p class="mt-2 mb-1">Please use this authentication code instead:</p>
                <code class="d-block p-2 bg-light text-dark mt-2">${fallbackCode}</code>
                `
						: ""
				}
            </div>
        `;
	},
};

// Make it globally available
window.QRCodeHelper = QRCodeHelper;
