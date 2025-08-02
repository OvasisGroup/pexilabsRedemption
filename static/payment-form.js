jQuery(function ($) {
  "use strict";

  const KPSPaymentForm = {
    init: function () {
      this.form = $("#kps-payment-form");
      this.submitButton = this.form.find('button[type="submit"]');
      this.amountInput = this.form.find("#amount");
      this.currencySelect = this.form.find("#currency");
      this.alertContainer = this.form.find(".alert-container");
      this.testDataButton = $("#fill-test-data");
      this.debug = kpsPaymentParams?.debug || false;

      this.initializeForm();
      this.bindEvents();
      this.log("Payment form initialized");
    },

    initializeForm: function () {
      // Initialize currency formatter
      this.currencyFormatter = new Intl.NumberFormat(undefined, {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });

      // Populate form with shortcode data
      this.populateShortcodeData();

      // Format amount on load
      this.formatAmount();

      // Update currency symbol
      this.updateCurrencySymbol();

      // Apply readonly and hidden field logic
      this.applyFieldRestrictions();

      // Initialize test mode if enabled
      if (kpsPaymentParams?.testMode) {
        this.testDataButton.show();
      } else {
        this.testDataButton.hide();
      }
    },

    bindEvents: function () {
      this.form.on("submit", this.handleSubmit.bind(this));
      this.amountInput.on("input", this.handleAmountInput.bind(this));
      this.amountInput.on("blur", this.handleAmountBlur.bind(this)); // Add blur handler
      this.currencySelect.on("change", this.handleCurrencyChange.bind(this));

      // Add input validation events
      this.form
        .find("input[required], select[required]")
        .on("input change", this.validateField.bind(this));

      // Phone number formatting
      this.form.find("#phone").on("input", this.formatPhoneNumber.bind(this));

      // Test data button
      this.testDataButton.on("click", this.fillTestData.bind(this));
    },

    handleSubmit: function (e) {
      e.preventDefault();

      if (!this.validateForm()) {
        return;
      }

      this.showLoading();
      this.clearAlerts();

      const formData = new FormData(this.form[0]);
      formData.append("action", "kps_create_payment");
      formData.append("nonce", kpsPaymentParams.nonce);

      this.log("Submitting payment form", Object.fromEntries(formData));

      $.ajax({
        url: kpsPaymentParams.ajaxUrl,
        type: "POST",
        data: formData,
        processData: false,
        contentType: false,
        success: this.handleSubmitSuccess.bind(this),
        error: this.handleSubmitError.bind(this),
      });
    },

    handleSubmitSuccess: function (response) {
      this.log("Server response", response);

      if (response.success) {
        // Redirect to checkout page
        window.location.href = response.data.checkout_url;
      } else {
        this.showError(response.data.message || "Payment creation failed");
        this.hideLoading();
      }
    },

    handleSubmitError: function (xhr, status, error) {
      this.log("Ajax error", { status, error, xhr });
      this.showError(
        "An error occurred while processing your request. Please try again."
      );
      this.hideLoading();
    },

    validateForm: function () {
      let isValid = true;
      const requiredFields = this.form.find(
        "input[required], select[required]"
      );

      requiredFields.each((i, field) => {
        if (!this.validateField({ target: field })) {
          isValid = false;
        }
      });

      // Validate amount
      const amount = parseFloat(this.amountInput.val());
      if (isNaN(amount) || amount <= 0) {
        this.showFieldError(this.amountInput, "Please enter a valid amount");
        isValid = false;
      }

      // Validate email format
      const emailInput = this.form.find("#customer_email");
      if (emailInput.length && !this.isValidEmail(emailInput.val())) {
        this.showFieldError(emailInput, "Please enter a valid email address");
        isValid = false;
      }

      return isValid;
    },

    validateField: function (e) {
      const field = $(e.target);
      const value = field.val().trim();

      if (field.prop("required") && !value) {
        this.showFieldError(field, "This field is required");
        return false;
      }

      this.clearFieldError(field);
      return true;
    },

    showFieldError: function (field, message) {
      const errorDiv = field.next(".field-error");
      if (errorDiv.length) {
        errorDiv.text(message);
      } else {
        field.after(
          `<div class="field-error text-red-500 text-sm mt-1">${message}</div>`
        );
      }
      field.addClass("border-red-500");
    },

    clearFieldError: function (field) {
      field.next(".field-error").remove();
      field.removeClass("border-red-500");
    },

    handleAmountInput: function (e) {
      // Allow continuous typing - only validate input
      let value = this.amountInput.val();

      // Remove any non-numeric characters except decimal point
      let cleanValue = value.replace(/[^\d.]/g, "");

      // Ensure only one decimal point
      const parts = cleanValue.split(".");
      if (parts.length > 2) {
        cleanValue = parts[0] + "." + parts.slice(1).join("");
      }

      // Limit decimal places to 2
      if (parts.length === 2 && parts[1].length > 2) {
        cleanValue = parts[0] + "." + parts[1].substring(0, 2);
      }

      // Update the input value if it changed
      if (cleanValue !== value) {
        this.amountInput.val(cleanValue);
      }
    },

    formatAmount: function () {
      let value = this.amountInput.val().replace(/[^\d.]/g, "");

      // Handle empty value
      if (!value) {
        return;
      }

      // Ensure only one decimal point
      const parts = value.split(".");
      if (parts.length > 2) {
        value = parts[0] + "." + parts.slice(1).join("");
      }

      // Convert to number and format
      const numValue = parseFloat(value);
      if (!isNaN(numValue)) {
        // Only format to 2 decimal places if there's a decimal point
        if (value.includes(".")) {
          const decimalPlaces = parts[1] ? parts[1].length : 0;
          if (decimalPlaces <= 2) {
            // Keep user's input as is if 2 or fewer decimal places
            this.amountInput.val(value);
          } else {
            // Format to 2 decimal places if more than 2
            this.amountInput.val(numValue.toFixed(2));
          }
        } else {
          // No decimal point, keep as is
          this.amountInput.val(value);
        }
      }
    },

    // Add blur handler for final formatting
    handleAmountBlur: function (e) {
      let value = this.amountInput.val().replace(/[^\d.]/g, "");

      if (value) {
        const numValue = parseFloat(value);
        if (!isNaN(numValue)) {
          // Format to 2 decimal places on blur
          this.amountInput.val(numValue.toFixed(2));
        }
      }
    },

    handleCurrencyChange: function (e) {
      this.updateCurrencySymbol();
    },

    updateCurrencySymbol: function () {
      const currency = this.currencySelect.val();
      const symbol = this.getCurrencySymbol(currency);
      const symbolSpan = this.form.find(".currency-symbol");

      // Update the symbol
      symbolSpan.text(symbol);

      // Adjust padding based on symbol length
      const input = this.form.find("#amount");
      if (symbol.length > 1) {
        input.removeClass("kps-pl-10").addClass("kps-pl-12");
      } else {
        input.removeClass("kps-pl-12").addClass("kps-pl-10");
      }
    },

    getCurrencySymbol: function (currency) {
      const symbols = {
        KES: "KSh",
        USD: "$",
        EUR: "€",
        GBP: "£",
      };
      return symbols[currency] || currency;
    },

    formatPhoneNumber: function (e) {
      let input = $(e.target);
      let value = input.val().replace(/\D/g, "");

      if (value.length > 0) {
        if (value.length <= 3) {
          value = "+" + value;
        } else if (value.length <= 6) {
          value = "+" + value.substring(0, 3) + "" + value.substring(3);
        } else {
          value =
            "+" +
            value.substring(0, 3) +
            "" +
            value.substring(3, 6) +
            "" +
            value.substring(6);
        }
      }

      input.val(value);
    },

    fillTestData: function (e) {
      e.preventDefault();
      this.log("Filling test data");

      this.form.find("#amount").val("1000.00").trigger("input");
      this.form.find("#currency").val("KES").trigger("change");
      this.form.find("#first_name").val("John");
      this.form.find("#last_name").val("Doe");
      this.form.find("#customer_email").val("test@example.com");
      this.form.find("#phone").val("+254700000000").trigger("input");
      this.form.find("#address_line1").val("123 Test Street");
      this.form.find("#address_city").val("Nairobi");
      this.form.find("#address_state").val("Nairobi");
      this.form.find("#address_country").val("KE").trigger("change");
      this.form.find("#address_postcode").val("00100");

      // Show success message
      this.showSuccess("Test data has been filled");
    },

    showLoading: function () {
      this.submitButton
        .prop("disabled", true)
        .html(
          '<svg class="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>Processing...'
        );
    },

    hideLoading: function () {
      this.submitButton.prop("disabled", false).html("Pay Now");
    },

    showError: function (message) {
      this.alertContainer.html(`
            <div class="kps-bg-red-50 kps-border-l-4 kps-border-red-400 kps-p-4 kps-mb-4">
                <div class="kps-flex">
                    <div class="kps-flex-shrink-0">
                        <svg class="kps-h-4 kps-w-4 kps-text-red-400" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                    <div class="kps-ml-2">
                        <p class="kps-text-sm kps-text-red-700">${message}</p>
                    </div>
                </div>
            </div>
        `);
    },

    showSuccess: function (message) {
      this.alertContainer.html(`
            <div class="kps-bg-green-50 kps-border-l-4 kps-border-green-400 kps-p-4 kps-mb-4">
                <div class="kps-flex">
                    <div class="kps-flex-shrink-0">
                        <svg class="kps-h-4 kps-w-4 kps-text-green-400" viewBox="0 0 20 20" fill="currentColor">
                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                    <div class="kps-ml-2">
                        <p class="kps-text-sm kps-text-green-700">${message}</p>
                    </div>
                </div>
            </div>
        `);
    },

    clearAlerts: function () {
      this.alertContainer.empty();
    },

    isValidEmail: function (email) {
      return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    },

    log: function (message, data = null) {
      if (this.debug) {
        console.log("KPS Payment Form:", message, data || "");
      }
    },

    populateShortcodeData: function () {
      const shortcodeData = kpsPaymentParams?.shortcodeData;
      if (!shortcodeData) return;

      this.log("Populating form with shortcode data", shortcodeData);

      // Map of field names to their values
      const fieldMappings = {
        amount: shortcodeData.amount,
        currency: shortcodeData.currency,
        first_name: shortcodeData.first_name,
        last_name: shortcodeData.last_name,
        email: shortcodeData.email,
        phone: shortcodeData.phone,
        address_line1: shortcodeData.address_line1,
        address_city: shortcodeData.address_city,
        address_state: shortcodeData.address_state,
        address_country: shortcodeData.address_country,
        address_postcode: shortcodeData.address_postcode,
      };

      // Populate each field if value exists
      Object.keys(fieldMappings).forEach((fieldName) => {
        const value = fieldMappings[fieldName];
        if (value && value !== "") {
          const field = this.form.find(`[data-shortcode-field="${fieldName}"]`);
          if (field.length) {
            field.val(value);

            // Trigger change event for select fields
            if (field.is("select")) {
              field.trigger("change");
            }

            // Trigger input event for input fields
            if (field.is("input")) {
              field.trigger("input");
            }
          }
        }
      });
    },

    applyFieldRestrictions: function () {
      const shortcodeData = kpsPaymentParams?.shortcodeData;
      if (!shortcodeData) return;

      this.log("Applying field restrictions", {
        readonly: shortcodeData.readonly_fields,
        hidden: shortcodeData.hidden_fields,
      });

      // Apply readonly fields
      if (
        shortcodeData.readonly_fields &&
        shortcodeData.readonly_fields.length > 0
      ) {
        shortcodeData.readonly_fields.forEach((fieldName) => {
          if (fieldName && fieldName !== "false") {
            const field = this.form.find(
              `[data-shortcode-field="${fieldName}"]`
            );
            if (field.length) {
              field.prop("readonly", true);
              field.addClass("kps-readonly");
              this.log(`Made field readonly: ${fieldName}`);
            }
          }
        });
      }

      // Apply hidden fields
      if (
        shortcodeData.hidden_fields &&
        shortcodeData.hidden_fields.length > 0
      ) {
        shortcodeData.hidden_fields.forEach((fieldName) => {
          if (fieldName && fieldName !== "false") {
            const field = this.form.find(
              `[data-shortcode-field="${fieldName}"]`
            );
            if (field.length) {
              const fieldContainer = field.closest(".kps-form-field");
              fieldContainer.hide();
              this.log(`Hidden field: ${fieldName}`);
            }
          }
        });
      }
    },
  };

  // Initialize the payment form
  KPSPaymentForm.init();
});
