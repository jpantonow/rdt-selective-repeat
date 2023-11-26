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
    timeout = 1

    def __init__(self, role_S, server_S, port):
        self.network = Network.NetworkLayer(role_S, server_S, port)

    def disconnect(self):
        self.network.disconnect()

    def rdt_4_0_send(self, segs_msg):
        packets = []

        for seg in segs_msg:
            packets.append(Packet(self.seq_num, seg))
            self.seq_num += 1

        ack_received = 0
        ack_dict = {i: 0 for i in range(len(packets))}
        time_dict = {i: 0 for i in range(len(packets))}
        lowest_seq = 0
        window_size = round(len(packets) / 2)

        last_rcv = time.time()
        while ack_received != len(packets):
            for packet in packets[lowest_seq : lowest_seq + window_size]:
                if not ack_dict[packet.seq_num] and (
                    time_dict[packet.seq_num] + self.timeout < time.time()
                ):
                    self.network.udt_send(packet.get_byte_S())
                    debug_log(f"Packet {packet.seq_num} mandado")
                    time_dict[packet.seq_num] = time.time()
                    time.sleep(0.02)

                # Verifica se chegou algum ACK, evitar acumulo de packets
                response = self.network.udt_receive()
                if response != "":
                    last_rcv = time.time()
                    msg_length = int(response[: Packet.length_S_length])
                    if not Packet.corrupt(response[:msg_length]):
                        response_p = Packet.from_byte_S(response[:msg_length])
                        if response_p.msg_S == "1":
                            debug_log(f"Recebi: ACK: {response_p.seq_num}")
                            if not ack_dict[response_p.seq_num]:
                                ack_dict[response_p.seq_num] = 1
                                ack_received += 1
                            if response_p.seq_num == lowest_seq:
                                for key in range(len(packets)):
                                    if not ack_dict[key]:
                                        lowest_seq = key
                                        window_change = True
                                        break
                    else:
                        debug_log("Corrompido")

            is_timeout = False
            window_change = False

            while (not is_timeout and not window_change) and (
                ack_received != len(packets)
            ):
                response = self.network.udt_receive()

                # Verifica se algum pacote estourou o timer
                timer = time.time()
                for key in list(ack_dict.keys())[lowest_seq : lowest_seq + window_size]:
                    if not ack_dict[key]:
                        if time_dict[key] + self.timeout < timer:
                            is_timeout = True
                            debug_log(f"Timeout: {key}")

                # Reinicia o while se nao tiver chegado a resposta
                if response == "":
                    if last_rcv + self.timeout * 10 < time.time():
                        raise ConnectionAbortedError
                    continue

                last_rcv = time.time()

                debug_log(f"Recebi: {response}")

                msg_length = int(response[: Packet.length_S_length])

                # Verifica se o pacote nao foi corrompido
                if not Packet.corrupt(response[:msg_length]):
                    response_p = Packet.from_byte_S(response[:msg_length])

                    # Verifica se a resposta foi ACK
                    if response_p.msg_S == "1":
                        debug_log(f"Recebi: ACK: {response_p.seq_num}")
                        if not ack_dict[response_p.seq_num]:
                                ack_dict[response_p.seq_num] = 1
                                ack_received += 1
                        if response_p.seq_num == lowest_seq:
                            for key in range(len(packets)):
                                if not ack_dict[key]:
                                    lowest_seq = key
                                    window_change = True
                                    break
                # Pacote corrompido
                else:
                    debug_log("Recebi: Packet corrompido")
        debug_log(
            "----------------------------------------------------------------------------------------------------"
        )

    def sinalizar_fim_entrega(self, role):
        self.timeout = 5
        null_time = 0

        while True:
            # Mandar o caractere nulo
            timer = time.time()
            if null_time + self.timeout < timer:
                self.network.udt_send(Packet(0, "\0").get_byte_S())
                null_time = timer
                if role == "server":
                    return
            # Espera alguma resposta\
            response = self.network.udt_receive()
            if response != "":
                debug_log(response)
                msg_length = int(response[: Packet.length_S_length])
                if not Packet.corrupt(response[:msg_length]):
                    response_p = Packet.from_byte_S(response[:msg_length])
                    return (response_p.seq_num, response_p.msg_S)

    def rdt_4_0_receive(self):
        seq_rec = {}
        last_rcv = time.time()

        while True:
            entry = self.network.udt_receive()
            if entry == "":
                if last_rcv + self.timeout * 10 < time.time():
                    debug_log("Connection timeout - Receive")
                    return seq_rec
                continue

            last_rcv = time.time()

            msg_length = int(entry[: Packet.length_S_length])
            if not Packet.corrupt(entry):
                entry_p = Packet.from_byte_S(entry[:msg_length])
                debug_log(f"Recebi: {entry_p.get_byte_S()}")

                if entry_p.msg_S == "\0":
                    self.network.udt_send(Packet(0, "\0").get_byte_S())
                    return seq_rec
                else:
                    add_seq = True
                    for i in range(len(seq_rec)):
                        if i in seq_rec:
                            if seq_rec[i] == entry_p.seq_num:
                                add_seq = False
                    if add_seq:
                        seq_rec[entry_p.seq_num] = entry_p.msg_S.upper()
                    self.network.udt_send(Packet(entry_p.seq_num, "1").get_byte_S())
            else:
                debug_log("Recebi: Packet Corrompido")


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
