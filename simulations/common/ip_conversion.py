""" Helper functions to work with IP addresses
"""

import struct
import socket


def ipv4_to_int(ip):
    """ Fast way to convert IPv4 from str to int
    """
    return struct.unpack('>L', socket.inet_aton(ip))[0]


def ipv4_to_str(ip):
    """ Fast way to convert IPv4 from int to str
    """
    return socket.inet_ntoa(struct.pack("!I", ip))


def ipv6_to_int(ip):
    """ Fast way to convert IPv6 from str to int
    to combine to one int: (hi << 64) | lo
    """
    hi, lo = struct.unpack('!QQ', socket.inet_pton(socket.AF_INET6, ip))
    return hi, lo
