<?php
if (!defined('ABSPATH')) {
    exit;
}

// Debug incoming request
if (defined('WP_DEBUG') && WP_DEBUG) {
    error_log('KPS Checkout Template - Request: ' . print_r($_REQUEST, true));
}

// Get payment data from URL
$payment_id = isset($_GET['payment_id']) ? intval($_GET['payment_id']) : 0;
$intent_token = isset($_GET['intent_token']) ? sanitize_text_field($_GET['intent_token']) : '';
$amount = isset($_GET['amount']) ? sanitize_text_field($_GET['amount']) : '';
$currency = isset($_GET['currency']) ? sanitize_text_field($_GET['currency']) : '';
$customer_name = isset($_GET['customer_name']) ? urldecode($_GET['customer_name']) : '';
$customer_email = isset($_GET['customer_email']) ? urldecode($_GET['customer_email']) : '';

// Debug payment data
if (defined('WP_DEBUG') && WP_DEBUG) {
    error_log('KPS Checkout Template - Payment ID: ' . $payment_id);
    error_log('KPS Checkout Template - Intent Token: ' . $intent_token);
}

// Validate payment data
if (!$payment_id || !$intent_token) {
    wp_die(__('Invalid payment session', 'kirchberg-payment-suite'));
}

// Get payment details
global $wpdb;
$payment = $wpdb->get_row($wpdb->prepare(
    "SELECT * FROM {$wpdb->prefix}kps_payments WHERE id = %d",
    $payment_id
));

// Debug payment details
if (defined('WP_DEBUG') && WP_DEBUG) {
    error_log('KPS Checkout Template - Payment Details: ' . print_r($payment, true));
}

if (!$payment) {
    wp_die(__('Payment not found', 'kirchberg-payment-suite'));
}

// Get settings
$settings = get_option('kirchberg_suite_settings', array());
$payment_settings = $settings['payment'] ?? array();
$test_mode = isset($settings['general']['test_mode']) && $settings['general']['test_mode'];

// Debug settings
if (defined('WP_DEBUG') && WP_DEBUG) {
    error_log('KPS Checkout Template - Settings: ' . print_r($settings, true));
}

// Format amount
function format_amount($amount, $currency) {
    return number_format($amount, 2) . ' ' . $currency;
}

// Get merchant info
$merchant_name = get_bloginfo('name');
$merchant_logo = get_site_icon_url();

// Decode meta data
$meta_data = json_decode($payment->meta_data, true);
$customer_name = $payment->customer_name;
$billing_address = json_decode($payment->billing_address, true);

// Define plugin directory URL
$plugin_url = plugin_dir_url(dirname(__FILE__));

// Debug URLs
if (defined('WP_DEBUG') && WP_DEBUG) {
    error_log('KPS Checkout Template - Plugin URL: ' . $plugin_url);
    error_log('KPS Checkout Template - Assets URLs: ' . print_r([
        'css' => $plugin_url . 'assets/css/checkout.css',
        'js' => $plugin_url . 'assets/js/checkout.js'
    ], true));
}

?>
<!DOCTYPE html>
<html <?php language_attributes(); ?> class="kps-h-full kps-bg-gray-100">
<head>
    <meta charset="<?php bloginfo('charset'); ?>">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo esc_html(sprintf(__('Payment - %s', 'kirchberg-payment-suite'), $merchant_name)); ?></title>
    
    <!-- Debug script -->
    <script>
        window.onerror = function(msg, url, lineNo, columnNo, error) {
            console.error('Error: ' + msg + '\nURL: ' + url + '\nLine: ' + lineNo + '\nColumn: ' + columnNo + '\nError object: ' + JSON.stringify(error));
            return false;
        };
        
        // Monitor iframe creation
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeName === 'IFRAME') {
                            console.log('Iframe added:', node);
                        }
                    });
                }
            });
        });

        document.addEventListener('DOMContentLoaded', function() {
            observer.observe(document.body, {
                childList: true,
                subtree: true
            });
        });
    </script>

    <?php 
    // Enqueue scripts early
    wp_enqueue_style('kps-style', $plugin_url . 'assets/css/style.css', array(), KPS_VERSION);
    wp_enqueue_script('jquery');
    wp_enqueue_script('kps-checkout', $plugin_url . 'assets/js/checkout.js', array('jquery'), KPS_VERSION, true);
    wp_localize_script('kps-checkout', 'kpsCheckoutParams', array(
        'ajaxUrl' => admin_url('admin-ajax.php'),
        'nonce' => wp_create_nonce('kps-payment'),
        'testMode' => $test_mode,
        'debug' => isset($settings['general']['debug']) && $settings['general']['debug'],
        'successUrl' => home_url('/kps-payment/success/'),
        'cancelUrl' => home_url('/kps-payment/cancelled/'),
        'paymentFormUrl' => home_url('/payment')
    ));
    wp_head(); 
    ?>
