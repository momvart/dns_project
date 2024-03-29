from datetime import datetime, timedelta

from requests.exceptions import HTTPError
from utils.signing import sign
from blockchain.models import Policy
from utils import headers
from utils.urls import BANK_URL, BC_URL, SELLER_URL
from utils.ids import BANK_ID, SELLER_ID
import utils.auth
from utils.auth import create_auth_header
from utils.encoding import from_base64, to_base64
import requests
from client.certificate_manager import load_certificate, load_private_key, load_public_key, obtain_certificate
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

obtain_certificate()

cert = load_certificate()
private_key = load_private_key()
# public_key = load_public_key()
utils.auth.default_private_key = private_key

logger.info("Certificate and public key generation is done!")

USER_ID_1 = "135702468"
USER_ID_2 = "0987654321"


def create_bank_account():
    data = {
        'certificate': to_base64(cert)
    }
    response = requests.post(
        f'{BANK_URL}/create',
        json=data,
        headers={headers.AUTHORIZATION: create_auth_header(USER_ID_1, BANK_ID)},
        verify=False
    )
    response.raise_for_status()

    logger.info('Bank account created successfully.')


def buy_item():
    data = {
        'certificate': to_base64(cert),
        # 'public_key': to_base64(public_key),
    }

    response = requests.post(
        f'{SELLER_URL}/{USER_ID_1}/buy/2',
        json=data,
        verify=False,
        headers={headers.AUTHORIZATION: create_auth_header(USER_ID_1, SELLER_ID)})
    response.raise_for_status()

    data = response.json()
    payment_id, amount = data['payment_id'], data['amount']
    logger.info(f'Item buy request submitted successfully. ' +
                f'Payment Id = {payment_id}, Amount = {amount}')
    return payment_id, amount


def pay_item(payment_id, user_id=USER_ID_1):
    response = requests.post(
        f'{BANK_URL}/payment/{payment_id}/pay',
        headers={headers.AUTHORIZATION: create_auth_header(user_id, BANK_ID)},
        verify=False
    )
    try:
        response.raise_for_status()
        logger.info('Item payment has been successfully done.')
        return True, None
    except HTTPError:
        if response.status_code == 460:
            logger.info('There was not a valid delegation for this payment.')
            return False, from_base64(str(response.content, 'ascii'))
        elif response.status_code == 450:
            logger.info('It seems something is wrong in header.')
            return False, from_base64(str(response.content, 'ascii'))
        return False, None


def delegate(amount):
    policy = Policy(
        int(datetime.utcnow().timestamp()),
        int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
        2,
        amount).to_bytes()
    data = {
        'certificate': to_base64(cert),
        # 'public_key': to_base64(public_key),
        'user_id': USER_ID_1,
        'bank_id': BANK_ID,
        'policy': to_base64(policy),
        'signature': to_base64(sign(private_key, bytes(BANK_ID, encoding='ascii') + policy))
    }

    response = requests.post(
        f'{BC_URL}/delegate',
        json=data,
        verify=False)
    response.raise_for_status()

    logger.info('Delegation successfully done.')


create_bank_account()
payment_id, amount = buy_item()
successful, bank_public_key = pay_item(payment_id)
if not successful:
    delegate(amount)
    pay_item(payment_id)
