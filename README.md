# SOCKS5 UDP Checker

Fast and reliable UDP support testing for SOCKS5 proxies. Works with both IP-authenticated and username/password-authenticated proxies.

[![Python](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**Author:** nixnode

---

## Why This Tool

Most proxy testing tools only check TCP connectivity. This tool actually verifies the complete UDP ASSOCIATE flow and tests real UDP traffic transmission.

Built for infrastructure validation, VPN testing, and proxy network management.

## Features

- Zero dependencies (pure Python stdlib)
- IP authentication support
- Username/password authentication
- Real UDP traffic testing (DNS queries)
- Clean CLI interface
- Exit codes for scripting
- Cross-platform (Windows/Linux/macOS)

## Quick Start

```bash
# IP-authenticated proxy
python udp-check.py proxy.example.com 1080

# Username/password authentication
python udp-check.py proxy.example.com 1080 -u username -p password

# Quiet mode (scripting)
python udp-check.py proxy.example.com 1080 -q && echo "UDP supported"
```

## Installation

No installation needed. Just Python 3.6+.

```bash
# Download
curl -O https://raw.githubusercontent.com/nixnode/udp-checker/main/udp-check.py

# Make executable (Linux/macOS)
chmod +x udp-check.py

# Run
python udp-check.py <host> <port>
```

## Usage

### Basic Usage

```bash
python udp-check.py <host> <port> [options]
```

### Options

| Option | Description |
|--------|-------------|
| `-u, --username` | Username for authentication |
| `-p, --password` | Password for authentication |
| `-q, --quiet` | Quiet mode (no output, exit code only) |
| `-t, --timeout` | UDP test timeout in seconds (default: 5.0) |
| `-h, --help` | Show help message |
| `-v, --version` | Show version |

### Examples

**IP-authenticated proxy:**
```bash
python udp-check.py 203.0.113.50 1080
```

**Authenticated proxy:**
```bash
python udp-check.py proxy.example.com 1080 -u myuser -p mypass
```

**Batch testing:**
```bash
#!/bin/bash
for proxy in $(cat proxy-list.txt); do
    host=$(echo $proxy | cut -d: -f1)
    port=$(echo $proxy | cut -d: -f2)
    if python udp-check.py $host $port -q; then
        echo "$proxy: UDP supported"
    else
        echo "$proxy: UDP not supported"
    fi
done
```

**CI/CD integration:**
```bash
python udp-check.py $PROXY_HOST $PROXY_PORT -u $USER -p $PASS || exit 1
```

## Output

### Verbose Mode (Default)

```
Testing: vpn.example.com:1080
============================================================
[1/4] TCP connection established
[2/4] SOCKS5 handshake complete (no auth required)
[3/4] UDP relay established: 203.0.113.5:54321
[4/4] UDP traffic test: SUCCESS
============================================================
✓ UDP FULLY SUPPORTED
```

### Quiet Mode (`-q`)

No output. Use exit code:
- `0` = UDP supported
- `1` = UDP not supported or error

## How It Works

1. **TCP Connect** - Establishes connection to SOCKS5 server
2. **Authentication** - Negotiates auth (none or username/password)
3. **UDP ASSOCIATE** - Requests UDP relay capability
4. **UDP Test** - Sends DNS query through relay
5. **Validation** - Confirms UDP response received

## Common Use Cases

### Infrastructure Validation

Test proxy fleet UDP capabilities:

```bash
psql -t -c "SELECT proxy_ip, proxy_port FROM upstream_pool" | \
while read ip port; do
    python udp-check.py $ip $port -q && \
    psql -c "UPDATE upstream_pool SET supports_udp=true WHERE proxy_ip='$ip'"
done
```

### Monitoring

Add to cron for periodic checks:

```bash
#!/bin/bash
if ! python udp-check.py $PROXY_HOST $PROXY_PORT -q; then
    curl -X POST $WEBHOOK_URL -d "UDP support is down"
fi
```

### VPN Server Setup

Verify UDP after server configuration:

```bash
python udp-check.py localhost 1080 && echo "Setup complete"
```

## Troubleshooting

### "No acceptable authentication methods"

**IP authentication:** Your source IP is not whitelisted. Test from an authorized server.

**Username/password:** Use `-u` and `-p` options.

### "UDP ASSOCIATE failed: Command not supported"

The proxy doesn't have UDP support enabled. For GoProxy:

```bash
./goproxy socks -t tcp -p :1080 --udp-port 1080 --udp-timeout 60
```

### "Connection timeout"

- Check firewall rules
- Verify proxy is running
- Confirm host:port are correct

### "UDP relay established but traffic not working"

- UDP ports blocked by firewall
- NAT/routing issues
- Enable UDP on firewall: `ufw allow 1080/udp`

## Testing from Whitelisted IP

If your proxies use IP authentication, test from a whitelisted server:

```bash
# Upload script to server
scp udp-check.py user@server:~/

# SSH and test
ssh user@server
python udp-check.py upstream-proxy.com 1080
```

## Exit Codes

- `0` - UDP fully supported
- `1` - UDP not supported, auth failed, or connection error

## Performance

- Test duration: 2-7 seconds
- Network overhead: ~200 bytes
- Memory: <5 MB
- No dependencies to install

## Protocol Details

Implements SOCKS5 RFC 1928 UDP ASSOCIATE:

```
Client → Server: UDP ASSOCIATE request (TCP)
Server → Client: UDP relay address (TCP)
Client → Relay:  DNS query (UDP)
Relay → Client:  DNS response (UDP)
```

The TCP connection must remain open during UDP session.

## Integration Examples

### Python

```python
import subprocess
result = subprocess.run(['python', 'udp-check.py', 'proxy.com', '1080'])
if result.returncode == 0:
    print("UDP supported")
```

### Bash

```bash
if python udp-check.py proxy.com 1080 -q; then
    export UDP_ENABLED=1
fi
```

### GitHub Actions

```yaml
- name: Verify UDP Support
  run: python udp-check.py ${{ secrets.PROXY_HOST }} 1080
```

## Security

- No logging of credentials
- No external connections (except test target: 8.8.8.8)
- No telemetry
- Open source (audit the code)

## Requirements

- Python 3.6 or newer
- Network access to proxy

That's it. No pip, no virtualenv, no complexity.

## Contributing

Issues and PRs welcome at github.com/nixnode/udp-checker

## License

MIT License - see LICENSE file

---

**Made by nixnode** | [GitHub](https://github.com/nixnode) | 2026
