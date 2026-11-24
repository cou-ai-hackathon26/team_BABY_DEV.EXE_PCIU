
import re
import ssl
import time
import socket
import ipaddress
import http.client

from urllib.parse import urlsplit, urljoin

from bs4 import BeautifulSoup


# =====================================
# Configuration
# =====================================

MAX_URL_LENGTH = 2048

MAX_TEXT_LENGTH = 50000

MIN_TEXT_LENGTH = 20

MAX_RESPONSE_SIZE = 5 * 1024 * 1024

MAX_REDIRECTS = 3

REQUEST_TIMEOUT = 10

TOTAL_TIMEOUT = 30

ALLOWED_LANGUAGES = ("en", "bn")


class URLExtractionError(Exception):
    pass


# =====================================
# 1. Validate Public URL
# =====================================

def validate_public_url(url):

    if not isinstance(url, str):
        raise URLExtractionError(
            "Invalid URL."
        )

    url = url.strip()

    if not url or len(url) > MAX_URL_LENGTH:
        raise URLExtractionError(
            "Invalid URL length."
        )

    if "\\" in url or any(
        ord(character) < 32
        or ord(character) == 127
        for character in url
    ):
        raise URLExtractionError(
            "Invalid URL characters."
        )

    try:
        parsed = urlsplit(url)

        port = parsed.port

    except ValueError:
        raise URLExtractionError(
            "Invalid URL format."
        )

    if parsed.scheme not in ("http", "https"):
        raise URLExtractionError(
            "Only HTTP and HTTPS URLs are supported."
        )

    if not parsed.hostname:
        raise URLExtractionError(
            "Invalid website hostname."
        )

    if parsed.username or parsed.password:
        raise URLExtractionError(
            "URLs containing credentials are not allowed."
        )

    expected_port = (
        443 if parsed.scheme == "https" else 80
    )

    if port is not None and port != expected_port:
        raise URLExtractionError(
            "Non-standard website ports are not allowed."
        )

    hostname = parsed.hostname.rstrip(".").lower()

    if (
        hostname == "localhost"
        or hostname.endswith(".localhost")
        or hostname.endswith(".local")
        or hostname.endswith(".internal")
        or hostname.endswith(".home.arpa")
    ):
        raise URLExtractionError(
            "Private or local URLs are not allowed."
        )

    try:
        hostname = hostname.encode("idna").decode("ascii")

        addresses = socket.getaddrinfo(
            hostname,
            expected_port,
            type=socket.SOCK_STREAM
        )

    except (socket.gaierror, UnicodeError):
        raise URLExtractionError(
            "Unable to resolve the website address."
        )

    public_addresses = []

    for address in addresses:

        ip = ipaddress.ip_address(
            address[4][0]
        )

        if (
            not ip.is_global
            or ip.is_multicast
            or ip.is_reserved
            or getattr(ip, "ipv4_mapped", None)
        ):
            raise URLExtractionError(
                "Private or restricted network addresses are not allowed."
            )

        public_addresses.append(str(ip))

    if not public_addresses:
        raise URLExtractionError(
            "No public website address was found."
        )

    return parsed, hostname, public_addresses[0]


# =====================================
# 2. Connect to Validated IP
# =====================================

class PublicHTTPConnection(http.client.HTTPConnection):

    def __init__(
        self,
        hostname,
        validated_ip,
        port,
        timeout
    ):
        super().__init__(
            hostname,
            port=port,
            timeout=timeout
        )

        self.validated_ip = validated_ip

    def connect(self):

        self.sock = socket.create_connection(
            (self.validated_ip, self.port),
            timeout=self.timeout
        )


class PublicHTTPSConnection(http.client.HTTPSConnection):

    def __init__(
        self,
        hostname,
        validated_ip,
        port,
        timeout
    ):
        super().__init__(
            hostname,
            port=port,
            timeout=timeout,
            context=ssl.create_default_context()
        )

        self.validated_ip = validated_ip

    def connect(self):

        raw_socket = socket.create_connection(
            (self.validated_ip, self.port),
            timeout=self.timeout
        )

        try:
            self.sock = self._context.wrap_socket(
                raw_socket,
                server_hostname=self.host
            )

        except Exception:
            raw_socket.close()
            raise


# =====================================
# 3. Download Public Webpage
# =====================================

