import Network
import argparse
import time
from time import sleep
import hashlib

debug = True
# default = False


def debug_log(message):
    if debug:
        print(message)


def debug_stats(message):
    if debug:
        print("\033[1;32m" + message + "\033[0m")


class Packet:
    # the number of bytes used to store packet length
    seq_num_S_length = 10
    length_S_length = 10
    # length of md5 checksum in hex
    checksum_length = 32

    def __init__(self, seq_num, msg_S):
        self.seq_num = seq_num
        self.msg_S = msg_S

    @classmethod
    def from_byte_S(self, byte_S):
        if Packet.corrupt(byte_S):
            raise RuntimeError(f"Cannot initialize Packet: byte_s = {byte_S} is corrupt")

        # extract the fields
        seq_num = int(
            byte_S[Packet.length_S_length: Packet.length_S_length + Packet.seq_num_S_length])
        msg_S = byte_S[Packet.length_S_length +
                       Packet.seq_num_S_length + Packet.checksum_length:]
        return self(seq_num, msg_S)

    def get_byte_S(self):
        # convert sequence number of a byte field of seq_num_S_length bytes
        seq_num_S = str(self.seq_num).zfill(self.seq_num_S_length)
        # convert length to a byte field of length_S_length bytes
        length_S = str(self.length_S_length + len(seq_num_S) + self.checksum_length + len(self.msg_S)).zfill(
            self.length_S_length)
        # compute the checks0um
        checksum = hashlib.md5(
            (length_S + seq_num_S + self.msg_S).encode('utf-8'))
        checksum_S = checksum.hexdigest()
        # compile into a string
        return length_S + seq_num_S + checksum_S + self.msg_S

    @staticmethod
    def corrupt(byte_S):
        # extract the fields
        length_S = byte_S[0:Packet.length_S_length]
        seq_num_S = byte_S[Packet.length_S_length:
                           Packet.seq_num_S_length + Packet.seq_num_S_length]
        checksum_S = byte_S[
            Packet.seq_num_S_length + Packet.seq_num_S_length: Packet.seq_num_S_length + Packet.length_S_length + Packet.checksum_length]
        msg_S = byte_S[Packet.seq_num_S_length +
                       Packet.seq_num_S_length + Packet.checksum_length:]

        # compute the checksum locally
        checksum = hashlib.md5(
            str(length_S + seq_num_S + msg_S).encode('utf-8'))
        computed_checksum_S = checksum.hexdigest()
        # and check if the same
        return checksum_S != computed_checksum_S

    def is_ack_pack(self):
        if self.msg_S == '1' or self.msg_S == '0':
            return True
        return False


