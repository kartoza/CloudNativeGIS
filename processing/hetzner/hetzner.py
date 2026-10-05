#!/usr/bin/env python3
"""Hetzner Cloud servers running CloudNativeGIS Processing, from a snapshot.

`HetznerClient.spin_up()` starts a server from the snapshot built by
cng-lite.pkr.hcl, gives it its own freshly generated LITE_API_TOKEN (through
cloud-init, see cng-lite.service) and waits until the API answers with that
token:

    1. find the snapshot      GET  /v1/images?type=snapshot&label_selector=...
    2. create the server      POST /v1/servers (token injected via cloud-init)
    3. wait until running     GET  /v1/actions/{id}
    4. wait for cng-lite      GET  http://<ip>:8000/health, then check token

`HetznerClient.delete()` deletes such a server again - it is billed per
started hour until it is deleted. Standard library only.

    client = HetznerClient(hcloud_token="...", version="0.0.3",
                           location="hel1")
    server = client.spin_up("cng-lite-test")    # {"url", "token", "id", ...}
    client.delete("cng-lite-test")

Command line (`make spin-up` / `make delete`), settings
from environment variables, filled in by the Makefile from .env:

    hetzner.py spin-up [SERVER_NAME]
    hetzner.py delete SERVER_NAME

    HCLOUD_TOKEN     required
    VERSION          snapshot version label (default: newest cng-lite snapshot)
    SERVER_TYPE      default: cx23
    LOCATION         default: fsn1
    SSH_KEYS         comma-separated Hetzner SSH key names/IDs, for debugging
    FIREWALL_ID      Hetzner firewall to attach (restrict port 8000 to caller)
    BOOT_TIMEOUT     seconds to wait for the API (default: 300)
    KEEP_ON_FAILURE  1 to keep the server if spin-up fails (default: delete it)

A started server's URL and token are saved to .servers/<name>.env (mode 600).
"""

import argparse
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path


class HetznerError(Exception):
    """A Hetzner Cloud API call or a spin-up step failed."""


