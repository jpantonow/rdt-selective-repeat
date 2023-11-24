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
            raise RuntimeError("Cannot initialize Packet: byte_S is corrupt")

        # extract the fields
        seq_num = int(
            byte_S[
                Packet.length_S_length : Packet.length_S_length
                + Packet.seq_num_S_length
            ]
        )
        msg_S = byte_S[
            Packet.length_S_length + Packet.seq_num_S_length + Packet.checksum_length :
        ]
        return self(seq_num, msg_S)

    def get_byte_S(self):
        # convert sequence number of a byte field of seq_num_S_length bytes
        seq_num_S = str(self.seq_num).zfill(self.seq_num_S_length)
        # convert length to a byte field of length_S_length bytes
        length_S = str(
            self.length_S_length
            + len(seq_num_S)
            + self.checksum_length
            + len(self.msg_S)
        ).zfill(self.length_S_length)
        # compute the checks0um
        checksum = hashlib.md5((length_S + seq_num_S + self.msg_S).encode("utf-8"))
        checksum_S = checksum.hexdigest()
        # compile into a string
        return length_S + seq_num_S + checksum_S + self.msg_S

    @staticmethod
    def corrupt(byte_S):
        # extract the fields
        length_S = byte_S[0 : Packet.length_S_length]
        seq_num_S = byte_S[
            Packet.length_S_length : Packet.seq_num_S_length + Packet.seq_num_S_length
        ]
        checksum_S = byte_S[
            Packet.seq_num_S_length
            + Packet.seq_num_S_length : Packet.seq_num_S_length
            + Packet.length_S_length
            + Packet.checksum_length
        ]
        msg_S = byte_S[
            Packet.seq_num_S_length + Packet.seq_num_S_length + Packet.checksum_length :
        ]

        # compute the checksum locally
        checksum = hashlib.md5(str(length_S + seq_num_S + msg_S).encode("utf-8"))
        computed_checksum_S = checksum.hexdigest()
        # and check if the same
        return checksum_S != computed_checksum_S

    def is_ack_pack(self):
        if self.msg_S == "1" or self.msg_S == "0":
            return True
        return False


