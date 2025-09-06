
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


def build_request(method, host, port, path):

    host_hdr = f"{host}:{port}"
    lines = [
        f"{method} {path} HTTP/1.1",
        f"Host: {host_hdr}",
        "User-Agent: myclient/0.1",
        "Accept: */*",
        "Connection: close",  # ensures server closes after response
        "",  # end of headers
        "",
    ]
    return ("\r\n".join(lines)).encode("iso-8859-1")

req_bytes = build_request("GET", host, port, path)
sock.sendall(req_bytes)


CRLF = b"\r\n"
marker = b"\r\n\r\n"

def read_header_bytes(sock, marker=b"\r\n\r\n", max_limit=64*1024):
    buf = bytearray()
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            raise ValueError("connection closed before end of headers")
        buf.extend(chunk)

        i = buf.find(marker)
        if i != -1:
            header = bytes(buf[:i+len(marker)])
            surplus = bytes(buf[i+len(marker):])
            return header, surplus

        if len(buf) > max_limit:
            raise ValueError("HTTP header section too large")
header_bytes, leftover = read_header_bytes(sock)

def parse_header(header_bytes):
    lines = header_bytes.split(CRLF)
    # parsed the first line
    start = lines[0].decode("iso-8859-1").split()
    http_version =start[0]
    status = start[1]
    reason = "".join(start[2:])
    parsed_lines = {}
    for line in lines[1:]:
        if not line:
            continue
        key, description = line.decode("iso-8859-1").split(":", 1)
        parsed_lines[key] = description
    return http_version, status, reason, parsed_lines

http_version, status, reason, header = parse_header(header_bytes)


print(f"http_version:{http_version}\n status: {status} \n reason:{reason} \n header:{header}")

 


