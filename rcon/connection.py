# Copyright (C) 2013 Peter Rowlands
"""Source server RCON communications module"""

import contextlib
import itertools
import struct
import asyncio

import logging

# "Vanilla" RCON Packet types
SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0
# Special packet type used by Squad RCON servers to indicate a chat message that streams in even without requests.
SQUAD_CHAT_STREAM = 1
# NOTE(bsubei): I completely invented this type just to internally signal end of multipacket response.
END_OF_MULTIPACKET = 9
# NOTE(timraay): I completely invented this type just to internally signal when the response was only a string and the pkt_id is the same as before.
MULTIPACKET_STRING = 10

# Special responses by the Squad server to indicate the end of a multipacket response.
SPECIAL_MULTIPACKET_HEADER = b'\x00\x01\x00\x00\x00\x00\x00'
SPECIAL_MULTIPACKET_BYTES = b'\x00\x00\x00\x01\x00\x00\x00'


class PlayerChat(object):
    """Represents chat messages from a player"""

    def __init__(self, player_id, player_name, messages=[]):
        self.player_id = player_id
        self.player_name = player_name
        self.messages = messages

    def __repr__(self):
        return f'ID: {self.player_id}, name: {self.player_name}, messages: {self.messages}'


class RconPacket(object):
    """RCON packet"""

    def __init__(self, pkt_id=0, pkt_type=-1, body=''):
        self.pkt_id = pkt_id
        self.pkt_type = pkt_type
        self.body = body

    def __str__(self):
        """Return the body string."""
        return self.body

    def size(self):
        """Return the pkt_size field for this packet."""
        return len(self.body) + 10

    def pack(self):
        """Return the packed version of the packet."""
        return struct.pack('<3i{0}s'.format(len(self.body) + 2),
                           self.size(), self.pkt_id, self.pkt_type,
                           bytearray(self.body, 'utf-8'))


@contextlib.contextmanager
def get_managed_rcon_connection(*args, **kwargs):
    """ Yields a managed RconConnection (closes its socket when leaving context). """
    conn = RconConnection(*args, **kwargs)
    yield conn
    conn._writer.close()


