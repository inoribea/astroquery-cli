import requests
import subprocess
import socket
from urllib.parse import urlparse

from ..i18n import get_translator
import builtins

URLS = [
    "https://almascience.org",
    "https://gea.esac.esa.int",
    "https://www.nasa.gov",
    "https://cds.unistra.fr",
]

def get_ping(host):
    _ = builtins._
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "2", host],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "time=" in line:
                    time_part = line.split("time=")[-1]
                    ms = time_part.split()[0]
                    return _("{ms_value} ms").format(ms_value=ms)
            return _("No time found")
        else:
            return _("ICMP disabled or blocked")
    except Exception as e:
        return _("Ping error: {error_message}").format(error_message=e)

def run_ping():
    _ = builtins._
    print(_("Checking service availability...\n"))
    for url in URLS:
        parsed = urlparse(url)
        host = parsed.hostname
        
        dns_status = _("Unknown")
        try:
            ip = socket.gethostbyname(host)
            dns_status = _("Resolved to {ip_address}").format(ip_address=ip)
        except Exception as e:
            dns_status = _("DNS resolution failed: {error_message}").format(error_message=e)

        ping_status = get_ping(host)
        
        http_status = _("Unknown")
        availability_message = _("Service Unavailable")
        try:
            response = requests.get(url, timeout=5)
            http_status = _("HTTP Status: {status_code}").format(status_code=response.status_code)
            if response.status_code == 200:
                availability_message = _("Service Available")
            else:
                availability_message = _("Service Responded with Error ({status_code})").format(status_code=response.status_code)
        except requests.exceptions.RequestException as e:
            http_status = _("HTTP Request Failed: {error_message}").format(error_message=e)
            availability_message = _("Service Unavailable (Connection Error)")
        
        print(_("--- {url_address} ---").format(url_address=url))
        print(_("  Availability: {availability_message}").format(availability_message=availability_message))
        print(_("  DNS Status: {dns_status}").format(dns_status=dns_status))
        print(_("  Ping Status: {ping_status}").format(ping_status=ping_status))
        print(_("  HTTP Status: {http_status}\n").format(http_status=http_status))

if __name__ == "__main__":
    run_ping()
