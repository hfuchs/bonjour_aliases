# 2013-07-24, Created by Hagen Fuchs <code@hfuchs.net>
#
# 2013-07-25, Inital code taken from
# <http://stackoverflow.com/questions/3430245/how-to-develop-an-avahi-client-server>
#
# 2013-09-02, Radical rewrite with pybonjour, simply merging the
# examples browse_and_resolve.py and register.py from
# <http://code.google.com/p/pybonjour/>

# --- High-level Overview
# pybonjour.DNSServiceBrowse() searches for regtype Bonjour records
# floating, err, multicasting by and calls browse_callback() when it
# finds one.  browse_callback() in turn uses resolve_callback() to make
# head or tails of the record: if it's a usable record, it gets pushed
# onto the stack called 'resolved'.  These entries are then fed to
# pybonjour.DNSServiceProcessResult() by browse_callback() again.
#
# Something along those lines.  Go read the excellent code.


# --- Modules and Globals
#
import select
import sys
import pybonjour
import re

# I'm using a fixed mDNS registry type: IPP printing.  Note: CUPS
# supports (and advertises) many more types, not least IPPS!  Change to
# taste.
regtype  = "_ipp._tcp"
timeout  = 5             # I'm rather impatient; tweak to taste.
resolved = []
# TODO The server name (short and long form) is still hardcoded below.
# Why?  Because this is essentially a throw-away script.  :)
#servername = "server.domain.com"


# --- Function Definitions
#
def resolve_callback(sdRef, flags, interfaceIndex, errorCode, fullname,
                     hosttarget, port, txtRecord):
    if errorCode == pybonjour.kDNSServiceErr_NoError:
        # Match fullname's like this:
        #    printer\032\064\032server\.domain\.com._ipp._tcp.local.
        #if re.match('^(?!AirPrint).*server..domain.._ipp', fullname):
        if re.match('^(?!AirPrint).*server._ipp', fullname):
            match = re.search('^[a-zA-Z0-9]*', fullname)
            #name  = match.group(0) + " @ server"
            name  = match.group(0) + " @ server.domain.com"
            print fullname + " -> " + name

            # Here's the gist: registering the same TXT record under
            # a different name.
            sdRef = pybonjour.DNSServiceRegister(name = name,
                    regtype = regtype, port = port, txtRecord = txtRecord)

        resolved.append(True)


def browse_callback(sdRef, flags, interfaceIndex, errorCode, serviceName,
                    regtype, replyDomain):
    if errorCode != pybonjour.kDNSServiceErr_NoError:
        return

    if not (flags & pybonjour.kDNSServiceFlagsAdd):
        print 'Service removed'
        return

    print 'Service found: ' + serviceName + '; resolving...'

    resolve_sdRef = pybonjour.DNSServiceResolve(0, interfaceIndex,
            serviceName, regtype, replyDomain, resolve_callback)

    try:
        while not resolved:
            ready = select.select([resolve_sdRef], [], [], timeout)
            if resolve_sdRef not in ready[0]:
                print 'Resolve timed out'
                break
            pybonjour.DNSServiceProcessResult(resolve_sdRef)
        else:
            resolved.pop()
    finally:
        resolve_sdRef.close()


# --- Main
#
browse_sdRef = pybonjour.DNSServiceBrowse(regtype = regtype,
                                          callBack = browse_callback)

try:
    try:
        while True:
            ready = select.select([browse_sdRef], [], [])
            if browse_sdRef in ready[0]:
                pybonjour.DNSServiceProcessResult(browse_sdRef)
    except KeyboardInterrupt:
        pass
finally:
    browse_sdRef.close()

