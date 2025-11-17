# Braintree settings
BRAINTREE_MERCHANT_ID = '7qvc63hzd9rss3bm'  # Get from Braintree dashboard
BRAINTREE_PUBLIC_KEY = 'ntk4wxwfjhr5cxxk'
BRAINTREE_PRIVATE_KEY = '013cde2ad3c5ba9c05d3495cf6c19cb0'

import braintree

BRAINTREE_CONF = braintree.Configuration(
    braintree.Environment.Sandbox,
    merchant_id=BRAINTREE_MERCHANT_ID,
    public_key=BRAINTREE_PUBLIC_KEY,
    private_key=BRAINTREE_PRIVATE_KEY
)