from flask import Flask, request
from markupsafe import escape
from flask import render_template
from pathlib import Path
import configparser

import requests
from requests.compat import urljoin, quote_plus
import hmac, hashlib

CONFIG_PATH = Path("config.cfg")

app = Flask(__name__)

config = configparser.ConfigParser()
if CONFIG_PATH.exists():
    config.read(CONFIG_PATH)
else:
    config = {}


@app.route("/", methods=["GET", "POST"])
def index(name=None):
    if request.method == "POST":
        auth_header = {"Authorization": "Bearer " + config["Backend"]["SynapseToken"]}
        base_validity_url = urljoin(
            config["Backend"]["SynapseURL"],
            "/_matrix/client/v1/register/m.login.registration_token/validity",
        )
        token_url = urljoin(base_validity_url, "?token=" + request.form["token"])

        res = requests.get(token_url, headers=auth_header)
        res_json = res.json()

        # Check if token is valid
        if res.status_code == 200 and res_json["valid"] is not True:
            return "The token you provided is not valid."
        elif res.status_code != 200:
            return "An unknown error has occured." + str(res.json())

        # Check if username is available
        username = (
            "@" + request.form["username"] + ":" + config["Backend"]["MatrixHost"]
        )
        base_user_url = urljoin(
            config["Backend"]["SynapseURL"],
            "/_matrix/client/r0/register/available"
            + "?username="
            + request.form["username"],
        )

        res = requests.get(base_user_url)

        if res.status_code != 200:
            return "Username taken or invalid" + base_user_url + str(res.json())

        # Do the registration
        # Get the session ID
        registration_base_url = urljoin(
            config["Backend"]["SynapseURL"], "/_matrix/client/r0/register"
        )

        res = requests.post(registration_base_url, json={})

        if res.status_code != 401:
            return (
                "An unknown error has occured during registration"
                + str(registration_base_url)
                + str(res.json())
            )

        session_id = res.json()["session"]

        json_payload = {
            "auth": {
                "type": "m.login.registration_token",
                "token": request.form["token"],
                "session": session_id,
            },
            "inhibit_login": True,
            "username": request.form["username"],
            "password": request.form["password"],
        }

        token_registration_url = urljoin(
            registration_base_url,
            "/_matrix/client/r0/register",
        )
        res = requests.post(token_registration_url, json=json_payload)

        if res.status_code != 401:
            return (
                "An unknown error happened during registration, "
                + token_registration_url
                + str(res.status_code)
                + str(res.json())
            )

        dummy_auth_url = urljoin(
            registration_base_url, "/_matrix/client/r0/auth/m.login.dummy/"
        )
        json_payload = {
            "auth": {
                "type": "m.login.dummy",
                "session": session_id,
            },
        }

        res = requests.post(token_registration_url, json=json_payload)

        if res.status_code == 200:
            return "Registration successful"
        else:
            return "An unknown error happened during registration, " + str(res.json())

    else:
        return render_template("index.html.j2", config=config["Frontend"])
