import os

import requests
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from flask import Flask, request
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from certificate_authority.csrgenerator import create_csr
from certificate_authority.validator import verify_certificate
from utils.auth import verify_auth_header, extract_user_id
from utils.signing import *

app = Flask(__name__)

my_id = '1020156016'

if not os.path.exists("assets"):
    os.mkdir("assets")

key, csr = create_csr("localhost:7000")

cert = requests.post('http://127.0.0.1:5000/sign', data=csr.public_bytes(serialization.Encoding.PEM),
                     verify=False, headers={'Content-type': 'application/octet-stream'})

with open('assets/certificate.pem', "w") as f:
    f.write(cert.text)

# each account has a 'value', 'password' and an array of policies.
account = dict({})
account['135702468'] = dict({'value': 100000, 'password': '1234', 'policies': []})
account['0987654321'] = dict({'value': 20000, 'password': '4321', 'policies': []})
# policies is a tuple of (bank_id, policy)


@app.route('/exchange', methods=['POST'])
def exchange():
    try:
        data = request.json
        certificate = x509.load_pem_x509_certificate(data['certificate'])
        header = data['header']
        try:
            verify_auth_header(header, certificate.public_key(), my_id)
        except InvalidSignature:
            return 'Signature Not Match', 450
        if not verify_certificate(certificate):
            return "Invalid Certificate", 451
        # todo: check value and bank id by policy.
    except ValueError:
        return "Bad create account data", 400


@app.route("/delegate")
def delegate():
    data = request.json
    try:
        verify_certificate(data["certificate"])
        pub_key = data["public_key"]
        bank_id = data["bank_id"]
        user_id = data["user_id"]
        policy = data["policy"]
        sign = data["signature"]
        pub_key = load_pem_public_key(bytes(pub_key, "utf-8"))
        verify_signature(pub_key, sign, bank_id + "|" + policy)
        account[user_id]["policies"].append((bank_id, policy))
        return "Created.", 201
    except ValueError:
        return "Bad create account data", 400