</head>
<body class="kps-min-h-full kps-bg-gradient-to-b kps-from-gray-50 kps-to-gray-100 kps-py-16 kps-px-4 kps-sm:px-6 kps-lg:px-8 kps-flex kps-items-center kps-justify-center">
    <div class="kps-w-full kps-max-w-2xl kps-mx-auto">
        <!-- Test Mode Banner -->
        <?php if ($test_mode): ?>
        <div class="kps-mb-2 kps-rounded kps-bg-yellow-50 kps-p-2 kps-shadow-sm">
            <div class="kps-flex kps-items-center kps-justify-center">
                <div>
                    <h3 class="kps-text-sm kps-font-semibold kps-text-yellow-800 kps-text-center">Test Mode Active</h3>
                    <div class="kps-mt-1 kps-text-sm kps-text-yellow-700 kps-text-center">
                        <p>This is a test payment. No real charges will be made.</p>
                    </div>
                </div>
            </div>
        </div>
        <?php endif; ?>

        <!-- Main Content -->
        <div class="kps-bg-white kps-rounded kps-shadow-xl kps-overflow-hidden kps-border kps-border-gray-100 kps-mb-2">
            <!-- Header -->
            <div class="kps-px-6 kps-py-6 kps-sm:px-8 kps-border-b kps-border-gray-100">
                <div class="kps-flex kps-items-center kps-justify-center">
                    <?php if ($merchant_logo): ?>
                    <img src="<?php echo esc_url($merchant_logo); ?>" alt="<?php echo esc_attr($merchant_name); ?>" class="kps-h-10 kps-w-auto">
                    <?php else: ?>
                    <h2 class="kps-text-xl kps-font-semibold kps-text-gray-900"><?php echo esc_html($merchant_name); ?></h2>
                    <?php endif; ?>
                </div>
            </div>

            <!-- Payment Details -->
            <div class="kps-px-6 kps-py-8 kps-sm:px-8">
                <div class="kps-text-center kps-mb-8">
                    <div class="kps-text-4xl kps-font-bold kps-text-gray-900 kps-mb-3">
                        <?php echo esc_html(format_amount($payment->amount, $payment->currency)); ?>
                    </div>
                    <div class="kps-text-base kps-font-medium kps-text-gray-700">
                        <?php echo esc_html($customer_name); ?>
                    </div>
                    <?php if ($billing_address): ?>
                    <div class="kps-mt-3 kps-text-sm kps-text-gray-500 kps-space-y-1">
                        <div><?php echo esc_html($billing_address['address_line1']); ?></div>
                        <?php if (!empty($billing_address['address_line2'])): ?>
                            <div><?php echo esc_html($billing_address['address_line2']); ?></div>
                        <?php endif; ?>
                        <div>
                            <?php echo esc_html($billing_address['address_city']); ?>,
                            <?php echo esc_html($billing_address['address_state']); ?>
                            <?php echo esc_html($billing_address['address_postcode']); ?>
                        </div>
                        <div><?php echo esc_html($billing_address['address_country']); ?></div>
                    </div>
                    <?php endif; ?>
                </div>

                <!-- Payment Widget -->
                <div class="kps-mt-8 kps-flex kps-justify-center">
                    <div class="kps-relative" style="width: 100%; max-width: 32rem;">
                        <!-- The Paydock widget container -->
                        <div id="kps-payment-widget"
                             data-intent-token="<?php echo esc_attr($intent_token); ?>"
                             data-payment-id="<?php echo esc_attr($payment_id); ?>"
                             data-amount="<?php echo esc_attr($payment->amount); ?>"
                             data-currency="<?php echo esc_attr($payment->currency); ?>"
                             data-customer-name="<?php echo esc_attr($customer_name); ?>"
                             data-customer-email="<?php echo esc_attr($payment->customer_email); ?>">
                        </div>
                    </div>
                </div>


                </div>
            </div>

            <!-- Footer -->
            <div class="kps-px-6 kps-py-4 kps-sm:px-8 kps-bg-gray-50">
                <div class="kps-flex kps-items-center kps-justify-center kps-space-x-2 kps-text-sm kps-text-gray-600">
                    <span class="kps-font-medium">Secure payment by <a href="https://www.ubakenya.com/" target="_blank" style="color: #D51709; text-decoration: none;"><?php _e('United Bank for Africa (UBA)', 'kirchberg-payment-suite'); ?></a></span>
                </div>
            </div>
        </div>
    </div>

    <?php wp_footer(); ?>
</body>
</html> 