def download_webpage(url):

    current_url = url

    deadline = time.monotonic() + TOTAL_TIMEOUT

    for redirect_count in range(MAX_REDIRECTS + 1):

        remaining_time = deadline - time.monotonic()

        if remaining_time <= 0:
            raise URLExtractionError(
                "Website extraction timed out."
            )

        parsed, hostname, validated_ip = (
            validate_public_url(current_url)
        )

        timeout = min(
            REQUEST_TIMEOUT,
            remaining_time
        )

        if parsed.scheme == "https":

            connection = PublicHTTPSConnection(
                hostname,
                validated_ip,
                443,
                timeout
            )

        else:

            connection = PublicHTTPConnection(
                hostname,
                validated_ip,
                80,
                timeout
            )

        path = parsed.path or "/"

        if parsed.query:
            path += "?" + parsed.query

        try:

            connection.request(
                "GET",
                path,
                headers={
                    "User-Agent": "CircularShield/1.0",
                    "Accept": (
                        "text/html,"
                        "application/xhtml+xml,"
                        "text/plain"
                    ),
                    "Accept-Encoding": "identity",
                    "Connection": "close"
                }
            )

            response = connection.getresponse()

            # Handle redirects manually.
            # Every redirected URL is validated again.

            if response.status in (
                301, 302, 303, 307, 308
            ):

                location = response.getheader(
                    "Location"
                )

                if not location:
                    raise URLExtractionError(
                        "Invalid website redirect."
                    )

                if redirect_count >= MAX_REDIRECTS:
                    raise URLExtractionError(
                        "Too many website redirects."
                    )

                next_url = urljoin(
                    current_url,
                    location
                )

                if (
                    parsed.scheme == "https"
                    and urlsplit(next_url).scheme != "https"
                ):
                    raise URLExtractionError(
                        "Unsafe HTTPS redirect."
                    )

                current_url = next_url

                continue


            if response.status in (401, 403):

                raise URLExtractionError(
                    "The website requires login or blocks automated extraction."
                )


            if response.status == 404:

                raise URLExtractionError(
                    "The webpage was not found."
                )


            if response.status == 429:

                raise URLExtractionError(
                    "The website is temporarily limiting requests."
                )


            if response.status != 200:

                raise URLExtractionError(
                    f"Website returned HTTP {response.status}."
                )


            # Validate response type

            content_type = response.getheader(
                "Content-Type", ""
            )

            media_type = (
                content_type.split(";")[0]
                .strip()
                .lower()
            )

            if media_type not in (
                "text/html",
                "application/xhtml+xml",
                "text/plain"
            ):

                raise URLExtractionError(
                    "This URL does not contain a supported HTML or text webpage. "
                    "For PDF or image links, download the file and upload it."
                )


            content_encoding = response.getheader(
                "Content-Encoding", "identity"
            ).lower()

            if content_encoding not in (
                "", "identity"
            ):
                raise URLExtractionError(
                    "Unsupported website response encoding."
                )


            content_length = response.getheader(
                "Content-Length"
            )

            if content_length:

                try:
                    if int(content_length) > MAX_RESPONSE_SIZE:
                        raise URLExtractionError(
                            "The webpage is too large."
                        )

                except ValueError:
                    raise URLExtractionError(
                        "Invalid website response."
                    )


            # Read response with a size limit

            chunks = []

            total_size = 0

            while True:

                if time.monotonic() > deadline:
                    raise URLExtractionError(
                        "Website extraction timed out."
                    )

                chunk = response.read(65536)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > MAX_RESPONSE_SIZE:
                    raise URLExtractionError(
                        "The webpage is too large."
                    )

                chunks.append(chunk)


            content = b"".join(chunks)

            return content, current_url, content_type


        except URLExtractionError:
            raise

        except (socket.timeout, TimeoutError):

            raise URLExtractionError(
                "The website took too long to respond."
            )

        except ssl.SSLError:

            raise URLExtractionError(
                "Unable to establish a secure website connection."
            )

        except (
            OSError,
            http.client.HTTPException,
            UnicodeError,
            ValueError
        ):

            raise URLExtractionError(
                "Unable to retrieve the webpage."
            )

        finally:

            connection.close()


    raise URLExtractionError(
        "Unable to retrieve the webpage."
    )


# =====================================
# 4. Clean Extracted Text
# =====================================

def clean_text(text):

    lines = []

    for line in text.splitlines():

        line = re.sub(
            r"[ \t]+",
            " ",
            line
        ).strip()

        if line:
            lines.append(line)

    return "\n".join(lines).strip()


# =====================================
# 5. Extract HTML Content
# =====================================

def extract_html_content(content, content_type):

    charset_match = re.search(
        r"charset\s*=\s*[\"']?([^;\"'\s]+)",
        content_type,
        re.IGNORECASE
    )

    charset = (
        charset_match.group(1)
        if charset_match
        else None
    )

    if content_type.lower().startswith("text/plain"):

        try:
            text = content.decode(
                charset or "utf-8",
                errors="replace"
            )

        except LookupError:
            text = content.decode(
                "utf-8",
                errors="replace"
            )

        return "", clean_text(text)


    soup = BeautifulSoup(
        content,
        "html.parser",
        from_encoding=charset
    )

    title = ""

    if soup.title:
        title = soup.title.get_text(
            " ",
            strip=True
        )


    # Remove unnecessary HTML elements

    for element in soup([
        "script",
        "style",
        "noscript",
        "iframe",
        "svg",
        "nav",
        "footer",
        "aside",
        "template"
    ]):
        element.decompose()


    # Prefer the main article or content area

    selectors = [
        "main article",
        "article",
        "main",
        "[role='main']",
        ".job-description",
        ".job-details",
        ".job-content",
        ".entry-content",
        ".post-content",
        ".article-content"
    ]

    candidates = []

    for selector in selectors:

        for element in soup.select(selector):

            candidate = clean_text(
                element.get_text(
                    separator="\n",
                    strip=True
                )
            )

            if len(candidate) >= MIN_TEXT_LENGTH:
                candidates.append(candidate)


    if candidates:

        text = max(
            candidates,
            key=len
        )

    else:

        body = soup.body or soup

        text = clean_text(
            body.get_text(
                separator="\n",
                strip=True
            )
        )


    return title, text


# =====================================
# 6. Main URL Extraction Function
# =====================================

def extract_text_from_url(url, language="en"):

    if language not in ALLOWED_LANGUAGES:

        raise URLExtractionError(
            "Unsupported language."
        )

    content, final_url, content_type = (
        download_webpage(url)
    )

    title, text = extract_html_content(
        content,
        content_type
    )

    if len(text) < MIN_TEXT_LENGTH:

        raise URLExtractionError(
            "Not enough readable text was found. "
            "The webpage may require JavaScript or contain only images."
        )

    if len(text) > MAX_TEXT_LENGTH:

        raise URLExtractionError(
            "The webpage contains more than 50,000 characters. "
            "Please copy the relevant circular using Paste Text."
        )

    return {

        "success": True,

        "source_type": "url",

        "language": language,

        "source_url": url.strip(),

        "final_url": final_url,

        "title": title[:300],

        "text": text,

        "character_count": len(text),

        "word_count": len(text.split())

    }
