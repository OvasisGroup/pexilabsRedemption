jQuery(document).ready(function ($) {
  "use strict";
  const pluginWidgetName = "paydock";

  function loadPaydockSDK() {
    console.log("%c[SDK] Loading Paydock SDK...", "color: blue");

    return new Promise((resolve, reject) => {
      if (window.paydock && typeof window.paydock.Checkout === "function") {
        console.log("%c[SDK] Paydock SDK already loaded.", "color: green");
        return resolve();
      }

      const script = document.createElement("script");
      script.src = "https://widget.paydock.com/sdk/latest/widget.umd.min.js";
      script.onload = () => {
        console.log("%c[SDK] Paydock SDK loaded successfully.", "color: green");
        if (window.paydock && typeof window.paydock.Checkout === "function") {
          resolve();
        } else {
          console.error(
            `[SDK] Paydock Checkout object (${pluginWidgetName}) not found after loading SDK.`,
            window.paydock
          );
          reject(
            new Error("Paydock Checkout object not found after loading SDK.")
          );
        }
      };
      script.onerror = () => {
        console.error("[SDK] Failed to load Paydock SDK.", "color: red");
        reject(new Error("Failed to load Paydock SDK."));
      };

      document.body.appendChild(script);
    });
  }

  async function initializeWidget() {
    try {
      await loadPaydockSDK();

      if (!window.paydock || typeof window.paydock.Checkout !== "function") {
        handleError("Paydock SDK is not correctly loaded or is incompatible.");
        return;
      }

      const container = $("#kps-payment-widget");
      if (!container.length) {
        console.error(
          "[Widget] FATAL: #kps-payment-widget container not found in DOM."
        );
        return;
      }

      let paymentId = container.data("payment-id");
      const nonce =
        typeof kpsCheckoutParams !== "undefined" ? kpsCheckoutParams.nonce : "";
      let intentToken = container.data("intent-token") || "";

      if (!intentToken && paymentId) {
        // Fetch intent token via AJAX if not present
        await new Promise((resolve, reject) => {
          $.ajax({
            url: kpsCheckoutParams.ajaxUrl,
            type: "POST",
            data: {
              action: "kps_fetch_payment",
              payment_id: paymentId,
              nonce: nonce,
            },
            success: function (response) {
              if (response.success && response.data && response.data.payment) {
                intentToken =
                  response.data.payment.meta_data?.intent_data?.token;
                if (intentToken) {
                  console.log("Intent token found: ", intentToken);
                  container.data("intent-token", intentToken);
                  resolve();
                } else {
                  handleError(
                    "Payment session data is missing. Please refresh the page."
                  );
                  reject("No intent token found in payment data.");
                }
              } else {
                handleError(response.data?.message || "Payment not found");
                reject(response.data?.message || "Payment not found");
              }
            },
            error: function (xhr, status, error) {
              handleError(error || "AJAX error");
              reject(error || "AJAX error");
            },
          });
        });
      }

      if (!intentToken) {
        console.error(
          "[Widget] FATAL: data-intent-token attribute missing from container and could not be fetched."
        );
        handleError(
          "Payment session data is missing. Please refresh the page."
        );
        return;
      }

      console.log(
        "%c[Widget] Initializing Paydock widget with intent token: " +
          intentToken,
        "color: blue"
      );

      // Hide loading indicator as widget initialization is about to start
      const loadingIndicator = container.parent().find(".loading-indicator");
      if (loadingIndicator.length) {
        loadingIndicator.hide();
      }

      // Debug: Check if Paydock object exists
      console.log("Paydock object:", window.paydock);
      console.log("Paydock Checkout constructor:", window.paydock?.Checkout);
      try {
        window.kpsPaydockWidget = new window.paydock.Checkout(
          "#kps-payment-widget",
          intentToken
        );

        console.log("Widget instance created:", window.kpsPaydockWidget);

        // Check if widget has required methods
        if (typeof window.kpsPaydockWidget.setEnv === "function") {
          if (kpsCheckoutParams && kpsCheckoutParams.testMode) {
            window.kpsPaydockWidget.setEnv("sandbox"); // Or 'test' depending on Paydock's exact env names
          } else {
            window.kpsPaydockWidget.setEnv("production");
          }
        }

        if (typeof window.kpsPaydockWidget.onPaymentSuccessful === "function") {
          window.kpsPaydockWidget.onPaymentSuccessful(function (data) {
            console.log("Payment successful:", data);
            const formData = new FormData();
            formData.append("action", "kps_verify_payment");
            formData.append("nonce", kpsCheckoutParams.nonce);
            formData.append("payment_id", container.data("payment-id"));
            formData.append("intent_id", data.intent_id || data.id);

            $.ajax({
              url: kpsCheckoutParams.ajaxUrl,
              type: "POST",
              data: formData,
              processData: false,
              contentType: false,
              success: function (response) {
                if (response.success) {
                  // Build success URL with payment details
                  const successUrl = new URL(kpsCheckoutParams.successUrl);

                  // Add payment details as query parameters
                  successUrl.searchParams.set(
                    "payment_id",
                    container.data("payment-id")
                  );

                  // Get payment details from container data attributes or URL parameters
                  const urlParams = new URLSearchParams(window.location.search);
                  const amount =
                    urlParams.get("amount") || container.data("amount");
                  const currency =
                    urlParams.get("currency") || container.data("currency");
                  const customerName =
                    urlParams.get("customer_name") ||
                    container.data("customer-name");
                  const customerEmail =
                    urlParams.get("customer_email") ||
                    container.data("customer-email");

                  if (amount) successUrl.searchParams.set("amount", amount);
                  if (currency)
                    successUrl.searchParams.set("currency", currency);
                  if (customerName)
                    successUrl.searchParams.set(
                      "customer_name",
                      encodeURIComponent(customerName)
                    );
                  if (customerEmail)
                    successUrl.searchParams.set(
                      "customer_email",
                      encodeURIComponent(customerEmail)
                    );

                  console.log(
                    "Redirecting to success page:",
                    successUrl.toString()
                  );
                  window.location.href = successUrl.toString();
                } else {
                  handleError(
                    response.data.message || "Payment verification failed."
                  );
                }
              },
              error: function () {
                handleError(
                  "Failed to verify payment. Please contact support."
                );
              },
            });
          });
        }

        if (typeof window.kpsPaydockWidget.onPaymentFailure === "function") {
          window.kpsPaydockWidget.onPaymentFailure(function (error) {
            console.error("Payment failure:", error);
            handleError(error.message || "An error occurred during payment.");
          });
        }

        if (typeof window.kpsPaydockWidget.onPaymentExpired === "function") {
          window.kpsPaydockWidget.onPaymentExpired(function (error) {
            console.error("Payment expired:", error);
            handleError(
              error.message || "Your payment session has expired. Please retry."
            );
          });
        }

        // Post-initialization check to see if iframe exists after a short delay
        setTimeout(() => {
          const iframe = container.find("iframe");
          if (iframe.length > 0) {
            console.log(
              "%c[Widget] SUCCESS: Iframe injected by Paydock inside #kps-payment-widget.",
              "color: green; font-weight: bold;"
            );
          } else {
            console.error(
              "%c[Widget] FAILURE: Iframe was NOT injected by Paydock.",
              "color: red; font-weight: bold;"
            );
            console.log("Container content:", container.html());
            // handleError(
            //   "Widget failed to render. The payment form could not be loaded."
            // );
          }
        }, 3000);
      } catch (widgetError) {
        console.error("Error creating Paydock widget:", widgetError);
        handleError("Failed to create payment widget: " + widgetError.message);
      }
    } catch (error) {
      console.error("[Init] Critical failure during widget init:", error);
      handleError("A critical error occurred: " + error.message);
    }
  }

  function handleError(message) {
    const container = $("#kps-payment-widget");
    container.css({
      display: "block",
      visibility: "visible",
      height: "auto",
      border: "1px solid #fca5a5",
    });
    container.empty();
    const errorDiv = $(
      `<div class="widget-error" style="padding: 1rem; margin-top: 1rem; color: #b91c1c; background-color: #fee2e2; border: 1px solid #fca5a5; border-radius: 0.5rem;"></div>`
    ).html(
      `<strong>Error:</strong> ${message}<br>Please try again or contact support.`
    );
    container.append(errorDiv);
    container.parent().find(".loading-indicator").hide();
  }

  initializeWidget();
});
