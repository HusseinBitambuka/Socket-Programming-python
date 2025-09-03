
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
    port = u.port or (443 if scheme == "https" else 80)
    path = (u.path or "/") + (("?" + u.query) if u.query else "")

    return scheme, host, port, path
    
scheme, host, port, path = parse_url(url=url)

# establish connection
sock = None
for af, socktype, proto, can_name, sa in socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM):
    try:
        s = socket.socket(af, socktype, proto)
        s.settimeout(10)
        if scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=host)
        s.connect(sa)
        sock = s
        break
        
    except Exception as e:
        last_err = ValueError(e)
        print(last_err)
        continue

if not sock:
    raise last_err or OSError("fail to connect to socket")

print("connected to", sock.getpeername())
