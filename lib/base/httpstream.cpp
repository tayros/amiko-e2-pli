#include <cstdio>
#include <openssl/evp.h>

#include <lib/base/httpstream.h>
#include <lib/base/eerror.h>

DEFINE_REF(eHttpStream);

eHttpStream::eHttpStream() : m_streamSocket(-1)
{
}

eHttpStream::~eHttpStream()
{
	close();
}

int eHttpStream::open(const std::string& url)
{
	std::string currenturl(url), newurl;

	for (unsigned int i = 0; i < 3; i++)
	{
		if (openUrl(currenturl, newurl) < 0)
		{
			/* connection failed */
			return -1;
		}
		if (newurl.empty())
		{
			/* we have a valid stream connection */
			return run();
		}
		/* switch to new url */
		close();
		currenturl.swap(newurl);
		newurl.clear();
	}
	/* too many redirect / playlist levels (we accept one redirect + one playlist) */
	return -1;
}

int eHttpStream::openUrl(const std::string &url, std::string &newurl)
{
	int port;
	std::string hostname;
	std::string uri = url;
	std::string request;
	size_t buflen = 1024;
	char *linebuf = NULL;
	int result;
	char proto[100];
	int statuscode = 0;
	char statusmsg[100];
	bool playlist = false;
	bool contenttypeparsed = false;

	close();

	int pathindex = uri.find("/", 7);
	if (pathindex > 0)
	{
		hostname = uri.substr(7, pathindex - 7);
		uri = uri.substr(pathindex, uri.length() - pathindex);
	}
	else
	{
		hostname = uri.substr(7, uri.length() - 7);
		uri = "";
	}
	int authenticationindex = hostname.find("@");
	if (authenticationindex > 0)
	{
		BIO *mbio, *b64bio, *bio;
		char *p = (char*)NULL;
		int length = 0;
		m_authorizationData = hostname.substr(0, authenticationindex);
		hostname = hostname.substr(authenticationindex + 1);
		mbio = BIO_new(BIO_s_mem());
		b64bio = BIO_new(BIO_f_base64());
		bio = BIO_push(b64bio, mbio);
		BIO_write(bio, m_authorizationData.data(), authorizationData.length());
		BIO_flush(bio);
		length = BIO_ctrl(mbio, BIO_CTRL_INFO, 0, (char*)&p);
		m_authorizationData = "";
		if (p && length > 0)
		{
			/* base64 output contains a linefeed, which we ignore */
			m_authorizationData.append(p, length - 1);
		}
		BIO_free_all(bio);
	}
	int customportindex = hostname.find(":");
	if (customportindex > 0)
	{
		port = atoi(hostname.substr(customportindex + 1, hostname.length() - customportindex - 1).c_str());
		hostname = hostname.substr(0, customportindex);
	}
	else if (customportindex == 0)
	{
		port = atoi(hostname.substr(1, hostname.length() - 1).c_str());
		hostname = "localhost";
	}
	else
	{
		port = 80;
	}
	streamSocket = eSocketBase::connect(hostname.c_str(), port, 10);
	if (streamSocket < 0) goto error;

	request = "GET ";
	request.append(uri).append(" HTTP/1.1\r\n");
	request.append("Host: ").append(hostname).append("\r\n");
	if (authorizationData != "")
	{
		request.append("Authorization: Basic ").append(m_authorizationData).append("\r\n");
	}
	request.append("Accept: */*\r\n");
	request.append("Connection: close\r\n");
	request.append("\r\n");

	eSocketBase::writeAll(streamSocket, request.data(), request.length());

	linebuf = (char*)malloc(buflen);

	result = eSocketBase::readLine(streamSocket, &linebuf, &buflen);
	if (result <= 0) goto error;

	result = sscanf(linebuf, "%99s %d %99s", proto, &statuscode, statusmsg);
	if (result != 3 || (statuscode != 200 && statuscode != 302))
	{
		eDebug("%s: wrong http response code: %d", __FUNCTION__, statuscode);
		goto error;
	}

	while (1)
	{
		result = eSocketBase::readLine(streamSocket, &linebuf, &buflen);
		if (!contenttypeparsed)
		{
			char contenttype[32];
			if (sscanf(linebuf, "Content-Type: %32s", contenttype) == 1)
			{
				contenttypeparsed = true;
				if (!strcmp(contenttype, "application/text")
				|| !strcmp(contenttype, "audio/x-mpegurl")
				|| !strcmp(contenttype, "audio/mpegurl")
				|| !strcmp(contenttype, "application/m3u"))
				{
					/* assume we'll get a playlist, some text file containing a stream url */
					playlist = true;
				}
			}
		}
		else if (playlist && !strncmp(linebuf, "http://", 7))
		{
			newurl = linebuf;
			eDebug("%s: playlist entry: %s", __FUNCTION__, newurl.c_str());
			break;
		}
		else if (statuscode == 302 && !strncmp(linebuf, "Location: ", 10))
		{
			newurl = &linebuf[10];
			eDebug("%s: redirecting to: %s", __FUNCTION__, newurl.c_str());
			break;
		}
		if (!playlist && result == 0) break;
		if (result < 0) break;
	}

	free(linebuf);
	return 0;
error:
	eDebug("%s failed", __FUNCTION__);
	free(linebuf);
	close();
	return -1;
}

int eHttpStream::close()
{
	kill();
	eDebug("eHttpStream::close socket");
	int retval = -1;
	if (m_streamSocket >= 0)
	{
		retval = ::close(m_streamSocket);
		m_streamSocket = -1;
	}
	return retval;
}

ssize_t eHttpStream::read(off_t offset, void *buf, size_t count)
{
	if (m_streamSocket < 0) {
		eDebug("eHttpStream::read not valid fd");
		return -1;
	}

	//max 2 reads, normal one and one after reconnect
	int tryReconnect = 2;
        
	while(tryReconnect) {
		const int nRead = eSocketBase::timedRead(streamSocket, buf, count, 5000, 500);
		if (!nRead) {
			close();
			if (open(m_url)) break;
		} else return nRead;
		tryReconnect--
	}

	return -1;
}

void eHttpStream::thread()
{
	hasStarted();
}

int eHttpStream::valid()
{
	return m_streamSocket >= 0;
}

off_t eHttpStream::length()
{
	return (off_t)-1;
}

off_t eHttpStream::offset()
{
	return 0;
}

