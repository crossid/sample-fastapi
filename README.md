# sample-fastapi

First, install dependencies

```bash
python3  -m venv env
source ./env/bin/activate
pip3 install -r requirements.txt
```

Then run server with:

```bash
CLIENT_ID=<client_id>\
CLIENT_SECRET=<client_secret> \
REDIRECT_URI=https://localhost/callback \
ISSUER_BASE_URL=https://<tenant_id>.<region>.crossid.io/oauth2/ \
uvicorn app:app --port 5000
```

Optionally, if you encounter "httpx.ConnectError: [SSL: CERTIFICATE_VERIFY_FAILED", you would need to export

```bash
REQUESTS_CA_BUNDLE=<path/to/ca-certificates.crt>
SSL_CERT_FILE=<path/to/ca-certificates.crt>
```

## Deploying on Digital Ocean

Click this button to deploy the app to the DigitalOcean App Platform.

[![Deploy to DigitalOcean](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/crossid/sample-fastapi/tree/main)

Fill the needed enviroment variables: ISSUER_BASE_URL

or if you have `doctl` installed then run:

`doctl apps create --spec .do/app.yaml`

Then go to the DigitalOcean admin screen and update the enviroment variables: Fill the needed enviroment variables: ISSUER_BASE_URL

Take note of the public url of your new app.

You will need to get a token from CrossID UI, and be able to use it with the /protected route
