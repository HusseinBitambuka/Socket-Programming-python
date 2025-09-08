import socket, ssl, sys, urllib.parse

class Mini_curl:
    
    def __init__(self, url) -> None:
        self.CRLF = b"\r\n"
        self.marker = b"\r\n\r\n"
        self.scheme, self.host, self.port, self.path =self.parse_url(url)

    def parse_url(self, url):

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
    
    def establish_connection(self):
        sock, last_err = None, None
        for af, socktype, proto, _, sa in socket.getaddrinfo(self.host, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            try:
                s = socket.socket(af, socktype, proto)
                s.settimeout(10)
                if self.scheme == "https":
                    ctx = ssl.create_default_context()
                    s = ctx.wrap_socket(s, server_hostname=self.host)
                s.connect(sa)
                sock = s
                return sock
                
            except Exception as e:
                last_err = e
                continue

        raise last_err or OSError("fail to connect to socket")
    
    def build_GET_request(self):
        default_port = 443 if self.scheme == "https" else 80
        host_hdr = self.host if self.port == default_port else f"{self.host}:{self.port}"
        lines = [
            f"GET {self.path} HTTP/1.1",
            f"Host: {host_hdr}",
            "User-Agent: myclient/0.1",
            "Accept: */*",
            "Connection: close",  # ensures server closes after response
            "",  # end of headers
            "",
        ]
        return ("\r\n".join(lines)).encode("iso-8859-1")
    
    def read_header_bytes(self, sock, max_limit=64*1024):
        buf = bytearray()
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                raise ValueError("connection closed before end of headers")
            buf.extend(chunk)

            i = buf.find(self.marker)
            if i != -1:
                header = bytes(buf[:i+len(self.marker)])
                surplus = bytes(buf[i+len(self.marker):])
                return header, surplus
            if len(buf) > max_limit:
                raise ValueError("HTTP header section too large")
            
    def parse_header(self, header_bytes):
        lines = header_bytes.split(self.CRLF)
        # status line
        first = lines[0].decode("iso-8859-1")
        parts = first.split(' ', 2)
        if len(parts) < 2:
            raise ValueError(f"bad status line: {first!r}")
        http_version, status = parts[0], int(parts[1])
        reason = parts[2] if len(parts) == 3 else ""
        headers = {}
        for line in lines[1:]:
            if not line:
                continue
            k, v = line.decode("iso-8859-1").split(":", 1)
            key = k.strip().lower()
            val = v.strip()
            headers[key] = f"{headers[key]}, {val}" if key in headers else val
        return http_version, status, reason, headers
    
    def read_fixed(self,sock, n, left_over=b""):
        data = bytearray(left_over[:n])
        left_over = left_over[n:]
        need = n - len(data)
        while need > 0:
           buff = sock.recv(min(need, 4*1024))
           if not buff:
               raise ValueError("connection closed before full body was received")
           data.extend(buff)
           need -= len(buff)
        return bytes(data), left_over
    
    def read_chuncked(self, left_over, sock, max_total=128*1024*1024,):
        buff = bytearray(left_over)
        data = bytearray()

        def read_until_marker(marker):
            while True:
                idx = buff.find(marker)
                if idx != -1:
                    return idx
                more = sock.recv(4*1024)
                if not more:
                    raise ValueError("truncated chunked body (waiting for marker)")
                buff += more
        
        while True:
            i = read_until_marker(self.CRLF)
            line = buff[:i]
            size_token = line.split(b";")[0].strip() # ignore any elements after the size if present

            try:
                size = int(size_token, 16)
            except:
                raise  ValueError(f"bad chunk size: {line!r}")
            if size == 0:
                # skip the last two end line marker
                view = bytes(buff[i+2:]) # skip the last end line characters
                while view.find(self.marker) == -1:
                    more = sock.recv(4*1024)
                    if not more:
                        raise ValueError("truncated while reading the final chunck terminator")
                    buff += more
                    view = bytes(buff[i+2:])
                end_index = view.find(self.marker)
                left_over = view[end_index + 4]
                return bytes(data), bytes(left_over)
            
            chunck, buff = self.read_fixed(sock, size, buff[i+2:]) # remember to ignore the first line and the CRF
            data.extend(chunck)
            if len(data)> max_total:
                raise ValueError(f"The body obect is too large{len(data)}")






def main():
        #check arguments
    args = sys.argv

    if len(args) > 2:
        raise ValueError("you provided too many arguments. the program works with only one URL with no flags")
    if len(args) < 2:
        raise ValueError (" you did not add the url")

    name_prog =  args[0]
    url = args[1]

    curl = Mini_curl(url)
    try:
            sock = curl.establish_connection()
            req_bytes = curl.build_GET_request()
            sock.sendall(req_bytes)
            header_bytes, left_over = curl.read_header_bytes(sock)
            http_version, status, reason, headers = curl.parse_header(header_bytes)

            print(f"http_version:{http_version}\n status: {status} \n reason:{reason} \n header:{headers}")



    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()