class HetznerClient:
    """Starts and deletes cng-lite servers from a Hetzner Cloud snapshot."""

    API = "https://api.hetzner.cloud/v1"
    SERVERS_DIR = Path(__file__).resolve().parent / ".servers"
    # Only servers carrying these labels are ever deleted.
    LABELS = {"role": "cng-lite", "managed-by": "spin-up-from-snapshot"}
    USER_DATA = """\
#cloud-config
write_files:
  - path: /etc/cng-lite/env
    owner: root:root
    permissions: "0600"
    content: |
      LITE_API_TOKEN={token}
runcmd:
  - systemctl start cng-lite
"""

    def __init__(
        self,
        hcloud_token,
        version="",
        server_type="cx23",
        location="fsn1",
        ssh_keys=(),
        firewall_id=None,
        boot_timeout=300,
        keep_on_failure=False,
    ):
        """Configure the client; only `hcloud_token` is required."""
        if not hcloud_token:
            raise HetznerError(
                "A Hetzner Cloud API token (Read & Write) is required."
            )
        self.hcloud_token = hcloud_token
        self.version = version
        self.server_type = server_type
        self.location = location
        self.ssh_keys = list(ssh_keys)
        self.firewall_id = firewall_id
        self.boot_timeout = boot_timeout
        self.keep_on_failure = keep_on_failure

    # -- Public --------------------------------------------------------------

    def spin_up(self, server_name=""):
        """Start a server from the snapshot and wait for cng-lite.

        Returns the server's details (id, name, ip, url, token, created,
        env_file). Raises HetznerError on failure; a server that was created
        but never became ready is deleted (unless `keep_on_failure`).
        """
        now = datetime.now(timezone.utc)
        server_name = server_name or f"cng-lite-{now:%Y%m%d-%H%M%S}"
        token = secrets.token_hex(32)

        snapshot_id = self._find_snapshot()
        created = self._create_server(server_name, snapshot_id, token)
        server = created["server"]
        ip = server["public_net"]["ipv4"]["ip"]
        base_url = f"http://{ip}:8000"

        try:
            self.log(
                f"Server {server['id']} created at {server['created']}, "
                f"IP {ip} - waiting for it to start"
            )
            self._wait_for_action(created["action"]["id"])
            self._wait_for_cng_lite(base_url, token)
        except (HetznerError, KeyboardInterrupt) as exc:
            if self.keep_on_failure:
                self.log(
                    f"Keeping server {server_name} ({server['id']}, {ip}) "
                    "- it is still being billed."
                )
            else:
                try:
                    self._delete_server(server)
                except HetznerError:
                    self.log(
                        f"Could not delete server {server['id']} - "
                        "delete it in the Hetzner Console!"
                    )
            if isinstance(exc, KeyboardInterrupt):
                raise HetznerError("Interrupted.") from exc
            raise

        result = {
            "id": server["id"],
            "name": server["name"],
            "ip": ip,
            "url": base_url,
            "token": token,
            "created": server["created"],
        }
        result["env_file"] = self._save_server(result)
        self._print_summary(result)
        return result

    def delete(self, server_name):
        """Delete a server started by spin_up(), by name.

        Refuses servers without this client's labels, so it can't delete
        anything else in the project.
        """
        if not server_name:
            raise HetznerError("A server name is required.")
        query = urllib.parse.urlencode({"name": server_name})
        servers = self.api("GET", f"/servers?{query}")["servers"]
        if not servers:
            raise HetznerError(f"No server named {server_name}.")
        server = servers[0]
        labels = server["labels"]
        if any(labels.get(key) != value for key, value in self.LABELS.items()):
            raise HetznerError(
                f"Server {server_name} wasn't started by spin_up() "
                f"(labels {server['labels']}); not deleting it."
            )
        self._delete_server(server)

    # -- Steps ---------------------------------------------------------------

    def _find_snapshot(self):
        selector = "app=cng-lite"
        if self.version:
            selector += f",version={self.version}"
        self.log(f"Looking up newest snapshot with labels: {selector}")
        query = urllib.parse.urlencode(
            {
                "type": "snapshot",
                "sort": "created:desc",
                "label_selector": selector,
            }
        )
        images = self.api("GET", f"/images?{query}")["images"]
        if not images:
            raise HetznerError(
                f"No snapshot found with labels {selector}. "
                "Run 'make generate-snapshot' first."
            )
        image = images[0]
        self.log(f"Using snapshot {image['id']} ({image['description']})")
        return image["id"]

    def _create_server(self, server_name, snapshot_id, token):
        payload = {
            "name": server_name,
            "server_type": self.server_type,
            "image": snapshot_id,
            "location": self.location,
            "user_data": self.USER_DATA.format(token=token),
            "start_after_create": True,
            "labels": self.LABELS,
        }
        if self.ssh_keys:
            payload["ssh_keys"] = self.ssh_keys
        if self.firewall_id:
            payload["firewalls"] = [{"firewall": int(self.firewall_id)}]

        self.log(
            f"Creating server {server_name} "
            f"({self.server_type}, {self.location})"
        )
        return self.api("POST", "/servers", payload)

    def _wait_for_action(self, action_id):
        while True:
            action = self.api("GET", f"/actions/{action_id}")["action"]
            if action["status"] == "success":
                return
            if action["status"] == "error":
                error = action.get("error") or {}
                message = error.get("message", "unknown error")
                raise HetznerError(
                    f"Hetzner action {action['command']} failed: {message}"
                )
            time.sleep(2)

    def _wait_for_cng_lite(self, base_url, token):
        self.log(f"Waiting for {base_url}/health (up to {self.boot_timeout}s)")
        deadline = time.monotonic() + self.boot_timeout
        while self.http_status(f"{base_url}/health") != 200:
            if time.monotonic() >= deadline:
                raise HetznerError(
                    "cng-lite did not become healthy within "
                    f"{self.boot_timeout}s."
                )
            time.sleep(3)

        # /health needs no token; a job lookup does. With the right token an
        # unknown job is a 404, without one it must be a 401 (else auth is
        # off).
        check_url = f"{base_url}/api/v1/jobs/token-check"
        with_token = self.http_status(check_url, token)
        without_token = self.http_status(check_url)
        if with_token != 404 or without_token != 401:
            raise HetznerError(
                f"Token check failed (with token: HTTP {with_token}, "
                f"without: HTTP {without_token})."
            )
        self.log("cng-lite is up and only accepts its own token")

    def _delete_server(self, server):
        self.log(f"Deleting server {server['name']} ({server['id']})")
        response = self.api("DELETE", f"/servers/{server['id']}")
        self._wait_for_action(response["action"]["id"])
        (self.SERVERS_DIR / f"{server['name']}.env").unlink(missing_ok=True)
        self.log(f"Deleted server {server['name']}")

    def _save_server(self, result):
        self.SERVERS_DIR.mkdir(exist_ok=True)
        path = self.SERVERS_DIR / f"{result['name']}.env"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as env_file:
            env_file.write(
                f"HETZNER_SERVER_ID={result['id']}\n"
                f"HETZNER_SERVER_NAME={result['name']}\n"
                f"HETZNER_SERVER_CREATED={result['created']}\n"
                f"CLOUDNATIVEGIS_URL={result['url']}\n"
                f"CLOUDNATIVEGIS_API_TOKEN={result['token']}\n"
            )
        return path

    @staticmethod
    def _print_summary(result):
        # Billed per started hour from `created`; keep a few minutes of margin.
        created = datetime.fromisoformat(result["created"])
        delete_before = created + timedelta(minutes=55)
        print(
            f"""
Server ready
  name      {result['name']}
  id        {result['id']}
  url       {result['url']}
  token     {result['token']}
  created   {result['created']}
  saved to  {result['env_file']}

Billed per started hour until the server is DELETED (powering off doesn't
stop billing). Delete before {delete_before:%Y-%m-%d %H:%M:%S %Z} to stay
within the first hour:
  make delete SERVER_NAME={result['name']}"""
        )

    # -- HTTP helpers --------------------------------------------------------

    def api(self, method, path, body=None):
        """Call the Hetzner Cloud API; returns the decoded JSON body."""
        request = urllib.request.Request(
            f"{self.API}{path}",
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={
                "Authorization": f"Bearer {self.hcloud_token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read()
        except urllib.error.HTTPError as exc:
            try:
                message = json.loads(exc.read())["error"]["message"]
            except (ValueError, KeyError):
                message = exc.reason
            raise HetznerError(
                f"Hetzner API {method} {path} failed "
                f"(HTTP {exc.code}): {message}"
            ) from exc
        except urllib.error.URLError as exc:
            raise HetznerError(
                f"Could not reach the Hetzner API: {exc.reason}"
            ) from exc
        return json.loads(content) if content else {}

    @staticmethod
    def http_status(url, token=None):
        """HTTP status of a GET to cng-lite, or None if not reachable yet."""
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=5):
                return 200
        except urllib.error.HTTPError as exc:
            return exc.code
        except (urllib.error.URLError, OSError):
            return None

    @staticmethod
    def log(message):
        """Print a progress message to stderr."""
        print(f"==> {message}", file=sys.stderr, flush=True)


def main():
    """Command line entry point: spin-up or delete."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    commands = parser.add_subparsers(dest="command", required=True)
    spin_up = commands.add_parser(
        "spin-up", help="start a server from the snapshot"
    )
    spin_up.add_argument("server_name", nargs="?", default="")
    delete = commands.add_parser(
        "delete", help="delete a server started by spin-up"
    )
    delete.add_argument("server_name")
    args = parser.parse_args()

    env = os.environ
    try:
        client = HetznerClient(
            hcloud_token=env.get("HCLOUD_TOKEN", ""),
            version=env.get("VERSION", ""),
            server_type=env.get("SERVER_TYPE") or "cx23",
            location=env.get("LOCATION") or "fsn1",
            ssh_keys=[
                key.strip()
                for key in env.get("SSH_KEYS", "").split(",")
                if key.strip()
            ],
            firewall_id=env.get("FIREWALL_ID") or None,
            boot_timeout=int(env.get("BOOT_TIMEOUT") or 300),
            keep_on_failure=env.get("KEEP_ON_FAILURE") == "1",
        )
        if args.command == "spin-up":
            client.spin_up(args.server_name)
        else:
            client.delete(args.server_name)
    except HetznerError as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
