import braintree
import os

BRAINTREE_CONF = braintree.Configuration(
    braintree.Environment.Sandbox,
    merchant_id=os.getenv("BRAINTREE_MERCHANT_ID"),
    public_key=os.getenv("BRAINTREE_PUBLIC_KEY"),
    private_key=os.getenv("BRAINTREE_PRIVATE_KEY")
)