# Braintree settings
BRAINTREE_MERCHANT_ID = 'merchant'  # Get from Braintree dashboard
BRAINTREE_PUBLIC_KEY = 'public'
BRAINTREE_PRIVATE_KEY = 'private'

import braintree

BRAINTREE_CONF = braintree.Configuration(
    braintree.Environment.Sandbox,
    merchant_id=BRAINTREE_MERCHANT_ID,
    public_key=BRAINTREE_PUBLIC_KEY,
    private_key=BRAINTREE_PRIVATE_KEY
)