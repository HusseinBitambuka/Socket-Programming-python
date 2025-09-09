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
        
    def read_chunked(self, left_over, sock, max_total=128*1024*1024):
        buff = bytearray(left_over)
        data = bytearray()

        def read_until_marker(marker):
            while True:
                idx = buff.find(marker)
                if idx != -1:
                    return idx
                more = sock.recv(4*1024)
                if not more:
                    raise ValueError("truncated body (waiting for marker)")
                buff.extend(more)

        while True:
            i = read_until_marker(self.CRLF)
            line = buff[:i]
            size_token = line.split(b";", 1)[0].strip()
            try:
                size = int(size_token, 16)
            except ValueError:
                raise ValueError(f"bad chunk size: {line!r}")

            if size == 0:
                # bytes after the "0\r\n" line
                view = bytes(buff[i+2:])

                # 1) Fast path: no trailers -> the very next two bytes are CRLF
                while len(view) < 2:
                    more = sock.recv(4*1024)
                    if not more:
                        raise ValueError("truncated while reading final chunk terminator (no trailers)")
                    buff.extend(more)
                    view = bytes(buff[i+2:])

                if view.startswith(self.CRLF):
                    # consume that single CRLF and we're done
                    left_over = view[2:]
                    return bytes(data), bytes(left_over)

                # 2) Slow path: there ARE trailers -> read until CRLFCRLF
                while True:
                    j = view.find(self.marker)  # \r\n\r\n
                    if j != -1:
                        left_over = view[j + 4:]
                        return bytes(data), bytes(left_over)
                    more = sock.recv(4*1024)
                    if not more:
                        raise ValueError("truncated while reading trailers after last chunk")
                    buff.extend(more)
                    view = bytes(buff[i+2:])


            chunk_bytes, after = self.read_fixed(sock, size, bytes(buff[i+2:]))
            data.extend(chunk_bytes)
            if len(data) > max_total:
                raise ValueError(f"the body object is too large: {len(data)} bytes")

            if len(after) < 2:
                need = 2 - len(after)
                extra, _ = self.read_fixed(sock, need, b"")
                after = after + extra
            if after[:2] != self.CRLF:
                raise ValueError("missing CRLF after chunk data")

            buff = bytearray(after[2:])



def process_request(url, retries=10):
    if retries <= 0:
        return f"Redirect limit reached for {url}"

    curl = Mini_curl(url)
    sock = None
    try:
        sock = curl.establish_connection()
        req_bytes = curl.build_GET_request()
        sock.sendall(req_bytes)

        header_bytes, left_over = curl.read_header_bytes(sock)
        http_version, status, reason, headers = curl.parse_header(header_bytes)

        # --- redirects (basic) ---
        if status in (301, 302, 303, 307, 308):
            location = headers.get("location")
            if not location:
                raise ValueError(f"{status} without Location")
            new_url = urllib.parse.urljoin(url, location)
            print(f"redirect {status} → {new_url}")
            return process_request(new_url, retries - 1)

        # --- decide if a body is expected ---
        # (for GET) there is NO body for 1xx, 204, 304
        has_body = not (100 <= status < 200 or status in (204, 304))

        body = b""
        if has_body:
            te = headers.get("transfer-encoding", "").lower()
            cl = headers.get("content-length")

            if "chunked" in te:
                body, left_over = curl.read_chunked(left_over, sock)
            elif te:
                raise ValueError(f"unsupported transfer-encoding: {te}")
            elif cl is not None:
                try:
                    n = int(cl)
                except Exception:
                    raise ValueError(f"Content-Length not an int: {cl!r}")
                body, left_over = curl.read_fixed(sock, n, left_over)
            else:
                # read-until-close
                chunks = [left_over]
                while True:
                    c = sock.recv(65536)
                    if not c: break
                    chunks.append(c)
                body = b"".join(chunks)

        # --- pretty print (optional) ---
        head_str = f"{http_version} {status} {reason}\n" + \
                   "\n".join(f"{k.capitalize()}: {v}" for k, v in headers.items())
        try:
            text_preview = body.decode("utf-8")
        except UnicodeDecodeError:
            text_preview = body.decode("iso-8859-1", errors="replace")

        return f"{head_str}\n\n{text_preview}"

    except Exception as e:
        raise
    finally:
        try:
            if sock is not None:
                sock.close()
        except Exception:
            pass



def main():
        #check arguments
    args = sys.argv

    if len(args) > 2:
        raise ValueError("you provided too many arguments. the program works with only one URL with no flags")
    if len(args) < 2:
        raise ValueError (" you did not add the url")

    name_prog =  args[0]
    url = args[1]
    response = process_request(url)
    print(response)

   







if __name__ == "__main__":
    main()




