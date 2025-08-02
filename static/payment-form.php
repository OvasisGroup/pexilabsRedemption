<?php
if (!defined('ABSPATH')) {
    exit;
}

// Get settings
$settings = get_option('kirchberg_suite_settings', array());
$payment_settings = $settings['payment'] ?? array();
$test_mode = isset($payment_settings['test_mode']) && $payment_settings['test_mode'];

// Get shortcode data from JavaScript params
$shortcode_data = isset($GLOBALS['kps_shortcode_data']) ? $GLOBALS['kps_shortcode_data'] : array();

// Initialize cart variables
$has_cart = false;
$cart_total = '';
$cart_currency = '';
$cart_items = array();

if (
    class_exists('WooCommerce') &&
    function_exists('WC') &&
    WC()->cart instanceof WC_Cart
) {
    WC()->cart->calculate_totals();
    $has_cart = true;
    $cart_total = WC()->cart->get_total('raw');
    $cart_currency = get_woocommerce_currency();
    $cart_items = WC()->cart->get_cart();
}
?>

<style>
/* Payment Form Styles - Two Column Layout */
.kps-payment-form-wrapper {
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem 1rem;
}

.kps-form-container {
    background: white;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    overflow: hidden;
    border: 1px solid #e5e7eb;
    display: flex;
    min-height: 600px;
}

.kps-form-left {
    flex: 2;
    padding: 2rem;
    background: #f9fafb;
}

.kps-form-right {
    flex: 1;
    background: white;
    border-left: 1px solid #e5e7eb;
    display: flex;
    flex-direction: column;
}

.kps-form-section {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
    border: 1px solid #e5e7eb;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.kps-form-section h3 {
    font-size: 1.125rem;
    font-weight: 600;
    color: #111827;
    margin-bottom: 1.5rem;
    margin-top: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.kps-form-section h3::before {
    content: '';
    width: 4px;
    height: 20px;
    background: #3b82f6;
    border-radius: 2px;
}

.kps-form-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
}

.kps-form-grid .kps-form-field {
    flex: 1;
    min-width: 200px;
}

@media (max-width: 1024px) {
    .kps-form-container {
        flex-direction: column;
    }
    
    .kps-form-left,
    .kps-form-right {
        flex: none;
    }
    
    .kps-form-right {
        border-left: none;
        border-top: 1px solid #e5e7eb;
    }
}

@media (max-width: 767px) {
    .kps-form-grid .kps-form-field {
        flex: 1 1 100%;
    }
}

/* Right side styling */
.kps-payment-summary {
    padding: 2rem;
    flex: 1;
}

