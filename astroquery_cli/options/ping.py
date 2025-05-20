import requests
import subprocess
import socket
from urllib.parse import urlparse

URLS = [
    "https://almascience.org",
    "https://gea.esac.esa.int",
    "https://ssd.jpl.nasa.gov",
    "https://vizier.cds.unistra.fr",
    "https://vizier.eso.org",
    "https://vizier.china-vo.org",
]

def get_ping(host):
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
                    return f"{ms} ms"
            return "No time found"
        else:
            return "Ping failed"
    except Exception as e:
        return f"Ping error: {e}"

def run_ping():
    print("Note: Many public web services disable ICMP (ping). 'Ping failed' does not mean the service is unavailable. HTTP status is the main indicator of availability.\n")
    for url in URLS:
        parsed = urlparse(url)
        host = parsed.hostname
        try:
            ip = socket.gethostbyname(host)
            dns_result = f"DNS: {ip}"
        except Exception as e:
            dns_result = f"DNS error: {e}"
        ping_result = get_ping(host)
        try:
            response = requests.get(url, timeout=5)
            msg = f"{url} - Status: {response.status_code} - {dns_result} - Ping: {ping_result}"
            if ping_result == "Ping failed":
                msg += " [ICMP likely disabled]"
            print(msg)
        except requests.exceptions.RequestException as e:
            msg = f"{url} - Error: {e} - {dns_result} - Ping: {ping_result}"
            if ping_result == "Ping failed":
                msg += " [ICMP likely disabled]"
            print(msg)

if __name__ == "__main__":
    run_ping()
