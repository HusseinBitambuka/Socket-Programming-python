
import socket, ssl, sys, urllib.parse


args = sys.argv

#check arguments

if len(args) > 2:
    raise ValueError("you provided too many arguments. the program works with only one URL with no flags")
if len(args) < 2:
    raise ValueError (" you did not add the url")

name_prog =  args[0]
url = args[1]

def parse_url(url):
    u = urllib.parse.urlsplit(url)

    if u.scheme not in ("http", "https"):
        raise ValueError("please provide a valid URL scheme. provide either http or https")
    if not u.hostname:
        raise ValueError("missing hostname")
    scheme = u.scheme
    host = u.hostname
    port = u.port or (423 if scheme == "https" else 80)
    path = (u.path or "/") + (("?" + u.query) if u.query else "")

    return scheme, host, port, path
    
scheme, host, port, path = parse_url(url=url)

print(f" the scheme is {scheme} and the host is {host} on port {port} the path is {path}")

def establish_connection(scheme, host, port, path):
    host_ip = socket.gethostbyname(f"{host}")
    try:
        new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return new_socket, host_ip
    except:
        raise ValueError (" could not create socket for the given user")
    
url_socket, host_ip = establish_connection(scheme, host, port, path)

print(f"the connection between my machine and  the host {host_ip} and is to be establish on the socket {url_socket}")