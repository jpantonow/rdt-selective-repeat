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
            raise RuntimeError('Cannot initialize Packet: byte_S is corrupt')

        # extract the fields
        seq_num = int(byte_S[Packet.length_S_length: Packet.length_S_length + Packet.seq_num_S_length])
        msg_S = byte_S[Packet.length_S_length + Packet.seq_num_S_length + Packet.checksum_length:]
        return self(seq_num, msg_S)

    def get_byte_S(self):
        # convert sequence number of a byte field of seq_num_S_length bytes
        seq_num_S = str(self.seq_num).zfill(self.seq_num_S_length)
        # convert length to a byte field of length_S_length bytes
        length_S = str(self.length_S_length + len(seq_num_S) + self.checksum_length + len(self.msg_S)).zfill(
            self.length_S_length)
        # compute the checks0um
        checksum = hashlib.md5((length_S + seq_num_S + self.msg_S).encode('utf-8'))
        checksum_S = checksum.hexdigest()
        # compile into a string
        return length_S + seq_num_S + checksum_S + self.msg_S

    @staticmethod
    def corrupt(byte_S):
        # extract the fields
        length_S = byte_S[0:Packet.length_S_length]
        seq_num_S = byte_S[Packet.length_S_length: Packet.seq_num_S_length + Packet.seq_num_S_length]
        checksum_S = byte_S[
                     Packet.seq_num_S_length + Packet.seq_num_S_length: Packet.seq_num_S_length + Packet.length_S_length + Packet.checksum_length]
        msg_S = byte_S[Packet.seq_num_S_length + Packet.seq_num_S_length + Packet.checksum_length:]

        # compute the checksum locally
        checksum = hashlib.md5(str(length_S + seq_num_S + msg_S).encode('utf-8'))
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
    timeout = 3
    window_size = 0
    
    def __init__(self, role_S, server_S, port):
        self.network = Network.NetworkLayer(role_S, server_S, port)
        self.packets = []
        self.buffer = []
    
    def check_buffer(self,buffer):
        for i in range(0,len(buffer)-1):
            if buffer[i].is_ack_pack:
                buffer.remove(buffer.index(i))
            return False
        return True
    
    def set_window_size(self, number):
        self.window_size = number
    
    def adjust_window_size(self,packet):
        for i in range(0,self.window_size-1):
            packet[i] = packet[i+1]
                
    def add_packets(self,Packet: Packet):
        self.packets.append(Packet)
    
    def send_packets(self,Packets):
        for i in range(0,len(Packets)-1):
            self.network.udt_send(Packets[i].get_byte_S())
    
    def adjust_packet_size(self,packets):
        seq_num = int(self.seq_num)
        window_size = int(self.window_size)
        new_packet = packets[seq_num:window_size]
        return new_packet
             
    def remove_packets(self,Packet: Packet):
        self.packets.remove(Packet)
        
    def disconnect(self):
        self.network.disconnect()

    def rdt_3_0_send(self, msg_S):
        p = Packet(self.seq_num, msg_S)
        current_seq = self.seq_num

        while current_seq == self.seq_num:
            self.network.udt_send(p.get_byte_S())
            response = ''
            timer = time.time()

            # Waiting for ack/nak
            while response == '' and timer + self.timeout > time.time():
                response = self.network.udt_receive()

            if response == '':
                continue

            debug_log("SENDER: " + response)

            msg_length = int(response[:Packet.length_S_length])
            self.byte_buffer = response[msg_length:]

            if not Packet.corrupt(response[:msg_length]):
                response_p = Packet.from_byte_S(response[:msg_length])
                if response_p.seq_num < self.seq_num:
                    # It's trying to send me data again
                    debug_log("SENDER: Receiver behind sender")
                    test = Packet(response_p.seq_num, "1")
                    self.network.udt_send(test.get_byte_S())
                elif response_p.msg_S is "1":
                    debug_log("SENDER: Received ACK, move on to next.")
                    debug_log("SENDER: Incrementing seq_num from {} to {}".format(self.seq_num, self.seq_num + 1))
                    self.seq_num += 1
                elif response_p.msg_S is "0":
                    debug_log("SENDER: NAK received")
                    self.byte_buffer = ''
            else:
                debug_log("SENDER: Corrupted ACK")
                self.byte_buffer = ''

    def rdt_3_0_receive(self):
        ret_S = None
        byte_S = self.network.udt_receive()
        self.byte_buffer += byte_S
        current_seq = self.seq_num
        # Don't move on until seq_num has been toggled
        # keep extracting packets - if reordered, could get more than one
        while current_seq == self.seq_num:
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
                answer = Packet(self.seq_num, "0")
                self.network.udt_send(answer.get_byte_S())
            else:
                # create packet from buffer content
                p = Packet.from_byte_S(self.byte_buffer[0:length])
                # Check packet
                if p.is_ack_pack():
                    self.byte_buffer = self.byte_buffer[length:]
                    continue
                if p.seq_num < self.seq_num:
                    debug_log('RECEIVER: Already received packet.  ACK again.')
                    # Send another ACK
                    answer = Packet(p.seq_num, "1")
                    self.network.udt_send(answer.get_byte_S())
                elif p.seq_num == self.seq_num:
                    debug_log('RECEIVER: Received new.  Send ACK and increment seq.')
                    # SEND ACK
                    answer = Packet(self.seq_num, "1")
                    self.network.udt_send(answer.get_byte_S())
                    debug_log("RECEIVER: Incrementing seq_num from {} to {}".format(self.seq_num, self.seq_num + 1))
                    self.seq_num += 1
                # Add contents to return string
                ret_S = p.msg_S if (ret_S is None) else ret_S + p.msg_S
            # remove the packet bytes from the buffer
            self.byte_buffer = self.byte_buffer[length:]
            # if this was the last packet, will return on the next iteration
        return ret_S
 
    
    # Sender’s Windows ( Ws) = Receiver’s Windows ( Wr).
    # Sender can transmit new packets as long as their number is with W of all unACKed packets.
    # Sender retransmit un-ACKed packets after a timeout – Or upon a NAK if NAK is employed.
    # Receiver ACKs all correct packets.
    # Receiver stores correct packets until they can be delivered in order to the higher layer.
    # In Selective Repeat ARQ, the size of the sender and receiver window must be at most one-half of 2^m.
    # Window size should be less than or equal to half the sequence number in SR protocol. This is to avoid packets 
    # being recognized incorrectly. If the size of the window is greater than half the sequence number space, 
    # then if an ACK is lost, 
    # the sender may send new packets that the receiver believes are retransmissions.
    
    #The size of the sender's window is 2^m-1, where m is the number of bits used in the
    #header of the packet to express the packet's sequence number. 
    def rdt_4_0_send(self, msg_L):
        #data from above:
        #if next available seq in window -> send packet
        #timeout(n):
        #resend packet n, restart timer
        
        #ack(n) in recv --> mark packet n as received
        #if n smallest unacked packet advance window to unnacked seq
        #configurar identifier para ter o mesmo numero de ack
        msg_acks = []
        packets = []
        packtime = {}
        iterator = 0
        
        for msg_S in msg_L:
            packets.append(Packet(self.seq_num+iterator,msg_S))
            iterator += 1
        
        self.set_window_size(round(len(packets)/2))
        responses = []
        size = self.window_size

        debug_log(self.seq_num)
        seq = self.seq_num
        #packet = packets[seq:size]
        packet = packets
        debug_log("packet sending == " + f"{packet}")
        for frame in packet:
            self.byte_buffer = ''
            debug_log("frame enviado:" + f"{frame.msg_S}")
            response = ''
            self.network.udt_send(frame.get_byte_S())
            timer = time.time()
            while response == '' and  (timer + self.timeout) > time.time():
                response = self.network.udt_receive()
                if(response):
                    debug_log(f"response == {response}")
            if response  == '':
                continue 
            
            msg_length = int(response[:Packet.length_S_length])
            self.byte_buffer = response[msg_length:]

            if not Packet.corrupt(response[:msg_length]):
                response_p = Packet.from_byte_S(response[:msg_length])
                msg_acks.append(response_p)
                if frame.msg_S in self.buffer:
                    debug_log("SENDER: Receiver behind sender")
                    test = Packet(response_p.seq_num, "1")
                    self.network.udt_send(test.get_byte_S())
            
                elif response_p.msg_S is "1":
                    debug_log("SENDER: Received ACK, move on to next.")
                    debug_log("SENDER: Incrementing seq_num from {} to {}".format(
                            self.seq_num, self.seq_num + 1))
                    self.seq_num += 1
                    self.buffer.append(frame.msg_S)
                    # if (self.check_buffer(msg_acks)):
                    #     responses.pop(0)
                    #     self.seq_num += 1

                elif response_p.msg_S is "0":
                    debug_log("SENDER: NAK received")
                    self.byte_buffer = ''
            else:
                debug_log("SENDER: Corrupted ACK")
                self.byte_buffer = ''

            debug_log("SENDER: " + response)
            msg_k = None
            while(msg_k is None):
                msg_k = self.rdt_4_0_receive()
            debug_log(f"CLIENT RECEBEU: {msg_k}")
            debug_log(self.buffer)
            
    def rdt_4_0_receive(self):
        #send ack(n)
        #if auto-of-order -> buffer
        #if in order -> deliver buffered or in-order,
        #advance window to not received packet
        #packet n in recv -> ack(n) otherwise ignore
        ret_S = None
        byte_S = self.network.udt_receive()
        self.byte_buffer += byte_S
        current_seq = self.seq_num
        # Don't move on until seq_num has been toggled
        # keep extracting packets - if reordered, could get more than one
        while current_seq == self.seq_num:
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
                answer = Packet(self.seq_num, "0")
                self.network.udt_send(answer.get_byte_S())
            else:
                    # create packet from buffer content
                p = Packet.from_byte_S(self.byte_buffer[0:length])
                # Check packet
                if p.is_ack_pack():
                    self.byte_buffer = self.byte_buffer[length:]
                    continue
                if p.seq_num < self.seq_num:
                    debug_log('RECEIVER: Already received packet.  ACK(n) again.')
                    # Send another ACK
                    answer = Packet(p.seq_num, "1")
                    self.network.udt_send(answer.get_byte_S())
                elif p.seq_num == self.seq_num:
                    debug_log('RECEIVER: Received new.  Send ACK(n) and increment seq.')
                    # SEND ACK
                    answer = Packet(self.seq_num, "1")
                    self.network.udt_send(answer.get_byte_S())
                    debug_log("RECEIVER: Incrementing seq_num from {} to {}".format(self.seq_num, self.seq_num + 1))
                    self.seq_num += 1
                # Add contents to return string
                ret_S = p.msg_S if (ret_S is None) else ret_S + p.msg_S
            # remove the packet bytes from the buffer
            self.byte_buffer = self.byte_buffer[length:]
            # if this was the last packet, will return on the next iteration
        if(ret_S):
            debug_log(f"RECEIVER: recv = {ret_S}")
        return ret_S