class RDT:
    # latest sequence number used in a packet
    seq_num = 0
    # buffer of bytes read from network
    byte_buffer = ''
    timeout = 2
    window_size = 0
    totalpackets = 0
    totalretransmited = 0
    totalcorrupted = 0
    totalcorrupted_acks = 0
    goodput_bytes = 0
    time_goodput = 0
    sizeof_goodput = 0
    
    
    
    def __init__(self, role_S, server_S, port):
        self.network = Network.NetworkLayer(role_S, server_S, port)
        self.packets = []
        self.buffer_send = []
        self.buffer_rcv = []
        self.window = []
        self.pack_msg = {}
        self.pack_ack = {}

    def check_buffer(self, buffer):
        for i in range(0, len(buffer)-1):
            if buffer[i].is_ack_pack:
                buffer.remove(buffer.index(i))
            return False
        return True

    def clear(self):
        self.window_size = 0
        self.seq_num = 0
        self.byte_buffer = ''
        self.packets = []
        self.buffer_send = []
        self.buffer_rcv = []
        self.pack_ack = {}
        self.pack_msg = {}
        self.window = []

    def set_window_size(self, number):
        self.window_size = number

    def adjust_window_size(self, packet):
        for i in range(0, self.window_size-1):
            packet[i] = packet[i+1]

    def add_packets(self, Packet: Packet):
        self.packets.append(Packet)

    def send_packets(self, Packets):
        for i in range(0, len(Packets)-1):
            self.network.udt_send(Packets[i].get_byte_S())

    def adjust_packet_size(self, packets):
        seq_num = int(self.seq_num)
        window_size = int(self.window_size)
        new_packet = packets[seq_num:window_size]
        return new_packet

    def remove_packets(self, Packet: Packet):
        self.packets.remove(Packet)

    def reorder(self,dict_data):
        return [dict_data[key] for key in sorted(dict_data.keys())]
    
    def disconnect(self):
        self.network.disconnect()

    def rdt_4_0_send(self, msg_L):
        # data from above:
        # if next available seq in window -> send packet
        # timeout(n):
        # resend packet n, restart timer

        # ack(n) in recv --> mark packet n as received
        # if n smallest unacked packet advance window to unnacked seq
        # configurar identifier para ter o mesmo numero de ack
        packets = []
        pack_ack = {}
        self.seq_num = 0
        for msg_S in msg_L:
            packets.append(Packet(self.seq_num, msg_S))
            self.seq_num += 1

        self.window_size = round(len(packets)/2)

        lowest_seq = 0
        transmited = []
        while(len(pack_ack)!=len(packets)):
            for packet in packets[lowest_seq : lowest_seq + self.window_size]:
                if(packet.seq_num in pack_ack):
                    continue
                debug_log(f"Transmiting Packet-> {packet.msg_S}")
                debug_log(f"Pack_Ack=={pack_ack}")
                t1_send = time.time()
                self.network.udt_send(packet.get_byte_S())
                response = ''
                timer = time.time()

                while response == '' and (timer + self.timeout > time.time()):
                    response = self.network.udt_receive()
                    
                if response == '':
                    continue

                debug_log("SENDER: " + response)
                msg_length = int(response[:Packet.length_S_length])
                self.byte_buffer = response[msg_length:]
                self.totalpackets += 1
                
                if(packet.seq_num in transmited):
                    self.totalretransmited += 1
                else:
                    transmited.append(packet.seq_num)
                
                if not Packet.corrupt(response[:msg_length]):
                    debug_log("Packet Not Corrupted")
                    response_p = Packet.from_byte_S(response[:msg_length])
                    if packet.seq_num in pack_ack:
                        if (pack_ack[packet.seq_num] == "1"):
                            debug_log("SENDER: Receiver behind sender")
                            test = Packet(response_p.seq_num, "1")
                            self.network.udt_send(test.get_byte_S())
                            self.goodbput_bytes += len(packet.msg_S)

                    elif (response_p.msg_S is "1"):
                        debug_log("NEW PACKET")
                        debug_log("SENDER: ACK received")
                        pack_ack[packet.seq_num] = response_p.msg_S
                        self.pack_msg[packet.msg_S] = response_p.msg_S
                        #debug_stats(f"msg_length == {msg_length}")
                        self.goodput_bytes += 53
                        #debug_stats(f"Goodput=={(time.time()-t1_send):.2f}[s]")
                        if response_p.seq_num == packets[lowest_seq].seq_num:
                            for key in packets:
                                if key.seq_num not in pack_ack:
                                    lowest_seq = key.seq_num
                                    break

                    elif response_p.msg_S is "0":
                        #debug_log("SENDER: NAK received")
                        self.byte_buffer = ''

                    else:
                        #debug_log("SENDER: Corrupted ACK")
                        self.byte_buffer = ''
                        self.totalcorrupted_acks += 1
                
                    debug_stats(f"Throughput=={(self.network.bytes_sent)/(time.time()-t1_send):.2f}[s]")
                    self.network.buffer_S = ''
                    self.byte_buffer = ''
                else:
                    self.totalcorrupted += 1
        self.byte_buffer = ''
        self.network.buffer_S = ''
        
        while True:
                self.network.udt_send(Packet(100000,"\0").get_byte_S())    
                response = ''
                timer = time.time()

                while response == '' and (timer + self.timeout > time.time()):
                    response = self.network.udt_receive()
                    
                if response == '':
                    continue

                msg_length = int(response[:Packet.length_S_length])
                self.byte_buffer = response[msg_length:]
                self.totalpackets +=1
                if(packet.seq_num in transmited):
                    self.totalretransmited += 1
                    
                if not Packet.corrupt(response[:msg_length]):
                    response_p = Packet.from_byte_S(response[:msg_length])

                    if (response_p.msg_S is "1"):
                        debug_log("SENDER: ACK RECEIVED")
                        debug_stats(f"Goodput=={(time.time()-t1_send):.2f}[s]")
                        break

                    elif response_p.msg_S is "0":
                        debug_log("SENDER: NAK received")
                        self.byte_buffer = ''

                    else:
                        debug_log("SENDER: Corrupted ACK")
                        self.byte_buffer = ''
                    #debug_stats(f"Throughput=={(self.network.bytes_sent)/(time.time()-t1_send):.2f}[s]")
                    self.network.buffer_S = ''
                    self.byte_buffer = ''
                else:
                    self.totalcorrupted += 1
                    
        self.pack_ack = pack_ack
        self.packets = packets
        
    def rdt_4_0_receive(self):
        # ver a parada dos buffers no rdt_4_0_receive
        self.byte_buffer = ''
        #pack_ack = {}
        pack_ack = self.pack_ack
        ret_S = None
        ret_seq = None
        byte_S = self.network.udt_receive()
        self.byte_buffer += byte_S
        # keep extracting packets - if reordered, could get more than one
        while True:
            # check if we have received enough bytes
            if len(self.byte_buffer) < Packet.length_S_length:
                break  # not enough bytes to read packet length
            # extract length of packet
            length = int(self.byte_buffer[:Packet.length_S_length])
            if len(self.byte_buffer) < length:
                break  # not enough bytes to read the whole packet
            # Check if packet is corrupt
            if Packet.corrupt(self.byte_buffer):
                # Send a NAK
                debug_log("RECEIVER: Corrupt packet, sending NAK.")
                if(Packet.corrupt(self.byte_buffer[0:length])):
                    break
                answer = Packet(Packet.from_byte_S(self.byte_buffer[0:length]).seq_num, "0")
                self.network.udt_send(answer.get_byte_S())
            else:
                # create packet from buffer content
                p = Packet.from_byte_S(self.byte_buffer[0:length])
                # Check packet
                if p.is_ack_pack():
                    self.byte_buffer = self.byte_buffer[length:]
                    continue
                if p.seq_num in pack_ack:
                    debug_log(
                        'RECEIVER: Already received packet. ACK(n) again.')
                    answer = Packet(p.seq_num, "1")
                    self.network.udt_send(answer.get_byte_S())

                else:
                    debug_log(
                        'RECEIVER: Received new.  Send ACK(n).')
                    # SEND ACK
                    answer = Packet(p.seq_num, "1")
                    self.network.udt_send(answer.get_byte_S())
                    pack_ack[p.seq_num] = "1"
                # Add contents to return string
                ret_S = p.msg_S if (ret_S is None) else ret_S + p.msg_S
                ret_seq = p.seq_num if(ret_seq is None) else ret_seq + p.seq_num
                # remove the packet bytes from the buffer
                self.byte_buffer = self.byte_buffer[length:]
                # if this was the last packet, will return on the next iteration
                # if(p.msg_S in pack_ack):
                #     break
            # remove the packet bytes from the buffer
            self.byte_buffer = self.byte_buffer[length:]
            # if this was the last packet, will return on the next iteration
        if (ret_S):
            debug_log(f"RECEIVER: recv = {ret_S}")
        return (ret_seq,ret_S)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RDT implementation.')
    parser.add_argument('role', help='Role is either client or server.', choices=[
                        'client', 'server'])
    parser.add_argument('server', help='Server.')
    parser.add_argument('port', help='Port.', type=int)
    args = parser.parse_args()

    rdt = RDT(args.role, args.server, args.port)
    if args.role == 'client':
        rdt.rdt_4_0_send('MSG_FROM_CLIENT')
        print(rdt.rdt_4_0_receive())
        rdt.disconnect()

    else:
        print(rdt.rdt_4_0_receive())
        rdt.rdt_4_0_send('MSG_FROM_SERVER')
        rdt.disconnect()