class RconConnection(object):
    """RCON client to server connection"""

    @classmethod
    async def create(cls, server, port=27015, password='', single_packet_mode=False, instance_id=None):
        """Construct an RconConnection.

        Parameters:
            server (str) server hostname or IP address
            port (int) server port number
            password (str) server RCON password
            single_packet_mode (bool) set to True for servers which do not hand 0-length SERVERDATA_RESPONSE_VALUE
                requests (i.e. Factorio).

        """
        self = cls()

        self.id = instance_id
        self.timeout = 10
        self.server = server # Times out when invalid
        self.port = port # Raises a ConnectionRefusedError when invalid
        self.password = password # Returns empty headers when invalid
        self.single_packet_mode = single_packet_mode

        self._writer = None
        await self._connect_sock()
        logging.info('New RCON connection created with %s:%s', self.server, self.port)
        self.pkt_id = itertools.count(1)
        await self._authenticate(password)
        self.all_player_chat = list()

        return self

    async def _connect_sock(self):
        if self._writer and not self._writer.is_closing():
            self._writer.close()
            await self._writer.wait_closed()
        
        try:
            self._reader, self._writer = await asyncio.wait_for(asyncio.open_connection(host=self.server, port=self.port), timeout=self.timeout)
        except asyncio.TimeoutError:
            raise RconAuthError("Unknown host")
        except ConnectionRefusedError:
            raise RconAuthError("Invalid port")
        except OSError:
            raise RconAuthError("Invalid host")

    async def _authenticate(self, password):
        """Authenticate with the server using the given password."""
        auth_pkt = RconPacket(next(self.pkt_id), SERVERDATA_AUTH, password)
        await self._send_pkt(auth_pkt)
        # The server should respond with a SERVERDATA_RESPONSE_VALUE followed by SERVERDATA_AUTH_RESPONSE.
        # Note that some server types omit the initial SERVERDATA_RESPONSE_VALUE packet.
        # For Squad, neither of these are sent and you'll face an empty stream.
        try:
            auth_resp = await self.read_response(auth_pkt, skip_empty_headers=False)
        except RconError:
            logging.warning('%s:%s refused RCON password %s', self.server, self.port, self.password)
            raise RconAuthError('Bad password')
        if auth_resp.pkt_type == SERVERDATA_RESPONSE_VALUE:
            auth_resp = await self.read_response()
        if auth_resp.pkt_type != SERVERDATA_AUTH_RESPONSE:
            raise RconError('Received invalid auth response packet')
        if auth_resp.pkt_id == -1:
            raise RconAuthError('Bad password')
        logging.debug('Logged in with RCON password at %s:%s', self.server, self.port)

    async def exec_command(self, command):
        """Execute the given RCON command.

        Parameters:
            command (str) the RCON command string (ex. "status")

        Returns the response body
        """
        #print(f'\n============================\n\nExecuting "{command}"')
        cmd_pkt = RconPacket(next(self.pkt_id), SERVERDATA_EXECCOMMAND, command)
        try:
            logging.info('Sending RCON command to %s:%s: %s', self.server, self.port, command)
            await self._send_pkt(cmd_pkt)
            resp = await self.read_response(cmd_pkt, multi=True)
        except (OSError, RconEmptyHeaderError):
            logging.warn('%s:%s raised OSError or RconEmptyHeaderError, creating new socket...', self.server, self.port)
            await self._connect_sock()
            await self._authenticate(self.password)
            # Try again
            await self._send_pkt(cmd_pkt)
            resp = await self.read_response(cmd_pkt, multi=True)
        except Exception as e:
            await self.flush_socket()
            raise e
        return resp.body

    async def _send_pkt(self, pkt):
        """Send one RCON packet over the connection.

            Raises:
                RconSizeError if the size of the specified packet is > 4096 bytes
                RconError if the received packet header is malformed
        """
        if pkt.size() > 4096:
            raise RconSizeError('pkt_size > 4096 bytes')
        data = pkt.pack()
        self._writer.write(data)
        await self._writer.drain()

    async def _recv_pkt(self, skip_empty_headers=True):
        """Read one RCON packet"""
        # The header is made of three little-endian integers (8 bytes each).
        HEADER_SIZE = struct.calcsize('<3i')
        for i in range(5):
            # Skip empty packets and try again.
            header = await asyncio.wait_for(self._reader.read(HEADER_SIZE), timeout=self.timeout)
            #print("\nheader:", header)
            if len(header) != 0 or skip_empty_headers:
                break
        if len(header) == 0:
            raise RconEmptyHeaderError('Received empty packet header')

        # We got a weird packet here! If it's the special multipacket header, there is nothing left to read for
        # this packet. Otherwise, it's a malformed packet header.
        if header == SPECIAL_MULTIPACKET_HEADER:
            #print("packet header is SPECIAL_MULTIPACKET_HEADER")
            return RconPacket(-1, END_OF_MULTIPACKET, '')
        if len(header) != HEADER_SIZE:
            raise RconError('Received malformed packet header!')
        
        # Use the given packet size to read the body of the packet.
        (pkt_size, pkt_id, pkt_type) = struct.unpack('<3i', header)
        #print("size,id,type:",pkt_size, pkt_id, pkt_type)

        bytes_left = pkt_size - 8
        body = b""
        while bytes_left > 0:
            recved_body = await self._reader.read(bytes_left)
            #print("bytes received: %s/%s" % (len(recved_body), bytes_left))
            bytes_left -= len(recved_body)
            body += recved_body
        #print("body:", body)

        # NOTE(bsubei): chat packets may come at any point. Just store them and continue with the normal response.
        # In this case we recursively call _recv_pkt until we get a non-chat packet.
        if pkt_type == SQUAD_CHAT_STREAM:
            #print("packet is SQUAD_CHAT_STREAM")
            self.add_chat_message(body.strip(b'\x00\x01').decode('utf-8'))
            return await self._recv_pkt()
        # NOTE(bsubei): sometimes the end of multipacket response comes attached with the chat message (and the chat
        # message has the wrong packet type). This was observed on Squad version b-17.0.13.23847.
        # e.g. packet body: b'\x00\x00\x00\x01\x00\x00\x00[ChatAll] this is example chat\x00\x00'.
        if SPECIAL_MULTIPACKET_BYTES in body:
            #print('Found multipacket response inside a chat message! Using chat and discarding the rest!')
            self.add_chat_message(body.strip(b'\x00\x01').decode('utf-8'))
            return RconPacket(-1, END_OF_MULTIPACKET, '')

        #print("returning normal packet")
        return RconPacket(pkt_id, pkt_type, body)

    async def read_response(self, request=None, multi=False, skip_empty_headers=True):
        """Return the next response packet.

        Parameters:
            request (RconPacket) if request is provided, read_response() will check that the response ID matches the
                specified request ID
            multi (bool) set to True if read_response() should check for a multi packet response. If the current
                RconConnection has single_packet_mode enabled, this parameter is ignored.

        Raises:
            RconError if an error occurred while receiving the server response
        """
        if request and not isinstance(request, RconPacket):
            raise TypeError('Expected RconPacket type for request')
        if not self.single_packet_mode and multi:
            if not request:
                raise ValueError('Must specify a request packet in order to'
                                 ' read a multi-packet response')
            response = await self._read_multi_response(request)
        else:
            response = await self._recv_pkt(skip_empty_headers)
        if (not self.single_packet_mode and
                response.pkt_type not in (SERVERDATA_RESPONSE_VALUE, SERVERDATA_AUTH_RESPONSE)):
            raise RconError('Recieved unexpected RCON packet type')
        if request and response.pkt_id != request.pkt_id:
            raise RconError(f'Response ID does not match request ID')
        return response

    async def _read_multi_response(self, req_pkt):
        """Return concatenated multi-packet response."""
        #print("reading multi-packet")
        chk_pkt = RconPacket(next(self.pkt_id), SERVERDATA_RESPONSE_VALUE)
        #print("send:", self.pkt_id)
        await self._send_pkt(chk_pkt)
        # According to the Valve wiki, a server will mirror a
        # SERVERDATA_RESPONSE_VALUE packet and then send an additional response
        # packet with an empty body. So we should concatenate any packets until
        # we receive a response that matches the ID in chk_pkt
        body_parts = []
        # TODO(bsubei): different messages may have different encodings (ascii vs utf-8) based on the kinds of player
        # names for commands like 'ListPlayers'. Keep an eye out for that bug.
        #print("entering loop")
        while True:
            response = await self._recv_pkt()
            if response.pkt_type == MULTIPACKET_STRING:
                if SPECIAL_MULTIPACKET_HEADER in response.body:
                    # Since we don't know the size of the response beforehand, the end-of-multipacket may be included inside the response.
                    #print("found end-of-multipacket response")
                    new_body = response.body.split(SPECIAL_MULTIPACKET_HEADER)[0]
                    body_parts.append(new_body)
                    return RconPacket(req_pkt.pkt_id, SERVERDATA_RESPONSE_VALUE,
                          ''.join(str(body_parts)))
            else:
                if response.pkt_type != SERVERDATA_RESPONSE_VALUE:
                    raise RconError('Received unexpected RCON packet type')
                if response.pkt_id == chk_pkt.pkt_id:
                    break
                elif response.pkt_id != req_pkt.pkt_id:
                    raise RconError('Response ID does not match request ID')
            #print("body:", response.body)
            body_parts.append(response.body)
        #print("exiting loop")
        # NOTE(bsubei): for Squad servers, end of multipacket is signalled by an empty body response and a special
        # 7-byte packet (sometimes included with the next chat message).
        empty_response = await self._recv_pkt()
        if empty_response.pkt_type != SERVERDATA_RESPONSE_VALUE and empty_response.pkt_id != response.pkt_id:
            raise RconError('Expected empty response after multipacket')
        end_of_multipacket = await self._recv_pkt()
        if (end_of_multipacket.pkt_type != END_OF_MULTIPACKET and
                SPECIAL_MULTIPACKET_BYTES not in end_of_multipacket.body):
            raise RconError('Expected end-of-multipacket response not received!')

        # Return the packet.
        return RconPacket(req_pkt.pkt_id, SERVERDATA_RESPONSE_VALUE,
                          ''.join(str(body_parts)))

    async def flush_socket(self):
        if not self._reader.at_eof():
            await self._reader.read()

    def get_player_chat(self):
        """ Returns the stored player chat objects. """
        return self.all_player_chat

    def add_chat_message(self, message):
        message = message.strip('\x00')
        logging.info('Logging new chat message: %s', message)
        self.all_player_chat.append(message)
        return self.all_player_chat

    def clear_player_chat(self):
        """ Clears the player chat objects (becomes an empty dict). """
        self.all_player_chat = list()



class RconError(Exception):
    """Generic RCON error."""
    pass
class RconAuthError(RconError):
    """Raised if an RCON Authentication error occurs."""
    pass
class RconEmptyHeaderError(RconError):
    """Raised when a RCON packet header is empty"""
    pass
class RconSizeError(RconError):
    """Raised when an RCON packet is an illegal size."""
    pass