class RDT:
    # latest sequence number used in a packet
    seq_num = 0
    # buffer of bytes read from network
    byte_buffer = ""
    timeout = 10

    def __init__(self, role_S, server_S, port):
        self.network = Network.NetworkLayer(role_S, server_S, port)

    def disconnect(self):
        self.network.disconnect()

    def rdt_3_0_send(self, msg_S):
        p = Packet(self.seq_num, msg_S)
        current_seq = self.seq_num

        while current_seq == self.seq_num:
            print("a")
            self.network.udt_send(p.get_byte_S())
            response = ""
            timer = time.time()

            # Waiting for ack/nak
            while response == "" and timer + self.timeout > time.time():
                print("a")
                response = self.network.udt_receive()

            if response == "":
                continue

            debug_log("SENDER: " + response)

            msg_length = int(response[: Packet.length_S_length])
            self.byte_buffer = response[msg_length:]

            if not Packet.corrupt(response[:msg_length]):
                response_p = Packet.from_byte_S(response[:msg_length])
                if response_p.seq_num < self.seq_num:
                    # It's trying to send me data again
                    debug_log("SENDER: Receiver behind sender")
                    test = Packet(response_p.seq_num, "1")
                    self.network.udt_send(test.get_byte_S())
                elif response_p.msg_S == "1":
                    debug_log("SENDER: Received ACK, move on to next.")
                    debug_log(
                        "SENDER: Incrementing seq_num from {} to {}".format(
                            self.seq_num, self.seq_num + 1
                        )
                    )
                    self.seq_num += 1
                elif response_p.msg_S == "0":
                    debug_log("SENDER: NAK received")
                    self.byte_buffer = ""
            else:
                debug_log("SENDER: Corrupted ACK")
                self.byte_buffer = ""

    def rdt_4_0_send(self, msg_S):
        seg_men = []

        # Divide a mensagem em strings de ate 10 chars
        for i in range(0, len(msg_S), 10):
            seg_men.append(Packet(self.seq_num, msg_S[i : i + 10]))
            self.seq_num += 1
            #debug_log(f"Entrou: {i}")
        #debug_log(f"{len(seg_men)}")

        ack_received = 0
        ack_dict = {i: 0 for i in range(len(seg_men))}
        time_dict = {i: 0 for i in range(len(seg_men))}
        lowest_seq = 0
        window_size = round(len(seg_men) / 2)

        msg_rcv = {}

        while ack_received != len(seg_men):
            # Manda os pacotes que nao receberam ACK
            #debug_log(f"{len(seg_men)}")
            for packet in seg_men[lowest_seq : lowest_seq + window_size]:
                if not ack_dict[packet.seq_num] and (time_dict[packet.seq_num] + self.timeout < time.time()):
                    self.network.udt_send(packet.get_byte_S())
                    debug_log(f"Packet {packet.seq_num} mandado")
                    time_dict[packet.seq_num] = time.time()
                    time.sleep(1)
                    response = self.network.udt_receive()
                    if response != "":
                        debug_log(response)
                        msg_length = int(response[: Packet.length_S_length])
                        self.byte_buffer = response[msg_length:]
                        if not Packet.corrupt(response[:msg_length]):
                            response_p = Packet.from_byte_S(response[:msg_length])

                            if response_p.msg_S == "1":
                                debug_log(f"Recebi: ACK: {response_p.seq_num}")
                                if not ack_dict[response_p.seq_num]:
                                    ack_dict[response_p.seq_num] = 1
                                    ack_received += 1
                                if response_p.seq_num == lowest_seq:
                                    for key in range(len(seg_men)):
                                        if not ack_dict[key]:
                                            lowest_seq = key
                                            window_change = True
                                            break


            is_timeout = False
            window_change = False

            while (not is_timeout and not window_change) and (ack_received != len(seg_men)):
                # Espera a chegada de ACKs
                response = self.network.udt_receive()

                # Verifica se algum pacote estourou o timer
                timer = time.time()
                for key in list(ack_dict.keys())[lowest_seq: lowest_seq + window_size]:
                    #debug_log(key)
                    #debug_log(f"{time_dict[key] + self.timeout < timer}")
                    if not ack_dict[key]:
                        if time_dict[key] + self.timeout < timer:
                            is_timeout = True
                            debug_log(f"timeout {key}")

                # Reinicia o while se nao tiver chegado a resposta
                if response == "":
                    continue


                debug_log(f"Recebi: {response}")

                msg_length = int(response[: Packet.length_S_length])
                self.byte_buffer = response[msg_length:]

                # Verifica se o pacote nao foi corrompido
                if not Packet.corrupt(response[:msg_length]):
                    response_p = Packet.from_byte_S(response[:msg_length])

                    # Verifica se a resposta foi ACK
                    if response_p.msg_S == "1":
                        debug_log(f"Recebi: ACK: {response_p.seq_num}")
                        ack_dict[response_p.seq_num] = 1
                        if response_p.seq_num == lowest_seq:
                            for key in range(len(seg_men)):
                                if not ack_dict[key]:
                                    lowest_seq = key
                                    window_change = True
                                    break  
                # Pacote corrompido
                else:
                    debug_log("Recebi: Packet corrompido")
                    self.byte_buffer = ""
        debug_log("++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        ack_null_char = False
        null_char_time = 0

        while len(msg_rcv) != ack_received:
            if not ack_null_char and null_char_time + self.timeout < time.time():
                self.network.udt_send(Packet(self.seq_num, "\0").get_byte_S())
                null_char_time = time.time()

            response = self.network.udt_receive()

            if response == '':
                continue

            msg_length = int(response[: Packet.length_S_length])
            self.byte_buffer = response[msg_length:]

            if not Packet.corrupt(response):
                response_p = Packet.from_byte_S(response[:msg_length])
                if response_p.msg_S == "1":
                    ack_null_char = True
                elif response_p.msg_S != "1" or response_p.msg_S != "0":
                    ack_null_char = True
                    msg_rcv[response_p.seq_num] = response_p.msg_S
                    self.network.udt_send(Packet(response_p.seq_num, "1").get_byte_S())
                    debug_log(f"Recebi: {response_p.msg_S}")
            else:
                debug_log(response)
                debug_log("corrupted")

        msg = ''
        for key in sorted(msg_rcv):
            msg += msg_rcv[key]
        return msg
    
    def rdt_4_0_receive(self):
        seq_rec = [] # Armazena TUPLA (seq_num, Packet) seq_num = numero de sequencia da chegada

        null_char = False
        connection_timeout = False

        seq_sent_ack = {}
        seq_sent_time = {}

        while not null_char and not connection_timeout:
            entry = self.network.udt_receive()
            if entry == "":
                continue
            msg_length = int(entry[: Packet.length_S_length])
            self.byte_buffer = entry[msg_length:]
            if not Packet.corrupt(entry):
                entry_p = Packet.from_byte_S(entry[:msg_length])
                debug_log(f"Recebi: {entry_p.get_byte_S()}")

                if entry_p.msg_S == "\0":
                    self.network.udt_send(Packet(1000, "1").get_byte_S())
                    null_char = True
                else:
                    add_seq = True
                    for i in range(len(seq_rec)):
                        if seq_rec[i][0] == entry_p.seq_num:
                            add_seq = False
                    if add_seq:
                        seq_rec.append((entry_p.seq_num, Packet(entry_p.seq_num, entry_p.msg_S.upper())))
                        seq_sent_time[entry_p.seq_num] = 0
                        seq_sent_ack[entry_p.seq_num] = 0
                        window_change = True
                    self.network.udt_send(Packet(entry_p.seq_num, "1").get_byte_S())
                    #debug_log(seq_rec)
            else:
                debug_log("Recebi: Packet Corrompido")
        debug_log("SAIU.")
        sleep(1)

        fin = False
        window_size = round(len(seq_rec) / 2)
        window_change = False
        is_timeout = False
        lowest_seq = 0

        seq_rec_ord = sorted(seq_rec, key=lambda l: l[0])
        while not fin:
            timer = time.time()
            for tupla in seq_rec_ord[lowest_seq:lowest_seq + window_size]:
                if not seq_sent_ack[tupla[0]] and seq_sent_time[tupla[0]] + self.timeout < timer:
                    self.network.udt_send(tupla[1].get_byte_S())
                    seq_sent_time[tupla[0]] = time.time()
                    debug_log(f"Enviado packet {tupla[0]}, {tupla[1].seq_num}, {tupla[1].msg_S}")

                    time.sleep(1)
                    response = self.network.udt_receive()

                    if response != "":
                        msg_length = int(response[: Packet.length_S_length])
                        self.byte_buffer = response[msg_length:]
                        debug_log(response)
                        if not Packet.corrupt(response):
                            msg_length = int(response[: Packet.length_S_length])
                            self.byte_buffer = response[msg_length:]
                            response_p = Packet.from_byte_S(response[:msg_length])

                            if response_p.msg_S == "1":
                                debug_log(f"Recebi: ACK: {response_p.seq_num}")
                                seq_sent_ack[response_p.seq_num] = 1
                                debug_log(seq_sent_ack)

                                if response_p.seq_num == lowest_seq:
                                    for key in range(len(seq_rec_ord)):
                                        if not seq_sent_ack[key]:
                                            lowest_seq = key
                                            debug_log(f"lowest: {lowest_seq}")
                                            window_change = True
                                            break       

            while not window_change and not is_timeout:
                response = self.network.udt_receive()
                if response == '':
                    continue

                msg_length = int(response[: Packet.length_S_length])
                self.byte_buffer = response[msg_length:]

                if not Packet.corrupt(response[msg_length:]):
                    response_p = Packet.from_byte_S(response[:msg_length])

                    if response_p.msg_S == "1":
                        debug_log(f"Recebi: ACK: {response_p.seq_num}")
                        seq_sent_ack[response_p.seq_num] = 1
                        debug_log(seq_sent_ack)

                        if response_p.seq_num == lowest_seq:
                            for key in range(len(seq_rec_ord)):
                                if not seq_sent_ack[key]:
                                    lowest_seq = key
                                    debug_log(f"lowest: {lowest_seq}")
                                    window_change = True
                                    break       
                
                else:
                    debug_log("Corrupted")
            

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
            length = int(self.byte_buffer[: Packet.length_S_length])
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
                    debug_log("RECEIVER: Already received packet.  ACK again.")
                    # Send another ACK
                    answer = Packet(p.seq_num, "1")
                    self.network.udt_send(answer.get_byte_S())
                elif p.seq_num == self.seq_num:
                    debug_log("RECEIVER: Received new.  Send ACK and increment seq.")
                    # SEND ACK
                    answer = Packet(self.seq_num, "1")
                    self.network.udt_send(answer.get_byte_S())
                    debug_log(
                        "RECEIVER: Incrementing seq_num from {} to {}".format(
                            self.seq_num, self.seq_num + 1
                        )
                    )
                    self.seq_num += 1
                # Add contents to return string
                ret_S = p.msg_S if (ret_S is None) else ret_S + p.msg_S
            # remove the packet bytes from the buffer
            self.byte_buffer = self.byte_buffer[length:]
            # if this was the last packet, will return on the next iteration
        return ret_S


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RDT implementation.")
    parser.add_argument(
        "role", help="Role is either client or server.", choices=["client", "server"]
    )
    parser.add_argument("server", help="Server.")
    parser.add_argument("port", help="Port.", type=int)
    args = parser.parse_args()

    rdt = RDT(args.role, args.server, args.port)
    if args.role == "client":
        rdt.rdt_3_0_send("MSG_FROM_CLIENT")
        sleep(2)
        print(rdt.rdt_3_0_receive())
        rdt.disconnect()

    else:
        sleep(1)
        print(rdt.rdt_3_0_receive())
        rdt.rdt_3_0_send("MSG_FROM_SERVER")
        rdt.disconnect()
