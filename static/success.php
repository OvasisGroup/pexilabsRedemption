<?php
if (!defined('ABSPATH')) {
    exit;
}

$payment_id = isset($_GET['payment_id']) ? intval($_GET['payment_id']) : 0;
$amount = isset($_GET['amount']) ? sanitize_text_field($_GET['amount']) : '';
$currency = isset($_GET['currency']) ? sanitize_text_field($_GET['currency']) : '';
$customer_name = isset($_GET['customer_name']) ? urldecode($_GET['customer_name']) : '';
$customer_email = isset($_GET['customer_email']) ? urldecode($_GET['customer_email']) : '';

// If we have a payment ID but missing other data, try to get it from the database
if ($payment_id && (!$amount || !$currency || !$customer_name || !$customer_email)) {
    global $wpdb;
    $payment = $wpdb->get_row($wpdb->prepare(
        "SELECT * FROM {$wpdb->prefix}kps_payments WHERE id = %d",
        $payment_id
    ));
    
    if ($payment) {
        if (!$amount) $amount = $payment->amount;
        if (!$currency) $currency = $payment->currency;
        if (!$customer_name) $customer_name = $payment->customer_name;
        if (!$customer_email) $customer_email = $payment->customer_email;
    }
}

?>
<!DOCTYPE html>
<html <?php language_attributes(); ?> class="kps-h-full kps-bg-gray-100">
<head>
    <meta charset="<?php bloginfo('charset'); ?>">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php esc_html_e('Payment Success', 'kirchberg-payment-suite'); ?></title>
    <style>
        body { background: #f8fafc; font-family: 'Inter', sans-serif; }
        .kps-success-container { max-width: 480px; margin: 60px auto; background: #fff; border-radius: 1.5rem; box-shadow: 0 4px 32px rgba(0,0,0,0.07); padding: 2.5rem 2rem; text-align: center; }
        .kps-success-icon { color: #22c55e; font-size: 3rem; margin-bottom: 1rem; }
        .kps-success-title { font-size: 2rem; font-weight: 700; color: #0f172a; margin-bottom: 0.5rem; }
        .kps-success-amount { font-size: 1.5rem; color: #2563eb; font-weight: 600; margin-bottom: 1.5rem; }
        .kps-success-details { color: #334155; font-size: 1.1rem; margin-bottom: 2rem; }
        .kps-success-footer { color: #64748b; font-size: 0.95rem; margin-top: 2rem; }
        .kps-btn { display: inline-block; background: #2563eb; color: #fff; padding: 0.75rem 2rem; border-radius: 0.5rem; font-weight: 600; text-decoration: none; margin-top: 1.5rem; transition: background 0.2s; }
        .kps-btn:hover { background: #1d4ed8; }
    </style>
</head>
<body>
    <div class="kps-success-container">
        <div class="kps-success-icon">&#10003;</div>
        <div class="kps-success-title"><?php esc_html_e('Payment Successful!', 'kirchberg-payment-suite'); ?></div>
        <?php if ($amount && $currency): ?>
            <div class="kps-success-amount">
                <?php echo esc_html(number_format((float)$amount, 2)) . ' ' . esc_html($currency); ?>
            </div>
        <?php endif; ?>
        <div class="kps-success-details">
            <?php if ($customer_name): ?>
                <div><strong><?php esc_html_e('Name:', 'kirchberg-payment-suite'); ?></strong> <?php echo esc_html($customer_name); ?></div>
            <?php endif; ?>
            <?php if ($customer_email): ?>
                <div><strong><?php esc_html_e('Email:', 'kirchberg-payment-suite'); ?></strong> <?php echo esc_html($customer_email); ?></div>
            <?php endif; ?>
        </div>
        <a href="<?php echo esc_url(home_url('/')); ?>" class="kps-btn"><?php esc_html_e('Return to Home', 'kirchberg-payment-suite'); ?></a>
        <div class="kps-success-footer">
            <?php esc_html_e('Thank you for your payment. If you have any questions, please contact our support.', 'kirchberg-payment-suite'); ?>
        </div>
    </div>
</body>
</html> 