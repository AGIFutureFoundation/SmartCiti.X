#!/usr/bin/env python3
"""payments/ - what a learner or an organisation could buy, and nothing we cannot stand behind.

No Stripe account is connected to this deployment. So this catalogue names
PLANS (who a plan is for, in words) and the NAMES of the environment variables
an operator fills in once they have created the matching Products and Prices in
their own Stripe dashboard. It holds no price, no currency, no discount, no tax
rate, no trial and no billing interval: every one of those is "set by the
operator in Stripe", and a record that carries a value there stops this build.

Outputs (both generated, never hand-edited):
  payments/registry/catalog.json  - the catalogue, with a sha256 source_stamp
  payments/catalog.mjs            - the same object as an ES module, so the
                                    Worker can import it without a JSON loader
"""
import hashlib
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
OPERATOR = 'set by the operator in Stripe'

# AUTHORED: the audiences the platform already addresses (learners, union
# halls, K-12 schools and districts). Words only; no commercial terms.
PLANS = [
    {'id': 'individual-learner', 'audience': 'one learner',
     'price_env': 'STRIPE_PRICE_INDIVIDUAL_LEARNER', 'mode_env': 'STRIPE_MODE_INDIVIDUAL_LEARNER'},
    {'id': 'union-hall', 'audience': 'a union training hall and its apprentices',
     'price_env': 'STRIPE_PRICE_UNION_HALL', 'mode_env': 'STRIPE_MODE_UNION_HALL'},
    {'id': 'school-district', 'audience': 'a K-12 school or district (PROPOSED partner, no agreement)',
     'price_env': 'STRIPE_PRICE_SCHOOL_DISTRICT', 'mode_env': 'STRIPE_MODE_SCHOOL_DISTRICT'},
]
COMMERCIAL = ('price', 'currency', 'interval', 'trial', 'discount', 'tax')


class CatalogError(Exception):
    pass


def plan_record(p):
    for k in ('id', 'audience', 'price_env', 'mode_env'):
        if k not in p or not p[k]:
            raise CatalogError(f'payments: plan field {k!r} is missing')
    if not re.fullmatch(r'[a-z][a-z0-9-]{2,40}', p['id']):
        raise CatalogError(f'payments: plan id {p["id"]!r} is not a slug')
    for k in ('price_env', 'mode_env'):
        if not re.fullmatch(r'STRIPE_[A-Z_]+', p[k]):
            raise CatalogError(f'payments: {p["id"]}.{k} {p[k]!r} is not an env var name')
    rec = {'id': p['id'], 'audience': p['audience'],
           'price_id': None, 'price_env': p['price_env'], 'mode_env': p['mode_env'],
           'label_key': f'plans.plan.{p["id"]}.title', 'desc_key': f'plans.plan.{p["id"]}.desc'}
    for k in COMMERCIAL:
        rec[k] = None
    rec['commercial_terms'] = OPERATOR
    return rec


def build():
    recs = [plan_record(p) for p in PLANS]
    ids = [r['id'] for r in recs]
    if len(set(ids)) != len(ids):
        raise CatalogError('payments: duplicate plan id')
    for r in recs:
        for k in COMMERCIAL + ('price_id',):
            if r[k] is not None:
                raise CatalogError(f'payments: {r["id"]}.{k} carries a value - never invent commercial terms')
    src = (HERE / 'build.py').read_bytes()
    return {
        'pack': 'payments',
        'provenance': 'AUTHORED',
        'live': False,
        'status': 'Payments are not live: no Stripe account is connected to this deployment',
        'commercial_terms': OPERATOR,
        'card_data': 'never handled by this code: Stripe-hosted Checkout only',
        'checkout': {
            'endpoint': '/api/checkout',
            'success_path': '/web/trade_craft_plans.html?checkout=success',
            'cancel_path': '/web/trade_craft_plans.html?checkout=cancelled',
            'secret_env': 'STRIPE_SECRET_KEY',
            'origin_env': 'SITE_ORIGIN',
            'stripe_api': 'https://api.stripe.com/v1/checkout/sessions',
            'hosted_prefix': 'https://checkout.stripe.com/',
        },
        'rate_limit': {
            'applies_to': '/api/checkout',
            'kind': 'token bucket in KV per (hashed client IP, plan)',
            'max_env': 'RATE_LIMIT_CHECKOUT_MAX',
            'window_env': 'RATE_LIMIT_CHECKOUT_WINDOW_S',
            'salt_env': 'RATE_LIMIT_SALT',
            'ip_header': 'cf-connecting-ip',
            'kv_binding': 'PAYMENTS_KV',
            'limits': 'set by the operator in env; no limit is policy in this repo',
        },
        'webhook': {
            'endpoint': '/api/stripe-webhook',
            'secret_env': 'STRIPE_WEBHOOK_SECRET',
            'kv_binding': 'PAYMENTS_KV',
            'tolerance_s': 300,
            'handled': ['checkout.session.completed'],
            'stored_fields': ['plan', 'payment_status', 'mode', 'livemode', 'at'],
        },
        'plans': recs,
        'source_stamp': 'sha256:' + hashlib.sha256(src).hexdigest(),
    }


def main():
    cat = build()
    (HERE / 'registry').mkdir(exist_ok=True)
    text = json.dumps(cat, indent=1, ensure_ascii=False) + '\n'
    (HERE / 'registry' / 'catalog.json').write_text(text)
    (HERE / 'catalog.mjs').write_text(
        '// GENERATED by payments/build.py from the same object as registry/catalog.json. Do not edit.\n'
        'export default ' + json.dumps(cat, indent=1, ensure_ascii=False) + ';\n')
    print(f'payments: {len(cat["plans"])} plans, live={cat["live"]}, prices: none ({OPERATOR})')


if __name__ == '__main__':
    main()