# if __name__ == '__main__':
#     parser = argparse.ArgumentParser(description='RDT implementation.')
#     parser.add_argument('role', help='Role is either client or server.', choices=['client', 'server'])
#     parser.add_argument('server', help='Server.')
#     parser.add_argument('port', help='Port.', type=int)
#     args = parser.parse_args()

#     rdt = RDT(args.role, args.server, args.port)
#     if args.role == 'client':
#         rdt.rdt_3_0_send('MSG_FROM_CLIENT')
#         sleep(2)
#         print(rdt.rdt_3_0_receive())
#         rdt.disconnect()


#     else:
#         sleep(1)
#         print(rdt.rdt_3_0_receive())
#         rdt.rdt_3_0_send('MSG_FROM_SERVER')
#         rdt.disconnect()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='RDT implementation.')
    parser.add_argument('role', help='Role is either client or server.', choices=['client', 'server'])
    parser.add_argument('server', help='Server.')
    parser.add_argument('port', help='Port.', type=int)
    args = parser.parse_args()

    rdt = RDT(args.role, args.server, args.port)
    if args.role == 'client':
        rdt.rdt_4_0_send('MSG_FROM_CLIENT')
        sleep(2)
        print(rdt.rdt_4_0_receive())
        rdt.disconnect()


    else:
        sleep(1)
        print(rdt.rdt_4_0_receive())
        rdt.rdt_4_0_send('MSG_FROM_SERVER')
        rdt.disconnect()

# Step 1 − Frame 0 sends from sender to receiver and set timer.

# Step 2 − Without waiting for acknowledgement from the receiver another frame, Frame1 is sent by sender by setting the timer for it.

# Step 3 − In the same way frame2 is also sent to the receiver by setting the timer without waiting for previous acknowledgement.

# Step 4 − Whenever sender receives the ACK0 from receiver, within the frame 0 timer then it is closed and sent to the next frame, frame 3.

# Step 5 − whenever the sender receives the ACK1 from the receiver, within the frame 1 timer then it is closed and sent to the next frame, frame 4.

# Step 6 − If the sender doesn’t receive the ACK2 from the receiver within the time slot, it declares timeout for frame 2 and resends the frame 2 again, because it thought the frame2 may be lost or damaged.