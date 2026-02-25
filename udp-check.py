#!/usr/bin/env python3
"""
SOCKS5 UDP Support Checker
Tests if a SOCKS5 proxy supports UDP ASSOCIATE command and UDP relay functionality.

Author: nixnode
License: MIT
"""

import socket
import struct
import sys
import argparse
from typing import Optional, Tuple

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

VERSION = "1.0.0"

class SOCKS5:
    VERSION = 0x05
    AUTH_NONE = 0x00
    AUTH_USERPASS = 0x02
    CMD_UDP_ASSOCIATE = 0x03
    ATYP_IPV4 = 0x01
    ATYP_DOMAIN = 0x03
    REP_SUCCESS = 0x00

    ERROR_MESSAGES = {
        0x01: "General server failure",
        0x02: "Connection not allowed by ruleset",
        0x03: "Network unreachable",
        0x04: "Host unreachable",
        0x05: "Connection refused",
        0x06: "TTL expired",
        0x07: "Command not supported",
        0x08: "Address type not supported",
        0x09: "UDP not supported",
    }


def connect_socks5(sock: socket.socket, username: Optional[str], password: Optional[str]) -> None:
    if username and password:
        greeting = struct.pack('BBBB', SOCKS5.VERSION, 2, SOCKS5.AUTH_NONE, SOCKS5.AUTH_USERPASS)
    else:
        greeting = struct.pack('BBB', SOCKS5.VERSION, 1, SOCKS5.AUTH_NONE)

    sock.sendall(greeting)
    response = sock.recv(2)

    if len(response) != 2:
        raise ConnectionError("Invalid handshake response")

    version, method = struct.unpack('BB', response)

    if version != SOCKS5.VERSION:
        raise ConnectionError(f"Unsupported SOCKS version: {version}")

    if method == 0xFF:
        raise ConnectionError("No acceptable authentication methods")

    if method == SOCKS5.AUTH_USERPASS:
        if not username or not password:
            raise ConnectionError("Server requires authentication")

        user_bytes = username.encode('utf-8')
        pass_bytes = password.encode('utf-8')
        auth_req = struct.pack('BB', 0x01, len(user_bytes)) + user_bytes + \
                   struct.pack('B', len(pass_bytes)) + pass_bytes
        sock.sendall(auth_req)

        auth_resp = sock.recv(2)
        if len(auth_resp) != 2 or auth_resp[1] != 0x00:
            raise ConnectionError("Authentication failed")


def request_udp_associate(sock: socket.socket) -> Tuple[str, int]:
    request = struct.pack('!BBB', SOCKS5.VERSION, SOCKS5.CMD_UDP_ASSOCIATE, 0x00)
    request += struct.pack('!B', SOCKS5.ATYP_IPV4)
    request += socket.inet_aton('0.0.0.0')
    request += struct.pack('!H', 0)

    sock.sendall(request)

    header = sock.recv(4)
    if len(header) != 4:
        raise ConnectionError("Invalid UDP ASSOCIATE response")

    version, reply, _, atyp = struct.unpack('BBBB', header)

    if version != SOCKS5.VERSION:
        raise ConnectionError(f"Invalid SOCKS version: {version}")

    if reply != SOCKS5.REP_SUCCESS:
        error = SOCKS5.ERROR_MESSAGES.get(reply, f"Unknown error (code {reply})")
        raise ConnectionError(f"UDP ASSOCIATE failed: {error}")

    if atyp == SOCKS5.ATYP_IPV4:
        addr = sock.recv(4)
        relay_host = socket.inet_ntoa(addr)
    elif atyp == SOCKS5.ATYP_DOMAIN:
        length = struct.unpack('B', sock.recv(1))[0]
        relay_host = sock.recv(length).decode('utf-8')
    else:
        raise ConnectionError(f"Unsupported address type: {atyp}")

    relay_port = struct.unpack('!H', sock.recv(2))[0]
    return relay_host, relay_port


