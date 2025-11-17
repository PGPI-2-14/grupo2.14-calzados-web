# Braintree settings
BRAINTREE_MERCHANT_ID = 'your_merchant_id'  # Get from Braintree dashboard
BRAINTREE_PUBLIC_KEY = 'your_public_key'
BRAINTREE_PRIVATE_KEY = 'your_private_key'

import braintree

BRAINTREE_CONF = braintree.Configuration(
    braintree.Environment.Sandbox,
    merchant_id=BRAINTREE_MERCHANT_ID,
    public_key=BRAINTREE_PUBLIC_KEY,
    private_key=BRAINTREE_PRIVATE_KEY
)