.kps-payment-summary h3 {
    font-size: 1.25rem;
    font-weight: 600;
    color: #111827;
    margin-bottom: 1.5rem;
    margin-top: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.kps-payment-summary h3::before {
    content: '';
    width: 4px;
    height: 24px;
    background: #10b981;
    border-radius: 2px;
}

.kps-summary-item {
    display: flex;
    justify-content: space-between;
    padding: 0.75rem 0;
    border-bottom: 1px solid #f3f4f6;
}

.kps-summary-item:last-child {
    border-bottom: none;
    font-weight: 600;
    font-size: 1.1rem;
    color: #111827;
    padding-top: 1rem;
    border-top: 2px solid #e5e7eb;
}

.kps-summary-label {
    color: #6b7280;
}

.kps-summary-value {
    color: #111827;
    font-weight: 500;
}

.kps-payment-actions {
    padding: 2rem;
    background: #f9fafb;
    border-top: 1px solid #e5e7eb;
}

.kps-form-button {
    width: 100%;
    background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
    color: white;
    border: none;
    padding: 1.25rem 1.5rem;
    font-size: 1.1rem;
    font-weight: 600;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.kps-form-button:hover {
    background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(59, 130, 246, 0.4);
}

.kps-form-button:disabled {
    background: #9ca3af;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
}

.kps-security-info {
    margin-top: 1.5rem;
    padding: 1rem;
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 8px;
    text-align: center;
}

.kps-security-info h4 {
    font-size: 0.875rem;
    font-weight: 600;
    color: #166534;
    margin: 0 0 0.5rem 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
}

.kps-security-info p {
    font-size: 0.75rem;
    color: #166534;
    margin: 0;
    opacity: 0.8;
}

/* Existing styles remain the same */
.kps-form-field {
    display: flex;
    flex-direction: column;
}

.kps-form-label {
    font-size: 0.875rem;
    font-weight: 500;
    color: #374151;
    margin-bottom: 0.5rem;
    display: block;
}

.kps-form-input,
.kps-form-select {
    width: 100%;
    padding: 0.75rem 1rem;
    font-size: 0.875rem;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    background-color: #ffffff;
    transition: all 0.2s ease;
    box-sizing: border-box;
    height: 44px;
}

.kps-form-input:focus,
.kps-form-select:focus {
    outline: none;
    border-color: #3b82f6;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.kps-form-input::placeholder {
    color: #9ca3af;
}

.kps-currency-input {
    position: relative;
}

.kps-currency-symbol {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: #6b7280;
    font-size: 0.875rem;
    pointer-events: none;
    z-index: 10;
}

.kps-currency-input .kps-form-input {
    padding-left: 2.5rem;
}

.kps-help-text {
    font-size: 0.75rem;
    color: #6b7280;
    margin-top: 0.5rem;
}

.kps-test-mode {
    background: #fef3c7;
    border: 1px solid #f59e0b;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 2rem;
}

.kps-test-mode h3 {
    font-size: 1rem;
    font-weight: 600;
    color: #92400e;
    margin: 0 0 0.5rem 0;
}

.kps-test-mode p {
    font-size: 0.875rem;
    color: #92400e;
    margin: 0 0 0.5rem 0;
}

.kps-test-mode button {
    background: none;
    border: none;
    color: #92400e;
    text-decoration: underline;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
}

.kps-test-mode button:hover {
    color: #78350f;
}

.kps-secure-notice {
    text-align: center;
    margin-top: 2rem;
}

.kps-secure-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: #f9fafb;
    padding: 0.5rem 1rem;
    border-radius: 9999px;
    font-size: 0.875rem;
    color: #374151;
}

.kps-secure-badge svg {
    width: 1.25rem;
    height: 1.25rem;
    color: #10b981;
}

.kps-secure-badge a {
    color: #dc2626;
    font-weight: 500;
    text-decoration: none;
}

.kps-secure-badge a:hover {
    color: #b91c1c;
}

/* Alert styling */
.alert-container {
    margin-bottom: 1.5rem;
}

.alert-container .kps-alert {
    padding: 1rem;
    border-radius: 8px;
    margin-bottom: 1rem;
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
}

.alert-container .kps-alert-error {
    background: #fef2f2;
    border: 1px solid #fecaca;
    color: #991b1b;
}

.alert-container .kps-alert-success {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    color: #166534;
}

.alert-container .kps-alert svg {
    width: 1.25rem;
    height: 1.25rem;
    flex-shrink: 0;
    margin-top: 0.125rem;
}

/* Field error styling */
.field-error {
    color: #dc2626;
    font-size: 0.75rem;
    margin-top: 0.25rem;
}

.kps-form-input.error,
.kps-form-select.error {
    border-color: #dc2626;
}

.kps-form-input.error:focus,
.kps-form-select.error:focus {
    border-color: #dc2626;
    box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
}

/* Readonly field styling */
.kps-form-input.kps-readonly,
.kps-form-select.kps-readonly {
    background-color: #f9fafb;
    color: #6b7280;
    cursor: not-allowed;
    opacity: 0.7;
}

.kps-form-input.kps-readonly:focus,
.kps-form-select.kps-readonly:focus {
    border-color: #d1d5db;
    box-shadow: none;
}
</style>

<div class="kps-payment-form-wrapper">
    <?php if ($test_mode): ?>
        <div class="kps-test-mode">
            <div style="display: flex; align-items: center; gap: 0.75rem;">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"/>
                </svg>
                <div>
                    <h3>Test Mode Active</h3>
                    <p>This is a test payment. No real charges will be made.</p>
                    <button type="button" id="fill-test-data">Fill with test data</button>
                </div>
            </div>
        </div>
    <?php endif; ?>

    <div class="kps-form-container">
        <!-- Left Column - Form Fields -->
        <div class="kps-form-left">
            <form id="kps-payment-form">
                <!-- Alert Container -->
                <div class="alert-container"></div>

                <!-- Amount and Currency -->
                <div class="kps-form-section">
                    <h3>Payment Amount</h3>
                    <div class="kps-form-grid">
                        <div class="kps-form-field">
                            <label for="currency" class="kps-form-label">Currency <span style="color: #dc2626;">*</span></label>
                            <select name="currency" 
                                    id="currency" 
                                    required
                                    class="kps-form-select"
                                    data-shortcode-field="currency">
                                <option value="">Select Currency</option>
                                <option value="USD">USD - US Dollar</option>
                                <option value="EUR">EUR - Euro</option>
                                <option value="GBP">GBP - British Pound</option>
                                <option value="JPY">JPY - Japanese Yen</option>
                                <option value="AUD">AUD - Australian Dollar</option>
                                <option value="CAD">CAD - Canadian Dollar</option>
                                <option value="CHF">CHF - Swiss Franc</option>
                                <option value="CNY">CNY - Chinese Yuan</option>
                                <option value="KES">KES - Kenyan Shilling</option>
                                <option value="NGN">NGN - Nigerian Naira</option>
                                <option value="ZAR">ZAR - South African Rand</option>
                                <option value="EGP">EGP - Egyptian Pound</option>
                                <option value="GHS">GHS - Ghanaian Cedi</option>
                                <option value="UGX">UGX - Ugandan Shilling</option>
                                <option value="TZS">TZS - Tanzanian Shilling</option>
                                <option value="RWF">RWF - Rwandan Franc</option>
                                <option value="ETB">ETB - Ethiopian Birr</option>
                                <option value="MAD">MAD - Moroccan Dirham</option>
                                <option value="TND">TND - Tunisian Dinar</option>
                                <option value="DZD">DZD - Algerian Dinar</option>
                                <option value="LYD">LYD - Libyan Dinar</option>
                                <option value="SDG">SDG - Sudanese Pound</option>
                                <option value="SOS">SOS - Somali Shilling</option>
                                <option value="DJF">DJF - Djiboutian Franc</option>
                                <option value="KMF">KMF - Comorian Franc</option>
                                <option value="MUR">MUR - Mauritian Rupee</option>
                                <option value="SCR">SCR - Seychellois Rupee</option>
                                <option value="BIF">BIF - Burundian Franc</option>
                                <option value="CDF">CDF - Congolese Franc</option>
                                <option value="XAF">XAF - Central African CFA Franc</option>
                                <option value="XOF">XOF - West African CFA Franc</option>
                                <option value="XPF">XPF - CFP Franc</option>
                                <option value="INR">INR - Indian Rupee</option>
                                <option value="PKR">PKR - Pakistani Rupee</option>
                                <option value="BDT">BDT - Bangladeshi Taka</option>
                                <option value="LKR">LKR - Sri Lankan Rupee</option>
                                <option value="NPR">NPR - Nepalese Rupee</option>
                                <option value="BTN">BTN - Bhutanese Ngultrum</option>
                                <option value="MVR">MVR - Maldivian Rufiyaa</option>
                                <option value="AFN">AFN - Afghan Afghani</option>
                                <option value="IRR">IRR - Iranian Rial</option>
                                <option value="IQD">IQD - Iraqi Dinar</option>
                                <option value="SAR">SAR - Saudi Riyal</option>
                                <option value="AED">AED - UAE Dirham</option>
                                <option value="QAR">QAR - Qatari Riyal</option>
                                <option value="KWD">KWD - Kuwaiti Dinar</option>
                                <option value="BHD">BHD - Bahraini Dinar</option>
                                <option value="OMR">OMR - Omani Rial</option>
                                <option value="YER">YER - Yemeni Rial</option>
                                <option value="JOD">JOD - Jordanian Dinar</option>
                                <option value="LBP">LBP - Lebanese Pound</option>
                                <option value="SYP">SYP - Syrian Pound</option>
                                <option value="ILS">ILS - Israeli Shekel</option>
                                <option value="PEN">PEN - Peruvian Sol</option>
                                <option value="BRL">BRL - Brazilian Real</option>
                                <option value="ARS">ARS - Argentine Peso</option>
                                <option value="CLP">CLP - Chilean Peso</option>
                                <option value="COP">COP - Colombian Peso</option>
                                <option value="MXN">MXN - Mexican Peso</option>
                                <option value="UYU">UYU - Uruguayan Peso</option>
                                <option value="PYG">PYG - Paraguayan Guaraní</option>
                                <option value="BOB">BOB - Bolivian Boliviano</option>
                                <option value="VES">VES - Venezuelan Bolívar</option>
                                <option value="GTQ">GTQ - Guatemalan Quetzal</option>
                                <option value="HNL">HNL - Honduran Lempira</option>
                                <option value="NIO">NIO - Nicaraguan Córdoba</option>
                                <option value="CRC">CRC - Costa Rican Colón</option>
                                <option value="PAB">PAB - Panamanian Balboa</option>
                                <option value="DOP">DOP - Dominican Peso</option>
                                <option value="JMD">JMD - Jamaican Dollar</option>
                                <option value="TTD">TTD - Trinidad and Tobago Dollar</option>
                                <option value="BBD">BBD - Barbadian Dollar</option>
                                <option value="XCD">XCD - East Caribbean Dollar</option>
                                <option value="GYD">GYD - Guyanese Dollar</option>
                                <option value="SRD">SRD - Surinamese Dollar</option>
                                <option value="BZD">BZD - Belize Dollar</option>
                                <option value="HTG">HTG - Haitian Gourde</option>
                                <option value="CUP">CUP - Cuban Peso</option>
                                <option value="BMD">BMD - Bermudian Dollar</option>
                                <option value="KYD">KYD - Cayman Islands Dollar</option>
                                <option value="ANG">ANG - Netherlands Antillean Guilder</option>
                                <option value="AWG">AWG - Aruban Florin</option>
                                <option value="BSD">BSD - Bahamian Dollar</option>
                                <option value="FJD">FJD - Fijian Dollar</option>
                                <option value="NZD">NZD - New Zealand Dollar</option>
                                <option value="SBD">SBD - Solomon Islands Dollar</option>
                                <option value="VUV">VUV - Vanuatu Vatu</option>
                                <option value="WST">WST - Samoan Tālā</option>
                                <option value="TOP">TOP - Tongan Paʻanga</option>
                                <option value="PGK">PGK - Papua New Guinean Kina</option>
                                <option value="KID">KID - Kiribati Dollar</option>
                                <option value="TVD">TVD - Tuvaluan Dollar</option>
                                <option value="NOK">NOK - Norwegian Krone</option>
                                <option value="SEK">SEK - Swedish Krona</option>
                                <option value="DKK">DKK - Danish Krone</option>
                                <option value="ISK">ISK - Icelandic Króna</option>
                                <option value="PLN">PLN - Polish Złoty</option>
                                <option value="CZK">CZK - Czech Koruna</option>
                                <option value="HUF">HUF - Hungarian Forint</option>
                                <option value="RON">RON - Romanian Leu</option>
                                <option value="BGN">BGN - Bulgarian Lev</option>
                                <option value="HRK">HRK - Croatian Kuna</option>
                                <option value="RSD">RSD - Serbian Dinar</option>
                                <option value="ALL">ALL - Albanian Lek</option>
                                <option value="MKD">MKD - Macedonian Denar</option>
                                <option value="MDL">MDL - Moldovan Leu</option>
                                <option value="UAH">UAH - Ukrainian Hryvnia</option>
                                <option value="BYN">BYN - Belarusian Ruble</option>
                                <option value="RUB">RUB - Russian Ruble</option>
                                <option value="KZT">KZT - Kazakhstani Tenge</option>
                                <option value="UZS">UZS - Uzbekistani Som</option>
                                <option value="KGS">KGS - Kyrgyzstani Som</option>
                                <option value="TJS">TJS - Tajikistani Somoni</option>
                                <option value="TMT">TMT - Turkmenistani Manat</option>
                                <option value="AZN">AZN - Azerbaijani Manat</option>
                                <option value="GEL">GEL - Georgian Lari</option>
                                <option value="AMD">AMD - Armenian Dram</option>
                                <option value="TRY">TRY - Turkish Lira</option>
                                <option value="KRW">KRW - South Korean Won</option>
                                <option value="TWD">TWD - New Taiwan Dollar</option>
                                <option value="HKD">HKD - Hong Kong Dollar</option>
                                <option value="SGD">SGD - Singapore Dollar</option>
                                <option value="MYR">MYR - Malaysian Ringgit</option>
                                <option value="THB">THB - Thai Baht</option>
                                <option value="PHP">PHP - Philippine Peso</option>
                                <option value="IDR">IDR - Indonesian Rupiah</option>
                                <option value="VND">VND - Vietnamese Dong</option>
                                <option value="MMK">MMK - Myanmar Kyat</option>
                                <option value="LAK">LAK - Lao Kip</option>
                                <option value="KHR">KHR - Cambodian Riel</option>
                                <option value="MNT">MNT - Mongolian Tögrög</option>
                                <option value="BND">BND - Brunei Dollar</option>
                                <option value="KYD">KYD - Cayman Islands Dollar</option>
                                <option value="BMD">BMD - Bermudian Dollar</option>
                                <option value="ANG">ANG - Netherlands Antillean Guilder</option>
                                <option value="AWG">AWG - Aruban Florin</option>
                                <option value="BSD">BSD - Bahamian Dollar</option>
                                <option value="FJD">FJD - Fijian Dollar</option>
                                <option value="NZD">NZD - New Zealand Dollar</option>
                                <option value="SBD">SBD - Solomon Islands Dollar</option>
                                <option value="VUV">VUV - Vanuatu Vatu</option>
                                <option value="WST">WST - Samoan Tālā</option>
                                <option value="TOP">TOP - Tongan Paʻanga</option>
                                <option value="PGK">PGK - Papua New Guinean Kina</option>
                                <option value="KID">KID - Kiribati Dollar</option>
                                <option value="TVD">TVD - Tuvaluan Dollar</option>
                            </select>
                        </div>
                        <div class="kps-form-field">
                            <label for="amount" class="kps-form-label">Amount <span style="color: #dc2626;">*</span></label>
                            <div class="kps-currency-input">
                                <span class="kps-currency-symbol currency-symbol"><?php echo $has_cart ? ($cart_currency === 'KES' ? 'KSh' : ($cart_currency === 'USD' ? '$' : ($cart_currency === 'EUR' ? '€' : ($cart_currency === 'GBP' ? '£' : $cart_currency)))) : '$'; ?></span>
                                <input type="text" 
                                       name="amount" 
                                       id="amount" 
                                       required
                                       inputmode="decimal"
                                       pattern="[0-9]*[.]?[0-9]*"
                                       class="kps-form-input" 
                                       placeholder="0.00"
                                       autocomplete="off"
                                       value="<?php echo $has_cart ? esc_attr(number_format($cart_total, 2, '.', '')) : ''; ?>"
                                       <?php echo $has_cart ? 'readonly' : ''; ?>>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Customer Information -->
                <div class="kps-form-section">
                    <h3>Customer Information</h3>
                    
                    <div class="kps-form-grid" style="margin-bottom: 1.5rem;">
                        <div class="kps-form-field">
                            <label for="first_name" class="kps-form-label">First Name <span style="color: #dc2626;">*</span></label>
                            <input type="text" 
                                   name="first_name" 
                                   id="first_name" 
                                   required
                                   class="kps-form-input"
                                   data-shortcode-field="first_name">
                        </div>

                        <div class="kps-form-field">
                            <label for="last_name" class="kps-form-label">Last Name <span style="color: #dc2626;">*</span></label>
                            <input type="text" 
                                   name="last_name" 
                                   id="last_name" 
                                   required
                                   class="kps-form-input"
                                   data-shortcode-field="last_name">
                        </div>
                    </div>

                    <div class="kps-form-grid">
                        <div class="kps-form-field">
                            <label for="customer_email" class="kps-form-label">Email Address <span style="color: #dc2626;">*</span></label>
                            <input type="email" 
                                   name="customer_email" 
                                   id="customer_email" 
                                   required
                                   class="kps-form-input"
                                   data-shortcode-field="email">
                            <p class="kps-help-text">We'll send the receipt to this email</p>
                        </div>

                        <div class="kps-form-field">
                            <label for="phone" class="kps-form-label">Phone Number <span style="color: #dc2626;">*</span></label>
                            <input type="tel" 
                                   name="phone" 
                                   id="phone" 
                                   required
                                   placeholder="+254"
                                   class="kps-form-input"
                                   data-shortcode-field="phone">
                        </div>
                    </div>
                </div>

                <!-- Billing Address -->
                <div class="kps-form-section">
                    <h3>Billing Address</h3>

                    <div class="kps-form-field" style="margin-bottom: 1.5rem;">
                        <label for="address_line1" class="kps-form-label">Street Address <span style="color: #dc2626;">*</span></label>
                        <input type="text" 
                               name="address_line1" 
                               id="address_line1" 
                               required
                               class="kps-form-input"
                               data-shortcode-field="address_line1">
                    </div>

                    <div class="kps-form-grid" style="margin-bottom: 1.5rem;">
                        <div class="kps-form-field">
                            <label for="address_city" class="kps-form-label">City <span style="color: #dc2626;">*</span></label>
                            <input type="text" 
                                   name="address_city" 
                                   id="address_city" 
                                   required
                                   class="kps-form-input"
                                   data-shortcode-field="address_city">
                        </div>

                        <div class="kps-form-field">
                            <label for="address_state" class="kps-form-label">State/Province <span style="color: #dc2626;">*</span></label>
                            <input type="text" 
                                   name="address_state" 
                                   id="address_state" 
                                   required
                                   class="kps-form-input"
                                   data-shortcode-field="address_state">
                        </div>
                    </div>

                    <div class="kps-form-grid">
                        <div class="kps-form-field">
                            <label for="address_country" class="kps-form-label">Country <span style="color: #dc2626;">*</span></label>
                            <select name="address_country" 
                                    id="address_country" 
                                    required
                                    class="kps-form-select"
                                    data-shortcode-field="address_country">
                                <option value="">Select Country</option>
                                <option value="AF">Afghanistan</option>
                                <option value="AL">Albania</option>
                                <option value="DZ">Algeria</option>
                                <option value="AD">Andorra</option>
                                <option value="AO">Angola</option>
                                <option value="AG">Antigua and Barbuda</option>
                                <option value="AR">Argentina</option>
                                <option value="AM">Armenia</option>
                                <option value="AU">Australia</option>
                                <option value="AT">Austria</option>
                                <option value="AZ">Azerbaijan</option>
                                <option value="BS">Bahamas</option>
                                <option value="BH">Bahrain</option>
                                <option value="BD">Bangladesh</option>
                                <option value="BB">Barbados</option>
                                <option value="BY">Belarus</option>
                                <option value="BE">Belgium</option>
                                <option value="BZ">Belize</option>
                                <option value="BJ">Benin</option>
                                <option value="BT">Bhutan</option>
                                <option value="BO">Bolivia</option>
                                <option value="BA">Bosnia and Herzegovina</option>
                                <option value="BW">Botswana</option>
                                <option value="BR">Brazil</option>
                                <option value="BN">Brunei</option>
                                <option value="BG">Bulgaria</option>
                                <option value="BF">Burkina Faso</option>
                                <option value="BI">Burundi</option>
                                <option value="CV">Cabo Verde</option>
                                <option value="KH">Cambodia</option>
                                <option value="CM">Cameroon</option>
                                <option value="CA">Canada</option>
                                <option value="CF">Central African Republic</option>
                                <option value="TD">Chad</option>
                                <option value="CL">Chile</option>
                                <option value="CN">China</option>
                                <option value="CO">Colombia</option>
                                <option value="KM">Comoros</option>
                                <option value="CG">Congo</option>
                                <option value="CR">Costa Rica</option>
                                <option value="HR">Croatia</option>
                                <option value="CU">Cuba</option>
                                <option value="CY">Cyprus</option>
                                <option value="CZ">Czech Republic</option>
                                <option value="CD">Democratic Republic of the Congo</option>
                                <option value="DK">Denmark</option>
                                <option value="DJ">Djibouti</option>
                                <option value="DM">Dominica</option>
                                <option value="DO">Dominican Republic</option>
                                <option value="EC">Ecuador</option>
                                <option value="EG">Egypt</option>
                                <option value="SV">El Salvador</option>
                                <option value="GQ">Equatorial Guinea</option>
                                <option value="ER">Eritrea</option>
                                <option value="EE">Estonia</option>
                                <option value="ET">Ethiopia</option>
                                <option value="FJ">Fiji</option>
                                <option value="FI">Finland</option>
                                <option value="FR">France</option>
                                <option value="GA">Gabon</option>
                                <option value="GM">Gambia</option>
                                <option value="GE">Georgia</option>
                                <option value="DE">Germany</option>
                                <option value="GH">Ghana</option>
                                <option value="GR">Greece</option>
                                <option value="GD">Grenada</option>
                                <option value="GT">Guatemala</option>
                                <option value="GN">Guinea</option>
                                <option value="GW">Guinea-Bissau</option>
                                <option value="GY">Guyana</option>
                                <option value="HT">Haiti</option>
                                <option value="HN">Honduras</option>
                                <option value="HU">Hungary</option>
                                <option value="IS">Iceland</option>
                                <option value="IN">India</option>
                                <option value="ID">Indonesia</option>
                                <option value="IR">Iran</option>
                                <option value="IQ">Iraq</option>
                                <option value="IE">Ireland</option>
                                <option value="IL">Israel</option>
                                <option value="IT">Italy</option>
                                <option value="JM">Jamaica</option>
                                <option value="JP">Japan</option>
                                <option value="JO">Jordan</option>
                                <option value="KZ">Kazakhstan</option>
                                <option value="KE">Kenya</option>
                                <option value="KI">Kiribati</option>
                                <option value="KW">Kuwait</option>
                                <option value="KG">Kyrgyzstan</option>
                                <option value="LA">Laos</option>
                                <option value="LV">Latvia</option>
                                <option value="LB">Lebanon</option>
                                <option value="LS">Lesotho</option>
                                <option value="LR">Liberia</option>
                                <option value="LY">Libya</option>
                                <option value="LI">Liechtenstein</option>
                                <option value="LT">Lithuania</option>
                                <option value="LU">Luxembourg</option>
                                <option value="MG">Madagascar</option>
                                <option value="MW">Malawi</option>
                                <option value="MY">Malaysia</option>
                                <option value="MV">Maldives</option>
                                <option value="ML">Mali</option>
                                <option value="MT">Malta</option>
                                <option value="MH">Marshall Islands</option>
                                <option value="MR">Mauritania</option>
                                <option value="MU">Mauritius</option>
                                <option value="MX">Mexico</option>
                                <option value="FM">Micronesia</option>
                                <option value="MD">Moldova</option>
                                <option value="MC">Monaco</option>
                                <option value="MN">Mongolia</option>
                                <option value="ME">Montenegro</option>
                                <option value="MA">Morocco</option>
                                <option value="MZ">Mozambique</option>
                                <option value="MM">Myanmar</option>
                                <option value="NA">Namibia</option>
                                <option value="NR">Nauru</option>
                                <option value="NP">Nepal</option>
                                <option value="NL">Netherlands</option>
                                <option value="NZ">New Zealand</option>
                                <option value="NI">Nicaragua</option>
                                <option value="NE">Niger</option>
                                <option value="NG">Nigeria</option>
                                <option value="NO">Norway</option>
                                <option value="OM">Oman</option>
                                <option value="PK">Pakistan</option>
                                <option value="PW">Palau</option>
                                <option value="PA">Panama</option>
                                <option value="PG">Papua New Guinea</option>
                                <option value="PY">Paraguay</option>
                                <option value="PE">Peru</option>
                                <option value="PH">Philippines</option>
                                <option value="PL">Poland</option>
                                <option value="PT">Portugal</option>
                                <option value="QA">Qatar</option>
                                <option value="RO">Romania</option>
                                <option value="RU">Russia</option>
                                <option value="RW">Rwanda</option>
                                <option value="KN">Saint Kitts and Nevis</option>
                                <option value="LC">Saint Lucia</option>
                                <option value="VC">Saint Vincent and the Grenadines</option>
                                <option value="WS">Samoa</option>
                                <option value="SM">San Marino</option>
                                <option value="ST">Sao Tome and Principe</option>
                                <option value="SA">Saudi Arabia</option>
                                <option value="SN">Senegal</option>
                                <option value="RS">Serbia</option>
                                <option value="SC">Seychelles</option>
                                <option value="SL">Sierra Leone</option>
                                <option value="SG">Singapore</option>
                                <option value="SK">Slovakia</option>
                                <option value="SI">Slovenia</option>
                                <option value="SB">Solomon Islands</option>
                                <option value="SO">Somalia</option>
                                <option value="ZA">South Africa</option>
                                <option value="SS">South Sudan</option>
                                <option value="ES">Spain</option>
                                <option value="LK">Sri Lanka</option>
                                <option value="SD">Sudan</option>
                                <option value="SR">Suriname</option>
                                <option value="SZ">Eswatini</option>
                                <option value="SE">Sweden</option>
                                <option value="CH">Switzerland</option>
                                <option value="SY">Syria</option>
                                <option value="TW">Taiwan</option>
                                <option value="TJ">Tajikistan</option>
                                <option value="TZ">Tanzania</option>
                                <option value="TH">Thailand</option>
                                <option value="TL">Timor-Leste</option>
                                <option value="TG">Togo</option>
                                <option value="TO">Tonga</option>
                                <option value="TT">Trinidad and Tobago</option>
                                <option value="TN">Tunisia</option>
                                <option value="TR">Turkey</option>
                                <option value="TM">Turkmenistan</option>
                                <option value="TV">Tuvalu</option>
                                <option value="UG">Uganda</option>
                                <option value="UA">Ukraine</option>
                                <option value="AE">United Arab Emirates</option>
                                <option value="GB">United Kingdom</option>
                                <option value="US">United States</option>
                                <option value="UY">Uruguay</option>
                                <option value="UZ">Uzbekistan</option>
                                <option value="VU">Vanuatu</option>
                                <option value="VA">Vatican City</option>
                                <option value="VE">Venezuela</option>
                                <option value="VN">Vietnam</option>
                                <option value="YE">Yemen</option>
                                <option value="ZM">Zambia</option>
                                <option value="ZW">Zimbabwe</option>
                            </select>
                        </div>

                        <div class="kps-form-field">
                            <label for="address_postcode" class="kps-form-label">Postal Code <span style="color: #dc2626;">*</span></label>
                            <input type="text" 
                                   name="address_postcode" 
                                   id="address_postcode" 
                                   required
                                   class="kps-form-input"
                                   data-shortcode-field="address_postcode">
                        </div>
                    </div>
                </div>
            </form>
        </div>

        <!-- Right Column - Payment Summary & Actions -->
        <div class="kps-form-right">
            <!-- Payment Summary -->
            <div class="kps-payment-summary">
                <h3>Payment Summary</h3>
                
                <?php if ($has_cart && !empty($cart_items)): ?>
                    <?php foreach ($cart_items as $item): 
                        $product = $item['data'];
                        $name = $product->get_name();
                        $qty = $item['quantity'];
                        $price = wc_price($product->get_price());
                    ?>
                        <div class="kps-summary-item">
                            <span class="kps-summary-label"><?php echo esc_html($name); ?> × <?php echo intval($qty); ?></span>
                            <span class="kps-summary-value"><?php echo $price; ?></span>
                        </div>
                    <?php endforeach; ?>
                    
                    <div class="kps-summary-item">
                        <span class="kps-summary-label">Total</span>
                        <span class="kps-summary-value"><?php echo wc_price($cart_total); ?></span>
                    </div>
                <?php else: ?>
                    <div class="kps-summary-item">
                        <span class="kps-summary-label">Amount</span>
                        <span class="kps-summary-value" id="summary-amount">$0.00</span>
                    </div>
                    <div class="kps-summary-item">
                        <span class="kps-summary-label">Currency</span>
                        <span class="kps-summary-value" id="summary-currency">USD</span>
                    </div>
                    <div class="kps-summary-item">
                        <span class="kps-summary-label">Total</span>
                        <span class="kps-summary-value" id="summary-total">$0.00</span>
                    </div>
                <?php endif; ?>
            </div>

            <!-- Payment Actions -->
            <div class="kps-payment-actions">
                <button type="submit" form="kps-payment-form" class="kps-form-button">
                    <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                    </svg>
                    Pay Now
                </button>

                <div class="kps-security-info">
                    <h4>
                        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"/>
                        </svg>
                        Secure Payment
                    </h4>
                    <p>Your payment information is encrypted and secure</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Secure Payment Notice -->
    <div class="kps-secure-notice">
        <div class="kps-secure-badge">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
            </svg>
            <span>Secure payment powered by 
                <a href="https://www.ubakenya.com/" target="_blank">
                    United Bank for Africa
                </a>
            </span>
        </div>
    </div>
</div>

<script>
// Update currency symbol when currency changes
document.addEventListener('DOMContentLoaded', function() {
    const amountInput = document.getElementById('amount');
    const currencySelect = document.getElementById('currency');
    const currencySymbol = document.querySelector('.currency-symbol');

    function updateCurrencySymbol() {
        const currency = currencySelect.value;
        const symbol = currency === 'KES' ? 'KSh' : currency === 'USD' ? '$' : currency === 'EUR' ? '€' : '£';
        currencySymbol.textContent = symbol;
        
        // Update summary if no cart
        if (document.getElementById('summary-currency')) {
            document.getElementById('summary-currency').textContent = currency || 'USD';
        }
    }

    currencySelect.addEventListener('change', updateCurrencySymbol);
    
    // Update amount in summary
    if (amountInput && document.getElementById('summary-amount')) {
        amountInput.addEventListener('input', function() {
            const amount = this.value || '0.00';
            const currency = currencySelect.value || 'USD';
            const symbol = currency === 'KES' ? 'KSh' : currency === 'USD' ? '$' : currency === 'EUR' ? '€' : '£';
            
            document.getElementById('summary-amount').textContent = symbol + amount;
            document.getElementById('summary-total').textContent = symbol + amount;
        });
    }
    
    // Initial update
    updateCurrencySymbol();
});
</script> 