def create_dns_query(domain: str = "google.com") -> bytes:
    header = struct.pack('!HHHHHH', 0x1234, 0x0100, 1, 0, 0, 0)

    question = b''
    for part in domain.split('.'):
        question += struct.pack('B', len(part)) + part.encode('utf-8')
    question += b'\x00'
    question += struct.pack('!HH', 1, 1)

    return header + question


def test_udp_relay(relay_host: str, relay_port: int, timeout: float = 5.0) -> bool:
    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.settimeout(timeout)

    try:
        header = struct.pack('!HBB', 0x0000, 0x00, SOCKS5.ATYP_DOMAIN)
        target = "8.8.8.8"
        target_bytes = target.encode('utf-8')
        header += struct.pack('B', len(target_bytes)) + target_bytes
        header += struct.pack('!H', 53)

        dns_query = create_dns_query("google.com")
        packet = header + dns_query

        udp_sock.sendto(packet, (relay_host, relay_port))

        try:
            response, _ = udp_sock.recvfrom(4096)
            return len(response) > 10
        except socket.timeout:
            return False
    finally:
        udp_sock.close()


def check_udp_support(host: str, port: int, username: Optional[str] = None,
                      password: Optional[str] = None, verbose: bool = False) -> bool:
    if verbose:
        print(f"\nTesting: {host}:{port}")
        print("=" * 60)

    tcp_sock = None

    try:
        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_sock.settimeout(10.0)
        tcp_sock.connect((host, port))

        if verbose:
            print("[1/4] TCP connection established")

        connect_socks5(tcp_sock, username, password)

        if verbose:
            auth_msg = "with credentials" if username else "no auth required"
            print(f"[2/4] SOCKS5 handshake complete ({auth_msg})")

        relay_host, relay_port = request_udp_associate(tcp_sock)

        if verbose:
            print(f"[3/4] UDP relay established: {relay_host}:{relay_port}")

        udp_works = test_udp_relay(relay_host, relay_port)

        if verbose:
            if udp_works:
                print("[4/4] UDP traffic test: SUCCESS")
                print("=" * 60)
                print("✓ UDP FULLY SUPPORTED\n")
            else:
                print("[4/4] UDP traffic test: FAILED")
                print("=" * 60)
                print("⚠ UDP relay established but traffic not working\n")

        return udp_works

    except ConnectionError as e:
        if verbose:
            print(f"✗ {e}")
            print("=" * 60)
            print("UDP NOT SUPPORTED\n")
        return False

    except socket.timeout:
        if verbose:
            print("✗ Connection timeout")
            print("=" * 60)
            print("CONNECTION FAILED\n")
        return False

    except Exception as e:
        if verbose:
            print(f"✗ Error: {e}")
            print("=" * 60)
            print("TEST FAILED\n")
        return False

    finally:
        if tcp_sock:
            tcp_sock.close()


def main():
    parser = argparse.ArgumentParser(
        description='SOCKS5 UDP Support Checker - Test if your proxy supports UDP',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  IP-authenticated proxy:
    %(prog)s proxy.example.com 1080

  Username/password authentication:
    %(prog)s proxy.example.com 1080 -u myuser -p mypass

  Batch test (quiet mode):
    %(prog)s proxy.example.com 1080 -q && echo "UDP works"

Author: nixnode
        """
    )

    parser.add_argument('host', help='Proxy hostname or IP address')
    parser.add_argument('port', type=int, help='Proxy port')
    parser.add_argument('-u', '--username', help='Username for authentication')
    parser.add_argument('-p', '--password', help='Password for authentication')
    parser.add_argument('-q', '--quiet', action='store_true',
                       help='Quiet mode (no output, use exit code)')
    parser.add_argument('-t', '--timeout', type=float, default=5.0,
                       help='UDP test timeout in seconds (default: 5.0)')
    parser.add_argument('-v', '--version', action='version',
                       version=f'%(prog)s {VERSION}')

    args = parser.parse_args()

    result = check_udp_support(
        args.host,
        args.port,
        args.username,
        args.password,
        verbose=not args.quiet
    )

    sys.exit(0 if result else 1)


if __name__ == '__main__':
    main()
